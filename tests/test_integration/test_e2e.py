"""E2E integration tests for the full lead pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.sell import sell_handler
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
    cb.from_user.id = 123456
    cb.from_user.username = "testuser"
    cb.from_user.first_name = "Ivan"
    return cb


def make_message(text: str) -> Message:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123456
    msg.from_user.username = "testuser"
    msg.from_user.first_name = "Ivan"
    return msg


def make_lead_processor(success: bool = True) -> MagicMock:
    processor = MagicMock()
    processor.process = AsyncMock(return_value=success)
    return processor


def make_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ---------------------------------------------------------------
# E2E: Full sell pipeline with LeadProcessor
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_sell_confirm_send_calls_lead_processor():
    """Full pipeline: confirm:send -> LeadProcessor.process called."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "Toyota Camry",
            "year": "2023",
            "mileage": "50000",
            "price": "2000000",
            "name": "Ivan",
            "phone": "+79991234567",
            "__confirming__": True,
        },
    )

    cb = make_callback("confirm:send")
    processor = make_lead_processor(success=True)
    session = make_session()

    await sell_handler._on_confirm_send(
        cb, state, session=session, lead_processor=processor,
    )

    processor.process.assert_called_once()
    call_kwargs = processor.process.call_args.kwargs
    assert call_kwargs["service_type"] == "sell"
    assert call_kwargs["data"]["car_brand"] == "Toyota Camry"
    assert call_kwargs["data"]["phone"] == "+79991234567"
    assert call_kwargs["telegram_user"]["id"] == 123456

    # Success text shown
    cb.message.edit_text.assert_called_once_with(SUCCESS_TEXT)

    # State cleared
    current = await state.get_state()
    assert current is None


@pytest.mark.asyncio
async def test_e2e_sell_confirm_send_crm_failure():
    """CRM failure -> error message shown, state cleared."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "BMW X5",
            "year": "2022",
            "mileage": "30000",
            "price": "5000000",
            "name": "Petr",
            "phone": "+79998887766",
            "__confirming__": True,
        },
    )

    cb = make_callback("confirm:send")
    processor = make_lead_processor(success=False)
    session = make_session()

    await sell_handler._on_confirm_send(
        cb, state, session=session, lead_processor=processor,
    )

    processor.process.assert_called_once()

    # Error text shown
    call_text = cb.message.edit_text.call_args[0][0]
    assert "техническая ошибка" in call_text

    # State cleared
    current = await state.get_state()
    assert current is None


@pytest.mark.asyncio
async def test_e2e_confirm_send_no_processor_fallback():
    """If lead_processor is not injected, still succeeds (fallback)."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "Kia",
            "year": "2024",
            "mileage": "1000",
            "price": "3000000",
            "name": "Anna",
            "phone": "+79991112233",
            "__confirming__": True,
        },
    )

    cb = make_callback("confirm:send")

    # No session or processor passed
    await sell_handler._on_confirm_send(cb, state)

    cb.message.edit_text.assert_called_once_with(SUCCESS_TEXT)


@pytest.mark.asyncio
async def test_e2e_clean_data_excludes_internal_keys():
    """Internal keys (__ prefixed) are stripped before sending to processor."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=SellStates.comment.state,
        data={
            "car_brand": "Honda",
            "year": "2021",
            "mileage": "80000",
            "price": "1500000",
            "name": "Test",
            "phone": "+79991234567",
            "__confirming__": True,
            "__editing_field__": None,
        },
    )

    cb = make_callback("confirm:send")
    processor = make_lead_processor()
    session = make_session()

    await sell_handler._on_confirm_send(
        cb, state, session=session, lead_processor=processor,
    )

    call_kwargs = processor.process.call_args.kwargs
    data = call_kwargs["data"]
    assert "__confirming__" not in data
    assert "__editing_field__" not in data
    assert "car_brand" in data
