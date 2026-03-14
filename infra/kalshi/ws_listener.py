"""
Kalshi WebSocket listener.

Subscribes to orderbook channels for active NBA game markets and streams
price updates to the orchestrator in real time.

WebSocket endpoint: wss://trading-api.kalshi.com/trade-api/ws/v2
Protocol docs: https://trading-api.kalshi.com/trade-api/v2/openapi.json
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Optional

logger = logging.getLogger(__name__)

KALSHI_WS_URL = {
    "prod": "wss://trading-api.kalshi.com/trade-api/ws/v2",
    "demo": "wss://demo-api.kalshi.co/trade-api/ws/v2",
}


class KalshiWebSocketListener:
    """
    Async WebSocket listener for Kalshi orderbook updates.

    Usage:
        listener = KalshiWebSocketListener(api_key_id, private_key_path, env="demo")
        await listener.run(on_update=handle_update)

    The on_update callback receives a dict with keys:
        ticker, bid, ask, mid, last_price, volume, timestamp
    """

    def __init__(
        self,
        api_key_id: str,
        private_key_path: str,
        env: str = "demo",
    ) -> None:
        """
        Args:
            api_key_id: Kalshi API key ID
            private_key_path: Path to RSA private key .pem file
            env: 'demo' or 'prod'
        """
        self.api_key_id = api_key_id
        self.private_key_path = private_key_path
        self.ws_url = KALSHI_WS_URL[env]
        self._subscribed_tickers: list[str] = []

    async def connect(self) -> None:
        """
        Establish WebSocket connection and authenticate.

        TODO: implement RSA-signed auth handshake per Kalshi WS docs.
        """
        raise NotImplementedError("Kalshi WS auth not yet implemented")

    async def subscribe(self, tickers: list[str]) -> None:
        """
        Subscribe to orderbook channels for the given market tickers.

        Args:
            tickers: List of Kalshi market tickers to subscribe to
        """
        raise NotImplementedError

    async def run(self, on_update: Callable[[dict], None]) -> None:
        """
        Main listen loop. Runs until cancelled.

        Connects, subscribes to all active NBA game markets, then calls
        on_update() for every orderbook delta received.

        Reconnects automatically on disconnect with exponential backoff.

        Args:
            on_update: Async or sync callable that receives an orderbook update dict.
        """
        raise NotImplementedError

    async def _reconnect_loop(self, on_update: Callable[[dict], None]) -> None:
        """Handle reconnection with exponential backoff."""
        delay = 1.0
        while True:
            try:
                await self.connect()
                await self.run(on_update)
            except Exception as exc:
                logger.warning("WebSocket disconnected: %s. Retrying in %.1fs", exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60.0)
