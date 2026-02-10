from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import get_main_menu_keyboard, WELCOME_TEXT
from src.bot.states.freetext import FreetextStates
from src.services.openai_client.client import OpenAIClient
from src.services.openai_client.prompts import ENTITY_KEY_MAPPING, INTENT_TO_SERVICE

logger = logging.getLogger(__name__)

router = Router()

MAX_AI_MESSAGES = 3

ESCALATION_TEXT = (
    "Похоже, ваш вопрос требует участия специалиста.\n"
    "Давайте я соединю вас с менеджером -- он свяжется с вами "
    "в ближайшее время.\n\n"
    "Или выберите услугу из меню:"
)

API_ERROR_TEXT = (
    "Извините, произошла техническая ошибка. "
    "Пожалуйста, выберите нужную услугу из меню:"
)

SERVICE_LABELS = {
    "sell": "Продать авто",
    "buy": "Купить авто",
    "find": "Подбор авто",
    "check": "Проверка авто",
    "legal": "Юридическая помощь",
}


def _build_suggestion_keyboard(service_type: str) -> InlineKeyboardMarkup:
    """Build keyboard with branch suggestion + menu."""
    builder = InlineKeyboardBuilder()
    label = SERVICE_LABELS.get(service_type, service_type)
    builder.add(
        InlineKeyboardButton(
            text=f"Перейти: {label}",
            callback_data=f"ai_suggest:{service_type}",
        )
    )
    builder.add(
        InlineKeyboardButton(text="В меню", callback_data="nav:home")
    )
    builder.adjust(1)
    return builder.as_markup()


def _build_continue_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for continuing freetext chat."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="В меню", callback_data="nav:home")
    )
    return builder.as_markup()


@router.callback_query(F.data == "service:freetext")
async def on_freetext_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(FreetextStates.chatting)
    await state.update_data(__ai_count__=0)
    await callback.message.edit_text(
        "Задайте ваш вопрос, и я постараюсь помочь:",
        reply_markup=_build_continue_keyboard(),
    )


@router.message(F.text, StateFilter(FreetextStates.chatting))
async def on_freetext_message(
    message: Message,
    state: FSMContext,
    openai_client: OpenAIClient | None = None,
) -> None:
    data = await state.get_data()
    ai_count = data.get("__ai_count__", 0)

    # Check message limit
    if ai_count >= MAX_AI_MESSAGES:
        await state.clear()
        await message.answer(ESCALATION_TEXT, reply_markup=get_main_menu_keyboard())
        return

    # Increment counter
    ai_count += 1
    await state.update_data(__ai_count__=ai_count)

    if openai_client is None:
        await message.answer(API_ERROR_TEXT, reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    # Classify the message
    response = await openai_client.classify(message.text)
    logger.info(
        "AI classify: user=%d intent=%s confidence=%.2f model=%s fallback=%s",
        message.from_user.id,
        response.intent,
        response.confidence,
        response.model_used,
        response.used_fallback,
    )

    # High confidence + known service -> suggest branch
    service_type = INTENT_TO_SERVICE.get(response.intent)
    if response.is_high_confidence and service_type:
        # Store extracted entities for pre-fill
        prefill = {}
        for ai_key, step_key in ENTITY_KEY_MAPPING.items():
            value = response.entities.get(ai_key)
            if value:
                prefill[step_key] = str(value)

        await state.update_data(__ai_prefill__=prefill, __ai_service__=service_type)

        reply_text = response.reply or "Я понял ваш запрос."
        reply_text += f"\n\nМогу предложить перейти к оформлению заявки:"

        await message.answer(
            reply_text,
            reply_markup=_build_suggestion_keyboard(service_type),
        )
        return

    # Low confidence or faq/unknown -> just reply
    reply_text = response.reply or "Не совсем понял ваш вопрос. Попробуйте уточнить."

    # Check if next message will hit the limit
    if ai_count >= MAX_AI_MESSAGES:
        reply_text += (
            "\n\n" + ESCALATION_TEXT
        )
        await state.clear()
        await message.answer(reply_text, reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(reply_text, reply_markup=_build_continue_keyboard())


@router.callback_query(F.data.startswith("ai_suggest:"))
async def on_ai_suggest_accept(callback: CallbackQuery, state: FSMContext) -> None:
    """User accepts the AI-suggested branch. Transfer with pre-filled entities."""
    await callback.answer()
    data = await state.get_data()
    service_type = callback.data.split(":", 1)[1]
    prefill = data.get("__ai_prefill__", {})

    # Clear freetext state, store prefill data for the branch
    await state.clear()
    await state.update_data(**prefill)

    logger.info(
        "AI suggest accepted: user=%d service=%s prefill=%s",
        callback.from_user.id, service_type, prefill,
    )

    # Simulate the service entry callback by dispatching to the branch router.
    # We update the callback data so the branch handler picks it up.
    # The branch entry handler is registered on F.data == "service:{type}"
    # so we need to re-emit. We do this by answering and editing with instruction.
    from src.bot.keyboards.main_menu import get_main_menu_keyboard
    builder = InlineKeyboardBuilder()
    label = SERVICE_LABELS.get(service_type, service_type)
    builder.add(
        InlineKeyboardButton(
            text=f"Начать: {label}",
            callback_data=f"service:{service_type}",
        )
    )
    builder.adjust(1)

    text = "Отлично! Нажмите кнопку, чтобы начать оформление заявки."
    if prefill:
        text += "\nДанные из вашего сообщения будут подставлены автоматически."

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
