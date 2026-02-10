"""Tests for the freetext (AI chat) handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message

from src.bot.handlers.freetext import (
    on_freetext_entry,
    on_freetext_message,
    on_ai_suggest_accept,
    MAX_AI_MESSAGES,
    ESCALATION_TEXT,
    API_ERROR_TEXT,
)
from src.bot.states.freetext import FreetextStates
from src.services.openai_client.models import AIResponse


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


def make_message(text: str = "test") -> Message:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123
    return msg


def make_openai_client(
    intent: str = "sell",
    confidence: float = 0.9,
    entities: dict | None = None,
    reply: str = "Test reply",
    used_fallback: bool = False,
) -> MagicMock:
    client = MagicMock()
    client.classify = AsyncMock(return_value=AIResponse(
        intent=intent,
        confidence=confidence,
        entities=entities or {},
        reply=reply,
        model_used="gpt-4o-mini",
        used_fallback=used_fallback,
    ))
    return client


# ---------------------------------------------------------------
# Entry
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_freetext_entry():
    """service:freetext sets chatting state."""
    storage = MemoryStorage()
    state = await make_state(storage)
    cb = make_callback("service:freetext")

    await on_freetext_entry(cb, state)

    current = await state.get_state()
    assert current == FreetextStates.chatting.state
    data = await state.get_data()
    assert data["__ai_count__"] == 0
    cb.message.edit_text.assert_called_once()


# ---------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_freetext_high_confidence_suggests_branch():
    """High confidence + known intent -> suggest branch."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": 0},
    )
    msg = make_message("Хочу продать Toyota Camry 2022")
    client = make_openai_client(
        intent="sell",
        confidence=0.9,
        entities={"brand": "Toyota", "model": "Camry", "year": "2022"},
        reply="Понял, вы хотите продать авто.",
    )

    await on_freetext_message(msg, state, openai_client=client)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "Понял" in call_text
    assert "оформлению" in call_text

    # Check pre-fill data stored
    data = await state.get_data()
    assert data["__ai_prefill__"]["car_brand"] == "Toyota"
    assert data["__ai_service__"] == "sell"


@pytest.mark.asyncio
async def test_freetext_low_confidence_replies_text():
    """Low confidence -> just reply with text."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": 0},
    )
    msg = make_message("Привет")
    client = make_openai_client(
        intent="faq",
        confidence=0.5,
        reply="Здравствуйте! Чем могу помочь?",
    )

    await on_freetext_message(msg, state, openai_client=client)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "Здравствуйте" in call_text


@pytest.mark.asyncio
async def test_freetext_escalation_after_max_messages():
    """After MAX_AI_MESSAGES, user gets escalation message."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": MAX_AI_MESSAGES},
    )
    msg = make_message("Ещё один вопрос")

    await on_freetext_message(msg, state)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "специалиста" in call_text

    # State should be cleared
    current = await state.get_state()
    assert current is None


@pytest.mark.asyncio
async def test_freetext_counter_increments():
    """Each message increments ai_count."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": 1},
    )
    msg = make_message("Вопрос")
    client = make_openai_client(
        intent="unknown", confidence=0.3, reply="Не понял."
    )

    await on_freetext_message(msg, state, openai_client=client)

    data = await state.get_data()
    assert data["__ai_count__"] == 2


@pytest.mark.asyncio
async def test_freetext_no_client_shows_error():
    """If openai_client is None, show error and clear state."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": 0},
    )
    msg = make_message("test")

    await on_freetext_message(msg, state, openai_client=None)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "техническая ошибка" in call_text

    current = await state.get_state()
    assert current is None


@pytest.mark.asyncio
async def test_freetext_last_message_includes_escalation():
    """The 3rd message (last allowed) includes escalation in reply."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": MAX_AI_MESSAGES - 1},
    )
    msg = make_message("Последний вопрос")
    client = make_openai_client(
        intent="faq", confidence=0.4, reply="Ответ."
    )

    await on_freetext_message(msg, state, openai_client=client)

    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "Ответ." in call_text
    assert "специалиста" in call_text

    # State cleared after 3rd message
    current = await state.get_state()
    assert current is None


# ---------------------------------------------------------------
# AI suggest accept
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_suggest_accept_stores_prefill():
    """Accepting AI suggestion clears state and shows branch button."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={
            "__ai_count__": 1,
            "__ai_prefill__": {"car_brand": "BMW", "year": "2023"},
            "__ai_service__": "sell",
        },
    )
    cb = make_callback("ai_suggest:sell")

    await on_ai_suggest_accept(cb, state)

    # State cleared, prefill data stored
    data = await state.get_data()
    assert data.get("car_brand") == "BMW"
    assert data.get("year") == "2023"
    # Internal keys cleaned
    assert "__ai_count__" not in data
    assert "__ai_prefill__" not in data

    cb.message.edit_text.assert_called_once()
    call_text = cb.message.edit_text.call_args[0][0]
    assert "автоматически" in call_text


@pytest.mark.asyncio
async def test_ai_suggest_accept_no_prefill():
    """Accepting suggestion with no prefill data."""
    storage = MemoryStorage()
    state = await make_state(
        storage,
        state_value=FreetextStates.chatting.state,
        data={"__ai_count__": 1, "__ai_prefill__": {}, "__ai_service__": "check"},
    )
    cb = make_callback("ai_suggest:check")

    await on_ai_suggest_accept(cb, state)

    cb.message.edit_text.assert_called_once()
    call_text = cb.message.edit_text.call_args[0][0]
    assert "Нажмите" in call_text
    assert "автоматически" not in call_text
