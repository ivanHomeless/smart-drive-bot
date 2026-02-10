"""Tests for the Sell branch."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message, PhotoSize

from src.bot.handlers.sell import sell_handler, validate_mileage
from src.bot.handlers.base_dialog import SUCCESS_TEXT
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
# Tests: Mileage validator
# ---------------------------------------------------------------

def test_validate_mileage_valid():
    assert validate_mileage("85000") == "85 000 км"


def test_validate_mileage_with_spaces():
    assert validate_mileage("85 000") == "85 000 км"


def test_validate_mileage_with_suffix():
    assert validate_mileage("85000км") == "85 000 км"


def test_validate_mileage_invalid():
    assert validate_mileage("abc") is None


def test_validate_mileage_negative():
    assert validate_mileage("-100") is None


# ---------------------------------------------------------------
# Tests: Entry and step count
# ---------------------------------------------------------------

def test_sell_has_8_steps():
    assert len(sell_handler.steps) == 8


@pytest.mark.asyncio
async def test_sell_entry_starts_at_car_brand():
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:sell")

    await sell_handler._on_entry(cb, state)

    assert await state.get_state() == SellStates.car_brand.state


# ---------------------------------------------------------------
# Tests: Happy path (full walkthrough)
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_happy_path():
    storage = MemoryStorage()
    state = await make_state(storage)
    h = sell_handler

    # Entry
    cb = make_callback("service:sell")
    await h._on_entry(cb, state)

    # Step 1: car_brand (text)
    msg = make_message("Toyota Camry")
    await h._make_text_handler(h.steps[0])(msg, state)
    assert await state.get_state() == SellStates.year.state

    # Step 2: year (button)
    cb = make_callback("step:year:2022")
    await h._make_button_handler(h.steps[1])(cb, state)
    assert await state.get_state() == SellStates.mileage.state

    # Step 3: mileage (text with validator)
    msg = make_message("85000")
    await h._make_text_handler(h.steps[2])(msg, state)
    assert await state.get_state() == SellStates.price.state

    # Step 4: price (text input with button)
    msg = make_message("1800000")
    await h._make_text_handler(h.steps[3])(msg, state)
    assert await state.get_state() == SellStates.photos.state

    # Step 5: photos (skip - optional)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)
    assert await state.get_state() == SellStates.name.state

    # Step 6: name (text)
    msg = make_message("Алексей")
    await h._make_text_handler(h.steps[5])(msg, state)
    assert await state.get_state() == SellStates.phone.state

    # Step 7: phone (text fallback)
    msg = make_message("+79991234567")
    await h._make_text_handler(h.steps[6])(msg, state)
    assert await state.get_state() == SellStates.comment.state

    # Step 8: comment (skip - optional)
    cb = make_callback("nav:skip")
    await h._on_nav_skip(cb, state)

    # Should be at confirmation
    data = await state.get_data()
    assert data.get("__confirming__") is True
    assert data["car_brand"] == "Toyota Camry"
    assert data["year"] == "2022"
    assert data["mileage"] == "85 000 км"
    assert data["name"] == "Алексей"


# ---------------------------------------------------------------
# Tests: Price button "На ваше усмотрение"
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_price_button():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.price.state,
        data={"car_brand": "BMW", "year": "2023", "mileage": "50 000 км"},
    )
    cb = make_callback("step:price:На ваше усмотрение")

    await sell_handler._make_button_handler(sell_handler.steps[3])(cb, state)

    data = await state.get_data()
    assert data["price"] == "На ваше усмотрение"
    assert await state.get_state() == SellStates.photos.state


# ---------------------------------------------------------------
# Tests: Year custom input
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_year_custom():
    """Clicking 'Старше' should show text prompt."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.year.state,
        data={"car_brand": "Lada"},
    )
    cb = make_callback("step:year:__custom__")

    await sell_handler._make_button_handler(sell_handler.steps[1])(cb, state)

    # Should still be on year state, waiting for text
    assert await state.get_state() == SellStates.year.state
    cb.message.edit_text.assert_called_once()
    assert "год" in cb.message.edit_text.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_sell_year_custom_text_input():
    """After clicking 'Старше', user types a year."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.year.state,
        data={"car_brand": "Lada"},
    )
    msg = make_message("2010")

    await sell_handler._make_text_handler(sell_handler.steps[1])(msg, state)

    data = await state.get_data()
    assert data["year"] == "2010"
    assert await state.get_state() == SellStates.mileage.state


# ---------------------------------------------------------------
# Tests: Mileage validation error
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_mileage_invalid():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.mileage.state,
        data={"car_brand": "BMW", "year": "2023"},
    )
    msg = make_message("много")

    await sell_handler._make_text_handler(sell_handler.steps[2])(msg, state)

    msg.answer.assert_called_once_with("Укажите пробег числом, например: 85000")
    assert "mileage" not in await state.get_data()


# ---------------------------------------------------------------
# Tests: Back navigation
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_back_from_mileage_to_year():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.mileage.state,
        data={"car_brand": "BMW", "year": "2023"},
    )
    cb = make_callback("nav:back")

    await sell_handler._on_nav_back(cb, state)

    assert await state.get_state() == SellStates.year.state


# ---------------------------------------------------------------
# Tests: Edit from confirmation
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_edit_car_brand_from_confirmation():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "Toyota Camry",
            "year": "2022",
            "mileage": "85 000 км",
            "price": "1 800 000",
            "name": "Алексей",
            "phone": "+79991234567",
            "__confirming__": True,
        },
    )

    # Select edit
    cb = make_callback("edit_field:car_brand")
    await sell_handler._on_edit_field_select(cb, state)
    assert await state.get_state() == SellStates.car_brand.state

    # Edit value
    msg = make_message("Honda Accord")
    await sell_handler._make_text_handler(sell_handler.steps[0])(msg, state)

    # Should return to confirmation
    data = await state.get_data()
    assert data["car_brand"] == "Honda Accord"
    assert data.get("__confirming__") is True


# ---------------------------------------------------------------
# Tests: Confirm send
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_sell_confirm_send():
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "Toyota",
            "year": "2022",
            "__confirming__": True,
        },
    )
    cb = make_callback("confirm:send")

    await sell_handler._on_confirm_send(cb, state)

    assert await state.get_state() is None
    cb.message.edit_text.assert_called_once_with(SUCCESS_TEXT)
