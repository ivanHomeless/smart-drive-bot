import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import Chat, Message, User

from src.bot.handlers.start import cmd_start, cmd_help, cmd_menu
from src.bot.keyboards.main_menu import WELCOME_TEXT, HELP_TEXT, RESET_WARNING_TEXT


def make_message(text: str = "/start") -> Message:
    user = User(id=123, is_bot=False, first_name="Test")
    chat = Chat(id=123, type="private")
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.from_user = user
    msg.chat = chat
    msg.answer = AsyncMock()
    return msg


async def make_state(storage: MemoryStorage, state_value: str | None = None) -> FSMContext:
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    state = FSMContext(storage=storage, key=key)
    if state_value:
        await state.set_state(state_value)
    return state


@pytest.mark.asyncio
async def test_start_shows_welcome_and_menu():
    storage = MemoryStorage()
    state = await make_state(storage)
    msg = make_message("/start")

    await cmd_start(msg, state)

    msg.answer.assert_called_once()
    args, kwargs = msg.answer.call_args
    assert args[0] == WELCOME_TEXT
    assert "reply_markup" in kwargs
    keyboard = kwargs["reply_markup"]
    buttons = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert len(buttons) == 6
    assert "Продать авто" in buttons
    assert "Купить авто" in buttons
    assert "Подбор авто" in buttons
    assert "Проверка авто" in buttons
    assert "Юридическая помощь" in buttons
    assert "Задать вопрос" in buttons


@pytest.mark.asyncio
async def test_start_mid_dialog_shows_warning():
    storage = MemoryStorage()
    state = await make_state(storage, state_value="SomeState:step1")
    msg = make_message("/start")

    await cmd_start(msg, state)

    msg.answer.assert_called_once()
    args, kwargs = msg.answer.call_args
    assert args[0] == RESET_WARNING_TEXT
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_help_shows_help_text():
    msg = make_message("/help")
    await cmd_help(msg)
    msg.answer.assert_called_once_with(HELP_TEXT)


@pytest.mark.asyncio
async def test_menu_no_dialog_shows_menu():
    storage = MemoryStorage()
    state = await make_state(storage)
    msg = make_message("/menu")

    await cmd_menu(msg, state)

    msg.answer.assert_called_once()
    args, kwargs = msg.answer.call_args
    assert args[0] == WELCOME_TEXT


@pytest.mark.asyncio
async def test_menu_mid_dialog_shows_warning():
    storage = MemoryStorage()
    state = await make_state(storage, state_value="SomeState:step1")
    msg = make_message("/menu")

    await cmd_menu(msg, state)

    msg.answer.assert_called_once()
    args, kwargs = msg.answer.call_args
    assert args[0] == RESET_WARNING_TEXT
