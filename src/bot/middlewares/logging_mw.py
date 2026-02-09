import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        user = data.get("event_from_user")
        user_id = user.id if user else "unknown"
        update_type = type(event).__name__

        logger.info("Update %s from user %s", update_type, user_id)

        try:
            result = await handler(event, data)
            duration = (time.monotonic() - start) * 1000
            logger.info("Update %s from user %s handled in %.1fms", update_type, user_id, duration)
            return result
        except Exception:
            duration = (time.monotonic() - start) * 1000
            logger.exception("Update %s from user %s failed after %.1fms", update_type, user_id, duration)
            raise
