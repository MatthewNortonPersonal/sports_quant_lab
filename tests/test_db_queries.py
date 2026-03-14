"""
Unit tests for infra/db/queries.py

Uses a temporary database so tests never touch data/quant_lab.db.

Run with: pytest tests/test_db_queries.py -v
"""

import pytest
import sqlite3
from pathlib import Path

from infra.db.init_db import init_db
from infra.db import queries


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    """Create and initialize a fresh temporary database for each test."""
    db_path = str(tmp_path / "test_quant_lab.db")
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Schema / init
# ---------------------------------------------------------------------------

class TestInitDb:

    def test_creates_all_tables(self, tmp_db: str) -> None:
        conn = sqlite3.connect(tmp_db)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        assert "teams" in tables
        assert "games" in tables
        assert "play_by_play" in tables
        assert "kalshi_snapshots" in tables
        assert "live_snapshots" in tables

    def test_idempotent(self, tmp_db: str) -> None:
        """Running init_db twice on the same file should not raise."""
        init_db(tmp_db)  # second call — should be safe


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeams:

    def test_upsert_and_get(self, tmp_db: str) -> None:
        queries.upsert_team(tmp_db, team_id="1610612747", league="NBA", name="Los Angeles Lakers", abbreviation="LAL")
        df = queries.get_teams(tmp_db)
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Los Angeles Lakers"

    def test_filter_by_league(self, tmp_db: str) -> None:
        queries.upsert_team(tmp_db, team_id="T1", league="NBA", name="Team A")
        queries.upsert_team(tmp_db, team_id="T2", league="NCAAW", name="Team B")

        nba = queries.get_teams(tmp_db, league="NBA")
        ncaaw = queries.get_teams(tmp_db, league="NCAAW")

        assert len(nba) == 1
        assert len(ncaaw) == 1

    def test_upsert_replaces_existing(self, tmp_db: str) -> None:
        queries.upsert_team(tmp_db, team_id="T1", league="NBA", name="Old Name")
        queries.upsert_team(tmp_db, team_id="T1", league="NBA", name="New Name")
        df = queries.get_teams(tmp_db)
        assert len(df) == 1
        assert df.iloc[0]["name"] == "New Name"


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

class TestGames:

    def _seed_team(self, db: str) -> None:
        queries.upsert_team(db, team_id="HOME", league="NBA", name="Home Team")
        queries.upsert_team(db, team_id="AWAY", league="NBA", name="Away Team")

    def test_upsert_and_get(self, tmp_db: str) -> None:
        self._seed_team(tmp_db)
        queries.upsert_game(
            tmp_db,
            game_id="G001",
            league="NBA",
            season="2024-25",
            game_date="2025-01-15",
            home_team_id="HOME",
            away_team_id="AWAY",
        )
        df = queries.get_games(tmp_db)
        assert len(df) == 1
        assert df.iloc[0]["game_id"] == "G001"

    def test_filter_by_status(self, tmp_db: str) -> None:
        self._seed_team(tmp_db)
        queries.upsert_game(tmp_db, game_id="G1", league="NBA", status="scheduled")
        queries.upsert_game(tmp_db, game_id="G2", league="NBA", status="final")

        scheduled = queries.get_games(tmp_db, status="scheduled")
        final = queries.get_games(tmp_db, status="final")

        assert len(scheduled) == 1
        assert len(final) == 1

    def test_update_final_score(self, tmp_db: str) -> None:
        self._seed_team(tmp_db)
        queries.upsert_game(tmp_db, game_id="G1", league="NBA")
        queries.update_game_final_score(tmp_db, game_id="G1", home_final_score=110, away_final_score=105)

        df = queries.get_games(tmp_db)
        row = df.iloc[0]
        assert row["home_final_score"] == 110
        assert row["away_final_score"] == 105
        assert row["status"] == "final"


# ---------------------------------------------------------------------------
# Play-by-play
# ---------------------------------------------------------------------------

class TestPlayByPlay:

    def _seed_game(self, db: str) -> str:
        queries.upsert_team(db, team_id="HOME", league="NBA", name="Home")
        queries.upsert_team(db, team_id="AWAY", league="NBA", name="Away")
        queries.upsert_game(db, game_id="G1", league="NBA", season="2024-25")
        return "G1"

    def test_insert_and_retrieve_batch(self, tmp_db: str) -> None:
        game_id = self._seed_game(tmp_db)
        events = [
            {
                "game_id": game_id,
                "event_index": i,
                "quarter": 1,
                "game_clock": "10:00",
                "elapsed_minutes": float(i),
                "event_type": "field_goal",
                "description": f"Event {i}",
                "home_score": i * 2,
                "away_score": i,
                "score_margin": i,
                "scoring_team_id": "HOME",
            }
            for i in range(5)
        ]
        count = queries.insert_play_by_play_batch(tmp_db, events)
        assert count == 5

        df = queries.get_play_by_play(tmp_db, game_id)
        assert len(df) == 5
        assert list(df["event_index"]) == list(range(5))

    def test_get_pbp_for_sigma(self, tmp_db: str) -> None:
        game_id = self._seed_game(tmp_db)
        events = [
            {
                "game_id": game_id,
                "event_index": i,
                "quarter": 1,
                "game_clock": "10:00",
                "elapsed_minutes": float(i),
                "event_type": "field_goal",
                "description": "",
                "home_score": i * 2,
                "away_score": i,
                "score_margin": i,
                "scoring_team_id": "HOME",
            }
            for i in range(3)
        ]
        queries.insert_play_by_play_batch(tmp_db, events)

        df = queries.get_play_by_play_for_sigma(tmp_db, league="NBA")
        assert "game_id" in df.columns
        assert "elapsed_minutes" in df.columns
        assert "score_margin" in df.columns
        assert len(df) == 3


# ---------------------------------------------------------------------------
# Live snapshots
# ---------------------------------------------------------------------------

class TestLiveSnapshots:

    def test_insert_and_retrieve(self, tmp_db: str) -> None:
        queries.upsert_game(tmp_db, game_id="G1", league="NBA")
        queries.insert_live_snapshot(
            db_path=tmp_db,
            game_id="G1",
            timestamp="2025-01-15T20:30:00",
            quarter=3,
            game_clock="5:00",
            elapsed_minutes=31.0,
            home_score=75,
            away_score=70,
            score_margin=5,
            kalshi_ticker="NBA-XXX-YES",
            kalshi_mid=0.65,
            kalshi_bid=0.63,
            kalshi_ask=0.67,
            model_win_prob=0.72,
            model_sigma=1.7,
            model_drift=0.0,
            edge=0.07 - 0.07 * 0.65 * 0.35,
        )

        df = queries.get_live_snapshots(tmp_db, "G1")
        assert len(df) == 1
        assert df.iloc[0]["quarter"] == 3
        assert df.iloc[0]["kalshi_mid"] == pytest.approx(0.65)

    def test_get_edge_signals(self, tmp_db: str) -> None:
        queries.upsert_game(tmp_db, game_id="G1", league="NBA")

        # Insert two snapshots: one with high edge, one with low
        for edge, game_id in [(0.08, "G1"), (0.02, "G1")]:
            queries.insert_live_snapshot(
                db_path=tmp_db,
                game_id=game_id,
                timestamp="2025-01-15T20:30:00",
                quarter=2,
                game_clock="6:00",
                elapsed_minutes=18.0,
                home_score=50,
                away_score=48,
                score_margin=2,
                kalshi_ticker="NBA-XXX-YES",
                kalshi_mid=0.55,
                kalshi_bid=0.53,
                kalshi_ask=0.57,
                edge=edge,
            )

        signals = queries.get_edge_signals(tmp_db, min_abs_edge=0.05)
        assert len(signals) == 1
        assert signals.iloc[0]["edge"] == pytest.approx(0.08)
