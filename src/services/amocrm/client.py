from __future__ import annotations

import logging
from typing import Any

import aiohttp

from src.services.amocrm.auth import AmoCRMAuth

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class AmoCRMError(Exception):
    """Base exception for AmoCRM API errors."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


class AmoCRMClient:
    """HTTP client for AmoCRM API v4."""

    def __init__(self, auth: AmoCRMAuth) -> None:
        self._auth = auth

    async def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        params: dict | None = None,
    ) -> dict:
        """Make an authenticated request to AmoCRM API with retry logic.

        Retries on 429, 5xx. On 401, refreshes token and retries once.
        """
        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            token = await self._auth.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        f"{self._auth.base_url}{path}",
                        json=json,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    ) as resp:
                        if resp.status in (200, 201, 204):
                            if resp.status == 204:
                                return {}
                            return await resp.json()

                        body = await resp.text()

                        if resp.status == 401 and attempt < max_attempts:
                            logger.warning(
                                "AmoCRM 401 on %s %s, refreshing token (attempt %d)",
                                method, path, attempt,
                            )
                            await self._auth.handle_401()
                            continue

                        if resp.status == 429 and attempt < max_attempts:
                            logger.warning(
                                "AmoCRM 429 on %s %s, retrying (attempt %d)",
                                method, path, attempt,
                            )
                            import asyncio
                            await asyncio.sleep(2 ** (attempt - 1))
                            continue

                        if resp.status >= 500 and attempt < max_attempts:
                            logger.warning(
                                "AmoCRM %d on %s %s, retrying (attempt %d)",
                                resp.status, method, path, attempt,
                            )
                            import asyncio
                            await asyncio.sleep(2 ** (attempt - 1))
                            continue

                        last_error = AmoCRMError(
                            f"AmoCRM API error: {resp.status} {body}",
                            status=resp.status,
                        )
                        raise last_error

            except aiohttp.ClientError as exc:
                last_error = exc
                if attempt < max_attempts:
                    logger.warning(
                        "AmoCRM connection error on %s %s: %s (attempt %d)",
                        method, path, exc, attempt,
                    )
                    import asyncio
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise AmoCRMError(f"AmoCRM connection error: {exc}") from exc

        if last_error:
            raise last_error
        raise AmoCRMError("Unexpected error in AmoCRM client")

    async def get(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> dict:
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: Any = None) -> dict:
        return await self._request("PATCH", path, json=json)
