import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message

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


@router.message()
async def unexpected_content_handler(message: Message, state: FSMContext) -> None:
    """Catch-all for unexpected messages (stickers, voice, etc.) during dialogs."""
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "Пожалуйста, используйте текст или кнопки для ответа."
        )
    # If no state, silently ignore (user might be sending random messages)


@router.callback_query()
async def stale_callback_handler(callback: CallbackQuery) -> None:
    """Catch-all for stale/unhandled callback queries."""
    await callback.answer("Кнопка больше не активна", show_alert=True)
