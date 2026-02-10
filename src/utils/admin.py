import logging

from aiogram import Bot

from src.config import settings

logger = logging.getLogger(__name__)


async def notify_admin(bot: Bot, text: str) -> None:
    """Send a notification message to the admin chat."""
    if not settings.ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID not set, skipping admin notification")
        return

    try:
        await bot.send_message(chat_id=settings.ADMIN_CHAT_ID, text=text)
    except Exception:
        logger.exception("Failed to send admin notification")
