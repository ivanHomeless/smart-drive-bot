"""Tests for edge cases: stale callbacks, unexpected content, /start mid-dialog."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.errors import stale_callback_handler, unexpected_content_handler
from src.bot.handlers.start import cmd_start, confirm_reset_yes, confirm_reset_no
from src.bot.states.sell import SellStates


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def make_state(
    storage: MemoryStorage,
    state_value: str | None = None,
    data: dict | None = None,
) -> FSMContext:
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    ctx = FSMContext(storage=storage, key=key)
    if state_value:
        await ctx.set_state(state_value)
    if data:
        await ctx.update_data(**data)
    return ctx


def make_callback(data: str) -> CallbackQuery:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.message = MagicMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.delete = AsyncMock()
    cb.answer = AsyncMock()
    cb.from_user = MagicMock()
    cb.from_user.id = 123
    return cb


def make_message(text: str | None = None) -> Message:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123
    return msg


# ---------------------------------------------------------------
# Stale callbacks
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_stale_callback_shows_alert():
    """Stale callback -> alert message."""
    cb = make_callback("some:old:callback")
    await stale_callback_handler(cb)
    cb.answer.assert_called_once_with("Кнопка больше не активна", show_alert=True)


# ---------------------------------------------------------------
# Unexpected content
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_unexpected_content_in_dialog():
    """Unexpected message during active dialog -> warning."""
    storage = MemoryStorage()
    state = await make_state(storage, state_value=SellStates.car_brand.state)
    msg = make_message()  # No text, simulating sticker/voice

    await unexpected_content_handler(msg, state)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "текст или кнопки" in call_text


@pytest.mark.asyncio
async def test_unexpected_content_no_state_ignored():
    """Unexpected message with no active state -> silently ignored."""
    storage = MemoryStorage()
    state = await make_state(storage)
    msg = make_message()

    await unexpected_content_handler(msg, state)

    msg.answer.assert_not_called()


# ---------------------------------------------------------------
# /start mid-dialog
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_mid_dialog_shows_warning():
    """/start during active dialog -> reset warning."""
    storage = MemoryStorage()
    state = await make_state(storage, state_value=SellStates.car_brand.state)
    msg = make_message("/start")

    await cmd_start(msg, state)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "незавершённый диалог" in call_text

    # State NOT cleared yet
    current = await state.get_state()
    assert current == SellStates.car_brand.state


@pytest.mark.asyncio
async def test_start_no_dialog_shows_menu():
    """/start with no active state -> main menu."""
    storage = MemoryStorage()
    state = await make_state(storage)
    msg = make_message("/start")

    await cmd_start(msg, state)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "Добро пожаловать" in call_text


@pytest.mark.asyncio
async def test_confirm_reset_yes_clears_state():
    """Confirming reset clears state and shows menu."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.car_brand.state,
        data={"car_brand": "BMW"},
    )
    cb = make_callback("confirm_reset:yes")

    await confirm_reset_yes(cb, state)

    current = await state.get_state()
    assert current is None
    data = await state.get_data()
    assert data == {}

    cb.message.answer.assert_called_once()
    call_text = cb.message.answer.call_args[0][0]
    assert "Добро пожаловать" in call_text


@pytest.mark.asyncio
async def test_confirm_reset_no_continues():
    """Declining reset keeps state and deletes warning."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.car_brand.state,
        data={"car_brand": "BMW"},
    )
    cb = make_callback("confirm_reset:no")

    await confirm_reset_no(cb)

    cb.message.delete.assert_called_once()
    cb.answer.assert_called_once_with("Продолжаем текущий диалог")

    # State preserved
    current = await state.get_state()
    assert current == SellStates.car_brand.state
