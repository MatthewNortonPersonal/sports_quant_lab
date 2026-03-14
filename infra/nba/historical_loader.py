"""
Historical play-by-play data loader.

Supports both NBA (via nba_api) and NCAAW (via CBBpy).
Normalizes both into the same play_by_play table schema.

Usage:
    python -m infra.nba.historical_loader --league NBA --season 2024-25
    python -m infra.nba.historical_loader --league NCAAW --season 2024-25
    python -m infra.nba.historical_loader --league NBA --season 2024-25 --backfill 3
"""

import argparse
import logging
import time
from typing import Optional

from infra.db import queries
from infra.nba.utils import compute_elapsed_minutes, score_margin

logger = logging.getLogger(__name__)


class HistoricalLoader:
    """
    Bulk loads historical play-by-play data into the database.

    Rate limiting:
        nba_api is unofficial — add ~0.5s delay between game requests.
        CBBpy scrapes ESPN — add ~1s delay and cache aggressively.
    """

    def __init__(self, db_path: str, delay_seconds: float = 0.6) -> None:
        """
        Args:
            db_path: Path to the SQLite database
            delay_seconds: Delay between API/scrape requests to avoid rate limits
        """
        self.db_path = db_path
        self.delay = delay_seconds

    def load_nba_season(
        self,
        season: str,
        team_filter: Optional[list[str]] = None,
    ) -> int:
        """
        Load a full NBA season of play-by-play data.

        Uses nba_api PlayByPlayV2 endpoint. Populates the games, teams,
        and play_by_play tables.

        Args:
            season: Season string, e.g. '2024-25'
            team_filter: Optional list of team abbreviations to limit the load

        Returns:
            Number of games successfully loaded

        TODO: implement using nba_api.stats.endpoints.leaguegamefinder and
              nba_api.stats.endpoints.playbyplayv2.PlayByPlayV2
        """
        raise NotImplementedError(
            "NBA historical loader not yet implemented. "
            "See README for endpoint details."
        )

    def load_ncaaw_season(
        self,
        season: str,
        team_filter: Optional[list[str]] = None,
    ) -> int:
        """
        Load a full NCAAW season of play-by-play data.

        Uses CBBpy Scraper.get_game_pbp(). Populates the same tables as
        load_nba_season(), normalized to the same schema.

        Args:
            season: Season string, e.g. '2024-25'
            team_filter: Optional list of team names to limit the load

        Returns:
            Number of games successfully loaded

        TODO: implement using cbbpy.womens_scraper.get_game_pbp()
        Be respectful of rate limits — ESPN blocks aggressive scrapers.
        """
        raise NotImplementedError(
            "NCAAW historical loader not yet implemented. "
            "See README for CBBpy details."
        )

    def _normalize_nba_pbp_row(self, row: dict, game_id: str) -> dict:
        """
        Normalize a single nba_api PBP row to our schema.

        Returns a dict matching the play_by_play table columns (excluding id).
        """
        raise NotImplementedError

    def _normalize_ncaaw_pbp_row(self, row: dict, game_id: str) -> dict:
        """
        Normalize a single CBBpy PBP row to our schema.

        Returns a dict matching the play_by_play table columns (excluding id).
        """
        raise NotImplementedError


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Load historical play-by-play data")
    parser.add_argument("--league", required=True, choices=["NBA", "NCAAW"])
    parser.add_argument("--season", required=True, help="e.g. 2024-25")
    parser.add_argument("--db-path", default="data/quant_lab.db")
    parser.add_argument(
        "--backfill",
        type=int,
        default=1,
        metavar="N",
        help="Load this many seasons back from --season (default 1)",
    )
    args = parser.parse_args()

    loader = HistoricalLoader(db_path=args.db_path)
    if args.league == "NBA":
        count = loader.load_nba_season(args.season)
    else:
        count = loader.load_ncaaw_season(args.season)

    print(f"Loaded {count} games for {args.league} {args.season}")
