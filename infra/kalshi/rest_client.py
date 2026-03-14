"""
Kalshi REST API client.

Handles authentication, market lookup, and order placement.
Uses key-based auth (RSA private key), not username/password.

References:
    https://trading-api.kalshi.com/trade-api/v2/openapi.json
"""

import httpx
from typing import Optional


KALSHI_BASE_URL = {
    "prod": "https://trading-api.kalshi.com/trade-api/v2",
    "demo": "https://demo-api.kalshi.co/trade-api/v2",
}


class KalshiRestClient:
    """
    Thin async wrapper around the Kalshi REST API.

    All methods that touch the API require the client to be authenticated first.
    Call authenticate() before any other method.
    """

    def __init__(self, api_key_id: str, private_key_path: str, env: str = "demo") -> None:
        """
        Args:
            api_key_id: Kalshi API key ID (from account dashboard)
            private_key_path: Path to the RSA private key .pem file
            env: 'demo' or 'prod'
        """
        self.api_key_id = api_key_id
        self.private_key_path = private_key_path
        self.base_url = KALSHI_BASE_URL[env]
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def authenticate(self) -> None:
        """
        Authenticate with Kalshi using RSA key-based auth.
        Stores the session token for subsequent requests.

        TODO: implement RSA signing of the login payload per Kalshi docs.
        """
        raise NotImplementedError("Kalshi REST auth not yet implemented")

    async def get_active_markets(self, event_ticker: str) -> list[dict]:
        """
        Fetch all active markets for a given event ticker.

        Args:
            event_ticker: e.g. 'NBA-2025-LAL-vs-GSW'

        Returns:
            List of market dicts with ticker, yes_bid, yes_ask, volume, etc.
        """
        raise NotImplementedError

    async def get_market(self, ticker: str) -> dict:
        """
        Fetch a single market by its ticker.

        Args:
            ticker: Kalshi market ticker, e.g. 'NBA-2025-LAL-GSW-SPREAD-...'

        Returns:
            Market dict with current orderbook state.
        """
        raise NotImplementedError

    async def place_order(
        self,
        ticker: str,
        side: str,
        count: int,
        order_type: str = "market",
        limit_price: Optional[int] = None,
    ) -> dict:
        """
        Place an order on Kalshi.

        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            count: Number of contracts
            order_type: 'market' or 'limit'
            limit_price: Required for limit orders (in cents, 1–99)

        Returns:
            Order confirmation dict from Kalshi API.

        IMPORTANT: Only call this after verifying KALSHI_ENV=demo in .env.
        Never place live orders without explicit authorization.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
