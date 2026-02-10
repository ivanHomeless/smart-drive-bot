from unittest.mock import AsyncMock, MagicMock

from aiogram.types import CallbackQuery

from src.bot.handlers.errors import stale_callback_handler


async def test_stale_callback_shows_alert():
    cb = MagicMock(spec=CallbackQuery)
    cb.data = "some:old:data"
    cb.answer = AsyncMock()

    await stale_callback_handler(cb)

    cb.answer.assert_called_once_with("Кнопка больше не активна", show_alert=True)
