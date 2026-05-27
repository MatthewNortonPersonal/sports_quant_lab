"""
Historical play-by-play data loader.

Supports NBA (via nba_api) and NCAAW (via CBBpy).
Normalizes both into the same play_by_play table schema.

Usage:
    python -m infra.nba.historical_loader --league NBA --season 2024-25
    python -m infra.nba.historical_loader --league NCAAW --season 2024-25
"""

import argparse
import logging
import re
import time
from typing import Optional

import pandas as pd

from infra.db import queries
from infra.nba.utils import compute_elapsed_minutes

logger = logging.getLogger(__name__)

# PlayByPlayV3 actionType → our event_type names
# actionType is a free-text string in V3 (e.g. 'Field Goal', 'Free Throw', 'Rebound')
def _map_action_type(action_type: str, sub_type: str) -> str:
    a = (action_type or "").lower().strip()
    s = (sub_type or "").lower().strip()
    if a == "field goal":
        return "field_goal" if "miss" not in a else "missed_shot"
    if "missed" in a or "miss" in s:
        return "missed_shot"
    if "free throw" in a:
        return "free_throw"
    if "rebound" in a:
        return "rebound"
    if "turnover" in a:
        return "turnover"
    if "foul" in a:
        return "foul"
    if "violation" in a:
        return "violation"
    if "substitution" in a or "sub" in a:
        return "substitution"
    if "timeout" in a:
        return "timeout"
    if "jump ball" in a:
        return "jump_ball"
    if "period" in a and "start" in s:
        return "period_start"
    if "period" in a and "end" in s:
        return "period_end"
    return a.replace(" ", "_") or "unknown"


class HistoricalLoader:
    """
    Bulk loads historical play-by-play data into the database.

    Rate limiting:
        nba_api is unofficial — uses ~0.65s delay between game requests.
        CBBpy scrapes ESPN — uses ~1.5s delay.
    """

    def __init__(self, db_path: str, delay_seconds: float = 3.0) -> None: # bumped from delay of 0.65
        self.db_path = db_path
        self.delay = delay_seconds

    # ------------------------------------------------------------------
    # NBA
    # ------------------------------------------------------------------

    def load_nba_season(
        self,
        season: str,
        team_filter: Optional[list[str]] = None,
        season_type: str = "Regular Season",
    ) -> int:
        """
        Load a full NBA season of play-by-play data.

        Populates the teams, games, and play_by_play tables.

        Args:
            season: Season string, e.g. '2024-25'
            team_filter: Optional list of team abbreviations to limit the load
            season_type: 'Regular Season', 'Playoffs', or 'All Star'

        Returns:
            Number of games successfully loaded
        """
        from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3
        from nba_api.stats.static import teams as nba_teams_static

        logger.info("Loading NBA %s %s...", season_type, season)

        # Seed teams table
        self._seed_nba_teams()
        time.sleep(self.delay)

        # Build a lookup: abbreviation → team_id (from static data)
        all_teams = pd.DataFrame(nba_teams_static.get_teams())
        abbrev_to_id = dict(zip(all_teams["abbreviation"], all_teams["id"].astype(str)))

        # Get all games for the season
        logger.info("Fetching game list...")
        finder = leaguegamefinder.LeagueGameFinder(
            season_nullable=season,
            league_id_nullable="00",
            season_type_nullable=season_type,
            timeout=30,
        )
        games_df = finder.get_data_frames()[0]
        time.sleep(self.delay)

        # Each game appears twice (once per team). Keep home games only.
        # MATCHUP: 'LAL vs. GSW' = home, 'LAL @ GSW' = away
        home_games = games_df[games_df["MATCHUP"].str.contains(r"vs\.", na=False)].copy()
        logger.info("Found %d games for NBA %s", len(home_games), season)

        games_loaded = 0
        games_failed = 0

        for _, row in home_games.iterrows():
            game_id = str(row["GAME_ID"])
            home_team_id = str(row["TEAM_ID"])
            home_abbrev = str(row["TEAM_ABBREVIATION"])
            game_date = str(row["GAME_DATE"])[:10]  # YYYY-MM-DD
            matchup = str(row["MATCHUP"])

            # Parse away team abbreviation: 'LAL vs. GSW' → 'GSW'
            away_match = re.search(r"vs\. ([A-Z]+)", matchup)
            away_team_id = abbrev_to_id.get(away_match.group(1)) if away_match else None

            # Upsert game record (even if we skip PBP for this game)
            queries.upsert_game(
                self.db_path, game_id=game_id, league="NBA", season=season,
                game_date=game_date, home_team_id=home_team_id,
                away_team_id=away_team_id, status="final",
            )

            # Apply optional team filter (skip PBP but keep game record)
            if team_filter and home_abbrev not in team_filter:
                continue

            # Skip if PBP already loaded (resumable)
            existing = queries.get_play_by_play(self.db_path, game_id)
            if not existing.empty:
                logger.debug("Game %s already loaded, skipping", game_id)
                games_loaded += 1
                continue

            # Fetch play-by-play
            logger.info("  %s | %s | %s", game_id, matchup, game_date)
            try:
                pbp_raw = playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=60) # increased the timeout to 60 seconds
                pbp_df = pbp_raw.get_data_frames()[0]
            except Exception as exc:
                logger.warning("  Failed to fetch PBP for %s: %s", game_id, exc)
                games_failed += 1
                time.sleep(self.delay * 2)
                continue

            if pbp_df.empty:
                logger.warning("  Empty PBP for game %s", game_id)
                games_failed += 1
                time.sleep(self.delay)
                continue

            # Normalize and insert
            events = self._normalize_nba_pbp(pbp_df, game_id)
            if events:
                queries.insert_play_by_play_batch(self.db_path, events)
                self._update_final_score_from_pbp(events, game_id)
                games_loaded += 1
                logger.info("  ✓ %d events", len(events))
            else:
                games_failed += 1

            time.sleep(self.delay)

        logger.info(
            "Done. %d loaded, %d failed (out of %d total).",
            games_loaded, games_failed, len(home_games),
        )
        return games_loaded

    def _seed_nba_teams(self) -> None:
        """Populate the teams table with NBA team data from nba_api static data."""
        from nba_api.stats.static import teams as nba_teams_static

        all_teams = nba_teams_static.get_teams()
        for t in all_teams:
            queries.upsert_team(
                self.db_path,
                team_id=str(t["id"]),
                league="NBA",
                name=t["full_name"],
                abbreviation=t["abbreviation"],
            )
        logger.info("Seeded %d NBA teams", len(all_teams))

    def _normalize_nba_pbp(self, df: pd.DataFrame, game_id: str) -> list[dict]:
        """
        Normalize a nba_api PlayByPlayV3 DataFrame into our play_by_play schema.

        V3 column names (differ from V2):
          clock      → ISO 8601 string, e.g. 'PT05M32.00S'  (parse_game_clock handles this)
          period     → quarter number
          scoreHome  → home score as string, empty on non-scoring events
          scoreAway  → away score as string, empty on non-scoring events
          actionType → free-text event type (e.g. 'Field Goal', 'Rebound')
          subType    → sub-classification (e.g. 'Jump Shot', 'start', 'end')
          description → single combined description string
          actionNumber → event ordering index
          teamId     → scoring team ID (populated on scoring events)
        """
        df = df.copy()

        # Forward-fill scores (only populated on scoring events)
        df["scoreHome"] = df["scoreHome"].replace("", None).ffill()
        df["scoreAway"] = df["scoreAway"].replace("", None).ffill()

        events = []
        for _, row in df.iterrows():
            # -- Scores --
            home_score, away_score, margin = None, None, None
            try:
                h = str(row.get("scoreHome") or "").strip()
                a = str(row.get("scoreAway") or "").strip()
                if h and a and h != "nan" and a != "nan":
                    home_score = int(h)
                    away_score = int(a)
                    margin = home_score - away_score # important to note -- margin = home - away
            except (ValueError, TypeError):
                pass

            # -- Clock & elapsed time --
            # V3 clock is ISO 8601: 'PT05M32.00S'
            game_clock = str(row.get("clock") or "").strip() or None
            quarter = int(row.get("period") or 1)
            elapsed = None
            if game_clock and game_clock not in ("", "nan"):
                try:
                    elapsed = compute_elapsed_minutes(quarter, game_clock)
                except ValueError:
                    pass

            # -- Event type --
            event_type = _map_action_type(
                str(row.get("actionType") or ""),
                str(row.get("subType") or ""),
            )

            # -- Description --
            description = str(row.get("description") or "").strip() or None
            if description == "nan":
                description = None

            # -- Scoring team --
            team_id = str(row.get("teamId") or "").strip() or None
            if team_id in ("0", "nan", ""):
                team_id = None

            events.append({
                "game_id": game_id,
                "event_index": int(row.get("actionId") or 0),
                "quarter": quarter,
                "game_clock": game_clock,
                "elapsed_minutes": elapsed,
                "event_type": event_type,
                "description": description,
                "home_score": home_score,
                "away_score": away_score,
                "score_margin": margin,
                "scoring_team_id": team_id,
            })

        return events

    def _update_final_score_from_pbp(self, events: list[dict], game_id: str) -> None:
        """Update games table with final score from the last scored event in PBP."""
        for event in reversed(events):
            if event["home_score"] is not None and event["away_score"] is not None:
                queries.update_game_final_score(
                    self.db_path, game_id,
                    home_final_score=event["home_score"],
                    away_final_score=event["away_score"],
                )
                return

    # ------------------------------------------------------------------
    # NCAAW
    # ------------------------------------------------------------------

    def load_ncaaw_season(
        self,
        season: str,
        team_filter: Optional[list[str]] = None,
    ) -> int:
        """
        Load a full NCAAW season of play-by-play data using CBBpy.

        TODO: implement using cbbpy.womens_scraper
        """
        raise NotImplementedError(
            "NCAAW loader not yet implemented. "
            "Coming after NBA baseline is established."
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Load historical play-by-play data")
    parser.add_argument("--league", required=True, choices=["NBA", "NCAAW"])
    parser.add_argument("--season", required=True, help="e.g. 2024-25")
    parser.add_argument("--db-path", default="data/quant_lab.db")
    parser.add_argument("--teams", nargs="+", help="Optional: limit to these team abbreviations")
    args = parser.parse_args()

    loader = HistoricalLoader(db_path=args.db_path)

    if args.league == "NBA":
        count = loader.load_nba_season(args.season, team_filter=args.teams)
    else:
        count = loader.load_ncaaw_season(args.season, team_filter=args.teams)

    print(f"\nLoaded {count} games.")
