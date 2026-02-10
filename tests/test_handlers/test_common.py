from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.common import nav_home
from src.bot.keyboards.main_menu import WELCOME_TEXT


async def make_state(storage: MemoryStorage, state_value: str | None = None) -> FSMContext:
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    state = FSMContext(storage=storage, key=key)
    if state_value:
        await state.set_state(state_value)
    return state


def make_callback(data: str) -> CallbackQuery:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.message = MagicMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


async def test_nav_home_clears_state_and_shows_menu():
    storage = MemoryStorage()
    state = await make_state(storage, state_value="SomeState:step1")
    cb = make_callback("nav:home")

    await nav_home(cb, state)

    assert await state.get_state() is None
    cb.message.edit_text.assert_called_once()
    args, kwargs = cb.message.edit_text.call_args
    assert args[0] == WELCOME_TEXT
    assert "reply_markup" in kwargs
    cb.answer.assert_called_once()
