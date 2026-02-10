"""Tests for the Legal branch."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.legal import legal_handler
from src.bot.states.legal import LegalStates


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


def test_legal_has_5_steps():
    assert len(legal_handler.steps) == 5


@pytest.mark.asyncio
async def test_legal_entry():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:legal")

    await legal_handler._on_entry(cb, state)

    assert await state.get_state() == LegalStates.question_type.state


@pytest.mark.asyncio
async def test_legal_happy_path():
    storage = MemoryStorage()
    state = await make_state(storage)
    h = legal_handler

    await h._on_entry(make_callback("service:legal"), state)

    # question_type (button)
    cb = make_callback("step:question_type:Страхование")
    await h._make_button_handler(h.steps[0])(cb, state)
    assert await state.get_state() == LegalStates.description.state

    # description (text)
    await h._make_text_handler(h.steps[1])(
        make_message("Нужно оформить ОСАГО"), state
    )
    assert await state.get_state() == LegalStates.name.state

    # name
    await h._make_text_handler(h.steps[2])(make_message("Ольга"), state)
    assert await state.get_state() == LegalStates.phone.state

    # phone
    await h._make_text_handler(h.steps[3])(make_message("+79991234567"), state)
    assert await state.get_state() == LegalStates.comment.state

    # comment (skip)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True
    assert data["question_type"] == "Страхование (ОСАГО / КАСКО)"
    assert data["description"] == "Нужно оформить ОСАГО"


@pytest.mark.asyncio
async def test_legal_question_type_other():
    """Clicking 'Другое' shows text prompt."""
    storage = MemoryStorage()
    state = await make_state(
        storage, state_value=LegalStates.question_type.state
    )
    cb = make_callback("step:question_type:__custom__")

    await legal_handler._make_button_handler(legal_handler.steps[0])(cb, state)

    assert await state.get_state() == LegalStates.question_type.state
    cb.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_legal_question_type_other_text():
    """After 'Другое', user types their question type."""
    storage = MemoryStorage()
    state = await make_state(
        storage, state_value=LegalStates.question_type.state
    )
    msg = make_message("Растаможка авто из-за рубежа")

    await legal_handler._make_text_handler(legal_handler.steps[0])(msg, state)

    data = await state.get_data()
    assert data["question_type"] == "Растаможка авто из-за рубежа"
    assert await state.get_state() == LegalStates.description.state


@pytest.mark.asyncio
async def test_legal_edit_description():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=LegalStates.comment.state,
        data={
            "question_type": "Страхование",
            "description": "ОСАГО",
            "name": "Ольга",
            "phone": "+79991234567",
            "__confirming__": True,
        },
    )

    # Select edit
    cb = make_callback("edit_field:description")
    await legal_handler._on_edit_field_select(cb, state)
    assert await state.get_state() == LegalStates.description.state

    # Edit value
    msg = make_message("КАСКО на новый авто")
    await legal_handler._make_text_handler(legal_handler.steps[1])(msg, state)

    data = await state.get_data()
    assert data["description"] == "КАСКО на новый авто"
    assert data.get("__confirming__") is True
