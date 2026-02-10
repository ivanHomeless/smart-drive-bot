import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """In-memory per-user rate limiter.

    Drops updates from users who send more than `rate_limit` updates
    within `period` seconds.
    """

    def __init__(self, rate_limit: int = 5, period: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self.period = period
        self._user_timestamps: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        user_id = user.id
        now = time.monotonic()

        timestamps = self._user_timestamps.get(user_id, [])
        # Remove timestamps outside the current window
        timestamps = [ts for ts in timestamps if now - ts < self.period]
        timestamps.append(now)
        self._user_timestamps[user_id] = timestamps

        if len(timestamps) > self.rate_limit:
            return None  # Silently drop the update

        return await handler(event, data)
