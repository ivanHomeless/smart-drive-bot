"""Tests for the Find branch."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.find import find_handler
from src.bot.states.find import FindStates


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
    cb.message.answer = AsyncMock()
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


def test_find_has_7_steps():
    assert len(find_handler.steps) == 7


@pytest.mark.asyncio
async def test_find_entry():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:find")

    await find_handler._on_entry(cb, state)

    assert await state.get_state() == FindStates.purpose.state


@pytest.mark.asyncio
async def test_find_happy_path():
    storage = MemoryStorage()
    state = await make_state(storage)
    h = find_handler

    await h._on_entry(make_callback("service:find"), state)

    # purpose (button)
    cb = make_callback("step:purpose:Для семьи")
    await h._make_button_handler(h.steps[0])(cb, state)
    assert await state.get_state() == FindStates.budget.state

    # budget (button)
    cb = make_callback("step:budget:1 000 000 - 2 000 000")
    await h._make_button_handler(h.steps[1])(cb, state)
    assert await state.get_state() == FindStates.brand_preference.state

    # brand_preference (text)
    await h._make_text_handler(h.steps[2])(make_message("Toyota"), state)
    assert await state.get_state() == FindStates.body_type.state

    # body_type (button)
    cb = make_callback("step:body_type:Кроссовер")
    await h._make_button_handler(h.steps[3])(cb, state)
    assert await state.get_state() == FindStates.name.state

    # name
    await h._make_text_handler(h.steps[4])(make_message("Мария"), state)
    assert await state.get_state() == FindStates.phone.state

    # phone
    await h._make_text_handler(h.steps[5])(make_message("+79991234567"), state)
    assert await state.get_state() == FindStates.comment.state

    # comment (skip)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True
    assert data["purpose"] == "Для семьи"
    assert data["brand_preference"] == "Toyota"
    assert data["body_type"] == "Кроссовер"


@pytest.mark.asyncio
async def test_find_purpose_other():
    """Clicking 'Другое' for purpose shows text prompt."""
    storage = MemoryStorage()
    state = await make_state(
        storage, state_value=FindStates.purpose.state
    )
    cb = make_callback("step:purpose:__custom__")

    await find_handler._make_button_handler(find_handler.steps[0])(cb, state)

    assert await state.get_state() == FindStates.purpose.state
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_find_purpose_other_text():
    """After 'Другое', user types purpose."""
    storage = MemoryStorage()
    state = await make_state(
        storage, state_value=FindStates.purpose.state
    )
    msg = make_message("Для путешествий")

    await find_handler._make_text_handler(find_handler.steps[0])(msg, state)

    data = await state.get_data()
    assert data["purpose"] == "Для путешествий"
    assert await state.get_state() == FindStates.budget.state


@pytest.mark.asyncio
async def test_find_brand_preference_button():
    """'Без разницы' button on brand_preference step."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FindStates.brand_preference.state,
        data={"purpose": "Для семьи", "budget": "до 500 000"},
    )
    cb = make_callback("step:brand_preference:Без разницы")

    await find_handler._make_button_handler(find_handler.steps[2])(cb, state)

    data = await state.get_data()
    assert data["brand_preference"] == "Без разницы"
    assert await state.get_state() == FindStates.body_type.state
