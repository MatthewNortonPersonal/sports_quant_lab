"""
NBA live game state poller.

Triggered by Kalshi WebSocket updates (not a fixed-interval timer).
Fetches current score, clock, quarter from nba_api live endpoints and
writes a paired snapshot to the live_snapshots table.
"""

import asyncio
import logging
from typing import Optional

from infra.db import queries
from infra.nba.utils import compute_elapsed_minutes, score_margin, time_remaining_minutes

logger = logging.getLogger(__name__)


class NBALivePoller:
    """
    Polls nba_api for live game state on demand.

    Designed to be called by the orchestrator each time a Kalshi orderbook
    update arrives, so that every live_snapshot row has a tightly paired
    market price and game state.
    """

    def __init__(self, db_path: str) -> None:
        """
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path

    async def get_game_state(self, nba_game_id: str) -> Optional[dict]:
        """
        Fetch the current live state for an NBA game.

        Args:
            nba_game_id: NBA game ID (10-digit string from nba_api)

        Returns:
            Dict with keys: quarter, game_clock, elapsed_minutes,
            time_remaining, home_score, away_score, score_margin
            Or None if the game is not found / not live.

        TODO: implement using nba_api.live.nba.endpoints.boxscore.BoxScore
        """
        raise NotImplementedError("NBA live poller not yet implemented")

    async def poll_and_write(
        self,
        nba_game_id: str,
        db_game_id: str,
        kalshi_ticker: str,
        kalshi_mid: float,
        kalshi_bid: Optional[float],
        kalshi_ask: Optional[float],
        timestamp: str,
    ) -> None:
        """
        Fetch live game state and write a paired snapshot to the database.

        Called by the orchestrator on each Kalshi WS update.

        Args:
            nba_game_id: NBA game ID for the live API call
            db_game_id: Game ID as stored in our database (may differ)
            kalshi_ticker: The Kalshi market ticker that triggered this poll
            kalshi_mid/bid/ask: Current Kalshi market prices
            timestamp: ISO timestamp of the Kalshi update
        """
        game_state = await self.get_game_state(nba_game_id)
        if game_state is None:
            logger.warning("No live state returned for game %s", nba_game_id)
            return

        queries.insert_live_snapshot(
            db_path=self.db_path,
            game_id=db_game_id,
            timestamp=timestamp,
            quarter=game_state["quarter"],
            game_clock=game_state["game_clock"],
            elapsed_minutes=game_state["elapsed_minutes"],
            home_score=game_state["home_score"],
            away_score=game_state["away_score"],
            score_margin=game_state["score_margin"],
            kalshi_ticker=kalshi_ticker,
            kalshi_mid=kalshi_mid,
            kalshi_bid=kalshi_bid,
            kalshi_ask=kalshi_ask,
            # Model fields filled in by orchestrator after model evaluation
            model_win_prob=None,
            model_sigma=None,
            model_drift=None,
            edge=None,
        )
