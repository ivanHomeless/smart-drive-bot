"""Tests for the Buy branch."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.buy import buy_handler, validate_budget
from src.bot.states.buy import BuyStates


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


# ---------------------------------------------------------------
# Tests: Budget validator
# ---------------------------------------------------------------

def test_validate_budget_valid():
    result = validate_budget("1500000")
    assert result is not None
    assert "1 500 000" in result


def test_validate_budget_with_spaces():
    result = validate_budget("1 500 000")
    assert result is not None


def test_validate_budget_invalid():
    assert validate_budget("abc") is None


def test_validate_budget_negative():
    assert validate_budget("-100") is None


# ---------------------------------------------------------------
# Tests: Entry
# ---------------------------------------------------------------

def test_buy_has_8_steps():
    assert len(buy_handler.steps) == 8


@pytest.mark.asyncio
async def test_buy_entry():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:buy")

    await buy_handler._on_entry(cb, state)

    assert await state.get_state() == BuyStates.car_brand.state


# ---------------------------------------------------------------
# Tests: Happy path
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_buy_happy_path():
    storage = MemoryStorage()
    state = await make_state(storage)
    h = buy_handler

    await h._on_entry(make_callback("service:buy"), state)

    # car_brand
    await h._make_text_handler(h.steps[0])(make_message("Kia Rio"), state)
    assert await state.get_state() == BuyStates.budget.state

    # budget (button)
    cb = make_callback("step:budget:до 500 000")
    await h._make_button_handler(h.steps[1])(cb, state)
    assert await state.get_state() == BuyStates.year_from.state

    # year_from (button)
    cb = make_callback("step:year_from:2020")
    await h._make_button_handler(h.steps[2])(cb, state)
    assert await state.get_state() == BuyStates.transmission.state

    # transmission (button)
    cb = make_callback("step:transmission:АКПП")
    await h._make_button_handler(h.steps[3])(cb, state)
    assert await state.get_state() == BuyStates.drive.state

    # drive (button)
    cb = make_callback("step:drive:Передний")
    await h._make_button_handler(h.steps[4])(cb, state)
    assert await state.get_state() == BuyStates.name.state

    # name
    await h._make_text_handler(h.steps[5])(make_message("Иван"), state)
    assert await state.get_state() == BuyStates.phone.state

    # phone
    await h._make_text_handler(h.steps[6])(make_message("+79991234567"), state)
    assert await state.get_state() == BuyStates.comment.state

    # comment (skip)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)

    data = await state.get_data()
    assert data.get("__confirming__") is True
    assert data["car_brand"] == "Kia Rio"
    assert data["budget"] == "до 500 000"
    assert data["transmission"] == "АКПП"


# ---------------------------------------------------------------
# Tests: Custom budget
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_buy_custom_budget_button():
    """Clicking 'Указать свой' shows text prompt."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=BuyStates.budget.state,
        data={"car_brand": "BMW"},
    )
    cb = make_callback("step:budget:__custom__")

    await buy_handler._make_button_handler(buy_handler.steps[1])(cb, state)

    assert await state.get_state() == BuyStates.budget.state
    cb.message.edit_text.assert_called_once()
    assert "бюджет" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_buy_custom_budget_text():
    """After custom prompt, user types a number."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=BuyStates.budget.state,
        data={"car_brand": "BMW"},
    )
    msg = make_message("2000000")

    await buy_handler._make_text_handler(buy_handler.steps[1])(msg, state)

    data = await state.get_data()
    assert "2 000 000" in data["budget"]
    assert await state.get_state() == BuyStates.year_from.state


@pytest.mark.asyncio
async def test_buy_custom_budget_invalid():
    """Invalid custom budget shows error."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=BuyStates.budget.state,
        data={"car_brand": "BMW"},
    )
    msg = make_message("не знаю")

    await buy_handler._make_text_handler(buy_handler.steps[1])(msg, state)

    msg.answer.assert_called_once_with("Укажите бюджет числом, например: 1500000")
    assert "budget" not in await state.get_data()
