import logging

from aiogram import Router
from aiogram.types import CallbackQuery, ErrorEvent

logger = logging.getLogger(__name__)

router = Router()


@router.errors()
async def global_error_handler(event: ErrorEvent) -> bool:
    """Global error handler — logs the exception and suppresses propagation."""
    logger.exception(
        "Unhandled error in update %s: %s",
        event.update.update_id if event.update else "?",
        event.exception,
    )
    return True


@router.callback_query()
async def stale_callback_handler(callback: CallbackQuery) -> None:
    """Catch-all for stale/unhandled callback queries."""
    await callback.answer("Кнопка больше не активна", show_alert=True)
