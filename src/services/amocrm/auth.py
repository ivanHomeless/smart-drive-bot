from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp

from src.config import settings
from src.db.models import AmoToken

logger = logging.getLogger(__name__)

# Refresh token when less than this many seconds until expiry
REFRESH_MARGIN_SECONDS = 300  # 5 minutes


class AmoCRMAuth:
    """Manages AmoCRM OAuth tokens.

    - Caches current token in memory
    - Refreshes lazily (before each request if about to expire)
    - Persists new tokens to DB (each refresh_token is single-use)
    - Uses asyncio.Lock to prevent concurrent refresh races
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._refresh_token: str | None = None
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        return f"https://{settings.AMOCRM_SUBDOMAIN}.amocrm.ru"

    async def get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        async with self._lock:
            if self._access_token and self._expires_at:
                now = datetime.now(timezone.utc)
                if now < self._expires_at - timedelta(seconds=REFRESH_MARGIN_SECONDS):
                    return self._access_token

            # Try to load from DB if not in memory
            if not self._refresh_token:
                await self._load_from_db()

            # If we have a refresh token and it's close to expiry, refresh
            if self._refresh_token:
                if not self._access_token or not self._expires_at or \
                   datetime.now(timezone.utc) >= self._expires_at - timedelta(seconds=REFRESH_MARGIN_SECONDS):
                    await self._refresh()

            if not self._access_token:
                raise RuntimeError(
                    "No AmoCRM token available. Run scripts/setup_amocrm.py first."
                )

            return self._access_token

    async def handle_401(self) -> None:
        """Force token refresh on 401 response."""
        async with self._lock:
            logger.warning("Forcing token refresh due to 401")
            if self._refresh_token:
                await self._refresh()
            else:
                await self._load_from_db()
                if self._refresh_token:
                    await self._refresh()

    async def _load_from_db(self) -> None:
        """Load the latest token from the database."""
        from src.db.repositories.token import TokenRepository

        async with self._session_factory() as session:
            repo = TokenRepository(session)
            token = await repo.get_current()
            if token:
                self._access_token = token.access_token
                self._refresh_token = token.refresh_token
                self._expires_at = token.expires_at
                if self._expires_at.tzinfo is None:
                    self._expires_at = self._expires_at.replace(tzinfo=timezone.utc)
                logger.info("Loaded AmoCRM token from DB, expires at %s", self._expires_at)

    async def _refresh(self) -> None:
        """Exchange refresh_token for a new token pair and save to DB."""
        logger.info("Refreshing AmoCRM token")

        payload = {
            "client_id": settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "redirect_uri": settings.AMOCRM_REDIRECT_URI,
        }

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                f"{self.base_url}/oauth2/access_token",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(
                        "Token refresh failed: status=%d body=%s",
                        resp.status, body,
                    )
                    raise RuntimeError(f"AmoCRM token refresh failed: {resp.status}")

                data = await resp.json()

        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        self._expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=data["expires_in"]
        )

        # Persist to DB
        await self._save_to_db()
        logger.info("AmoCRM token refreshed, expires at %s", self._expires_at)

    async def _save_to_db(self) -> None:
        """Save the current token pair to database."""
        from src.db.repositories.token import TokenRepository

        async with self._session_factory() as session:
            repo = TokenRepository(session)
            token = AmoToken(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                expires_at=self._expires_at,
            )
            await repo.save(token)
            await session.commit()
