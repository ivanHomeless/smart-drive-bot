"""Tests for the Check branch."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.check import check_handler
from src.bot.states.check import CheckStates


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


def test_check_has_6_steps():
    assert len(check_handler.steps) == 6


@pytest.mark.asyncio
async def test_check_entry():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:check")

    await check_handler._on_entry(cb, state)

    assert await state.get_state() == CheckStates.check_type.state


@pytest.mark.asyncio
async def test_check_happy_path():
    storage = MemoryStorage()
    state = await make_state(storage)
    h = check_handler

    await h._on_entry(make_callback("service:check"), state)

    # check_type (button)
    cb = make_callback("step:check_type:Комплексная проверка")
    await h._make_button_handler(h.steps[0])(cb, state)
    assert await state.get_state() == CheckStates.car_brand.state

    # car_brand (text)
    await h._make_text_handler(h.steps[1])(make_message("Mazda CX-5"), state)
    assert await state.get_state() == CheckStates.vin.state

    # vin (skip - optional)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)
    assert await state.get_state() == CheckStates.name.state

    # name
    await h._make_text_handler(h.steps[3])(make_message("Петр"), state)
    assert await state.get_state() == CheckStates.phone.state

    # phone
    await h._make_text_handler(h.steps[4])(make_message("+79991234567"), state)
    assert await state.get_state() == CheckStates.comment.state

    # comment (skip)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True
    assert data["check_type"] == "Комплексная проверка"
    assert data["car_brand"] == "Mazda CX-5"


@pytest.mark.asyncio
async def test_check_with_vin():
    """VIN is filled instead of skipped."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=CheckStates.vin.state,
        data={"check_type": "Техническая диагностика", "car_brand": "BMW X3"},
    )

    await check_handler._make_text_handler(check_handler.steps[2])(
        make_message("WBAPH5C55BA123456"), state
    )

    data = await state.get_data()
    assert data["vin"] == "WBAPH5C55BA123456"
    assert await state.get_state() == CheckStates.name.state


@pytest.mark.asyncio
async def test_check_back_from_car_brand():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=CheckStates.car_brand.state,
        data={"check_type": "Комплексная проверка"},
    )
    cb = make_callback("nav:back")

    await check_handler._on_nav_back(cb, state)

    assert await state.get_state() == CheckStates.check_type.state
