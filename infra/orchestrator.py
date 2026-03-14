"""
Main orchestrator — wires together Kalshi WS, NBA live poller, and model evaluation.

Entry point for the live data pipeline.

Flow:
    1. Connect to Kalshi WebSocket for active NBA game markets
    2. On each price update, poll NBA live game state
    3. Run model evaluation (win_probability)
    4. Write paired snapshot to live_snapshots
    5. Log edge signal if abs(edge) > threshold

Usage:
    python -m infra.orchestrator
    python -m infra.orchestrator --env demo --edge-threshold 0.05
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from infra.kalshi.ws_listener import KalshiWebSocketListener
from infra.nba.live_poller import NBALivePoller

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Ties together the Kalshi WS listener, NBA live poller, and model evaluation.

    All operations are async. The run() method is the main entry point.
    """

    def __init__(
        self,
        db_path: str,
        api_key_id: str,
        private_key_path: str,
        env: str = "demo",
        edge_threshold: float = 0.05,
        sigma: float = 1.7,
    ) -> None:
        """
        Args:
            db_path: Path to the SQLite database
            api_key_id: Kalshi API key ID
            private_key_path: Path to RSA private key
            env: 'demo' or 'prod' — NEVER use 'prod' without explicit authorization
            edge_threshold: Minimum abs(edge) to log as a signal
            sigma: Volatility parameter from model calibration
        """
        self.db_path = db_path
        self.edge_threshold = edge_threshold
        self.sigma = sigma

        self.ws_listener = KalshiWebSocketListener(api_key_id, private_key_path, env)
        self.nba_poller = NBALivePoller(db_path)

    async def handle_kalshi_update(self, update: dict) -> None:
        """
        Process a single Kalshi orderbook update.

        Called by the WS listener for every price tick.

        TODO: Implement model evaluation and edge computation.
        """
        raise NotImplementedError("Orchestrator.handle_kalshi_update not yet implemented")

    async def run(self) -> None:
        """
        Start the live pipeline. Runs indefinitely until interrupted.

        IMPORTANT: Only run with KALSHI_ENV=demo until model is validated
        and David explicitly authorizes live trading.
        """
        logger.info("Starting orchestrator (env=%s)", self.ws_listener.ws_url)
        await self.ws_listener.run(on_update=self.handle_kalshi_update)


async def _main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run the live data pipeline")
    parser.add_argument("--env", default=None, help="Override KALSHI_ENV (.env)")
    parser.add_argument("--db-path", default=None, help="Override DB_PATH (.env)")
    parser.add_argument("--edge-threshold", type=float, default=0.05)
    args = parser.parse_args()

    load_dotenv()

    env = args.env or os.getenv("KALSHI_ENV", "demo")
    db_path = args.db_path or os.getenv("DB_PATH", "data/quant_lab.db")
    api_key_id = os.environ["KALSHI_API_KEY_ID"]
    private_key_path = os.environ["KALSHI_PRIVATE_KEY_PATH"]

    if env == "prod":
        logger.warning(
            "PROD MODE — real money is at risk. Ctrl-C to abort. Starting in 5s..."
        )
        await asyncio.sleep(5)

    orchestrator = Orchestrator(
        db_path=db_path,
        api_key_id=api_key_id,
        private_key_path=private_key_path,
        env=env,
        edge_threshold=args.edge_threshold,
    )
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(_main())
