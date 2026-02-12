from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.confirm import get_confirm_keyboard, get_edit_fields_keyboard
from src.bot.keyboards.main_menu import WELCOME_TEXT, get_main_menu_keyboard
from src.bot.keyboards.navigation import get_nav_keyboard
from src.utils.formatters import FIELD_LABELS, format_confirmation

logger = logging.getLogger(__name__)


class StepType(Enum):
    TEXT_INPUT = "text_input"
    BUTTON_SELECT = "button_select"
    PHONE_INPUT = "phone_input"
    PHOTO_UPLOAD = "photo_upload"


@dataclass
class StepConfig:
    key: str
    state: State
    prompt_text: str
    step_type: StepType
    buttons: list[tuple[str, str]] | None = None
    required: bool = True
    validator: Callable[[str], str | None] | None = None
    error_text: str = "Некорректный ввод. Попробуйте ещё раз."
    display_label: str = ""
    keyboard_columns: int = 2
    custom_input_prompt: str | None = None  # Shown when __custom__ button is clicked

    def __post_init__(self) -> None:
        if not self.display_label:
            self.display_label = FIELD_LABELS.get(self.key, self.key)


SUCCESS_TEXT = (
    "\u2705 Спасибо! Ваша заявка принята.\n\n"
    "Наш менеджер свяжется с вами в ближайшее время.\n"
    "Если у вас появятся вопросы -- нажмите /start"
)


class BaseDialogHandler:
    """Generic multi-step dialog engine.

    Subclasses define ``service_type``, ``states_group``, and ``steps``.
    The base class auto-registers all necessary handlers on its own Router.
    """

    service_type: str
    states_group: type[StatesGroup]
    steps: list[StepConfig]

    def __init__(self) -> None:
        self.router = Router()
        self._state_to_step: dict[str, int] = {}
        for i, step in enumerate(self.steps):
            self._state_to_step[step.state.state] = i
        self._register_handlers()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        group_filter = StateFilter(self.states_group)

        # Entry point: service:{service_type} callback
        self.router.callback_query.register(
            self._on_entry,
            F.data == f"service:{self.service_type}",
        )

        # Navigation within this branch
        self.router.callback_query.register(
            self._on_nav_back,
            F.data == "nav:back",
            group_filter,
        )
        self.router.callback_query.register(
            self._on_nav_skip,
            F.data == "nav:skip",
            group_filter,
        )

        # Confirmation actions
        self.router.callback_query.register(
            self._on_confirm_send,
            F.data == "confirm:send",
            group_filter,
        )
        self.router.callback_query.register(
            self._on_confirm_edit,
            F.data == "confirm:edit",
            group_filter,
        )
        self.router.callback_query.register(
            self._on_confirm_cancel,
            F.data == "confirm:cancel",
            group_filter,
        )

        # Edit field selection
        self.router.callback_query.register(
            self._on_edit_field_select,
            F.data.startswith("edit_field:"),
            group_filter,
        )

        # Accept pre-filled value (AI pre-fill) — for all steps
        self.router.callback_query.register(
            self._on_accept_prefill,
            F.data.endswith(":__accept__"),
            group_filter,
        )

        # Per-step handlers
        for step in self.steps:
            if step.step_type == StepType.BUTTON_SELECT:
                self.router.callback_query.register(
                    self._make_button_handler(step),
                    F.data.startswith(f"step:{step.key}:"),
                    StateFilter(step.state),
                )
                # Also register text handler for hybrid steps (custom input)
                if step.custom_input_prompt is not None:
                    self.router.message.register(
                        self._make_text_handler(step),
                        F.text,
                        StateFilter(step.state),
                    )
            elif step.step_type == StepType.TEXT_INPUT:
                self.router.message.register(
                    self._make_text_handler(step),
                    F.text,
                    StateFilter(step.state),
                )
                # Also register callback handler if TEXT_INPUT has buttons
                if step.buttons:
                    self.router.callback_query.register(
                        self._make_button_handler(step),
                        F.data.startswith(f"step:{step.key}:"),
                        StateFilter(step.state),
                    )
                continue
            elif step.step_type == StepType.PHONE_INPUT:
                # Contact message
                self.router.message.register(
                    self._make_phone_handler(step),
                    F.contact,
                    StateFilter(step.state),
                )
                # Text fallback for phone
                self.router.message.register(
                    self._make_text_handler(step),
                    F.text,
                    StateFilter(step.state),
                )
            elif step.step_type == StepType.PHOTO_UPLOAD:
                self.router.message.register(
                    self._make_photo_handler(step),
                    F.photo,
                    StateFilter(step.state),
                )
                self.router.callback_query.register(
                    self._make_photo_done_handler(step),
                    F.data == f"step:{step.key}:done",
                    StateFilter(step.state),
                )
            # PHOTO_UPLOAD handled above; TEXT_INPUT handled in elif block

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------

    async def _on_entry(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        # Preserve pre-filled data from AI suggestion
        existing_data = await state.get_data()
        await state.clear()
        if existing_data:
            # Re-store non-internal keys (AI pre-fill values like car_brand, year, etc.)
            prefill = {k: v for k, v in existing_data.items() if not k.startswith("__")}
            if prefill:
                await state.update_data(**prefill)
        await self._send_step(callback.message, state, 0)

    # ------------------------------------------------------------------
    # Step rendering
    # ------------------------------------------------------------------

    async def _send_step(
        self,
        target: Message,
        state: FSMContext,
        step_index: int,
        *,
        edit: bool = False,
    ) -> None:
        step = self.steps[step_index]
        await state.set_state(step.state)

        text = step.prompt_text

        # Check if we have a pre-filled value from AI
        data = await state.get_data()
        editing = data.get("__editing_field__")
        prefilled = data.get(step.key)
        has_prefill = False
        if prefilled and not editing and step.step_type in (
            StepType.TEXT_INPUT, StepType.BUTTON_SELECT,
        ):
            text += f"\n\nТекущее значение: {prefilled}"
            has_prefill = True

        keyboard = self._build_step_keyboard(step, step_index, has_prefill=has_prefill)

        if edit:
            await target.edit_text(text, reply_markup=keyboard)
        else:
            if step.step_type == StepType.PHONE_INPUT:
                # Send reply keyboard with contact button, plus inline nav
                reply_kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="\U0001f4f1 Поделиться контактом", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )
                await target.answer(text, reply_markup=reply_kb)
                nav_kb = self._build_nav_keyboard(step_index, show_skip=False)
                await target.answer("Или введите номер телефона вручную:", reply_markup=nav_kb)
            else:
                await target.answer(text, reply_markup=keyboard)

    def _build_step_keyboard(
        self, step: StepConfig, step_index: int, *, has_prefill: bool = False
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        # "Accept" button for pre-filled values from AI
        if has_prefill:
            builder.add(
                InlineKeyboardButton(
                    text="\u2705 Принять",
                    callback_data=f"step:{step.key}:__accept__",
                )
            )
            builder.adjust(1)

        if step.buttons and step.step_type in (StepType.BUTTON_SELECT, StepType.TEXT_INPUT):
            for label, value in step.buttons:
                builder.add(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"step:{step.key}:{value}",
                    )
                )
            builder.adjust(step.keyboard_columns)

        if step.step_type == StepType.PHOTO_UPLOAD:
            builder.add(
                InlineKeyboardButton(
                    text="\u2705 Готово",
                    callback_data=f"step:{step.key}:done",
                )
            )
            builder.adjust(1)

        # Navigation row
        nav_buttons = self._get_nav_buttons(step_index, step)
        if nav_buttons:
            builder.row(*nav_buttons)

        return builder.as_markup()

    def _build_nav_keyboard(
        self, step_index: int, show_skip: bool = False
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        nav_buttons = self._get_nav_buttons(step_index, self.steps[step_index])
        if nav_buttons:
            builder.row(*nav_buttons)
        return builder.as_markup()

    def _get_nav_buttons(
        self, step_index: int, step: StepConfig
    ) -> list[InlineKeyboardButton]:
        buttons = []
        if step_index > 0:
            buttons.append(
                InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="nav:back")
            )
        buttons.append(
            InlineKeyboardButton(text="\U0001f3e0 В начало", callback_data="nav:home")
        )
        if not step.required:
            buttons.append(
                InlineKeyboardButton(text="\u23ed Пропустить", callback_data="nav:skip")
            )
        return buttons

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def _on_nav_back(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        current_state = await state.get_state()
        step_index = self._state_to_step.get(current_state, 0)
        if step_index > 0:
            data = await state.get_data()
            is_editing = bool(data.get("__editing_field__"))
            if is_editing:
                # In edit mode, just go back to confirmation
                await state.update_data(__editing_field__=None)
                await self._show_confirmation(callback.message, state, edit=True)
            else:
                # Remove keyboard from current message
                step = self.steps[step_index]
                try:
                    await callback.message.edit_text(step.prompt_text)
                except Exception:
                    pass
                await self._send_step(callback.message, state, step_index - 1)

    async def _on_nav_skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        current_state = await state.get_state()
        step_index = self._state_to_step.get(current_state, 0)
        step = self.steps[step_index]
        if not step.required:
            # Remove keyboard from current message
            try:
                await callback.message.edit_text(
                    f"{step.prompt_text}\n\n\u23ed Пропущено"
                )
            except Exception:
                pass
            await self._advance(callback.message, state, step_index)

    # ------------------------------------------------------------------
    # Advance logic
    # ------------------------------------------------------------------

    async def _advance(
        self,
        target: Message,
        state: FSMContext,
        current_step_index: int,
        *,
        edit: bool = False,
    ) -> None:
        data = await state.get_data()
        editing_field = data.get("__editing_field__")

        if editing_field:
            # Return to confirmation after editing
            await state.update_data(__editing_field__=None)
            await self._show_confirmation(target, state, edit=edit)
            return

        next_index = current_step_index + 1
        if next_index >= len(self.steps):
            await self._show_confirmation(target, state, edit=edit)
        else:
            await self._send_step(target, state, next_index, edit=edit)

    # ------------------------------------------------------------------
    # Confirmation
    # ------------------------------------------------------------------

    async def _show_confirmation(
        self,
        target: Message,
        state: FSMContext,
        *,
        edit: bool = False,
    ) -> None:
        # Set state to last step + use a convention: we stay in the last step's state
        # but we use a special marker in FSM data
        data = await state.get_data()
        await state.update_data(__confirming__=True)

        text = format_confirmation(self.service_type, data)
        keyboard = get_confirm_keyboard()

        if edit:
            await target.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)

    async def _on_confirm_send(self, callback: CallbackQuery, state: FSMContext, **kwargs: Any) -> None:
        await callback.answer()
        data = await state.get_data()

        # Clean internal keys
        clean_data = {k: v for k, v in data.items() if not k.startswith("__")}

        success = await self._process_lead(callback, state, clean_data, **kwargs)

        await state.clear()
        if success:
            await callback.message.edit_text(SUCCESS_TEXT)
        else:
            await callback.message.edit_text(
                "Спасибо! Ваша заявка принята, но возникла техническая ошибка "
                "при отправке. Мы сохранили её и обработаем в ближайшее время.\n\n"
                "Если у вас появятся вопросы -- нажмите /start"
            )

    async def _process_lead(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        data: dict,
        **kwargs: Any,
    ) -> bool:
        """Process the lead via LeadProcessor (AmoCRM + DB)."""
        from src.services.lead_processor import LeadProcessor

        session = kwargs.get("session")
        lead_processor: LeadProcessor | None = kwargs.get("lead_processor")

        telegram_user = {
            "id": callback.from_user.id,
            "username": callback.from_user.username,
            "first_name": callback.from_user.first_name,
        }

        if lead_processor and session:
            return await lead_processor.process(
                session=session,
                telegram_user=telegram_user,
                service_type=self.service_type,
                data=data,
            )

        # Fallback: no processor available (e.g. in tests)
        logger.warning(
            "LeadProcessor not available, lead not sent to CRM: "
            "service=%s user=%s",
            self.service_type,
            callback.from_user.id,
        )
        return True

    async def _on_confirm_edit(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        data = await state.get_data()

        # Build list of filled fields
        fields = []
        for step in self.steps:
            value = data.get(step.key)
            if value is not None:
                fields.append((step.key, step.display_label))
            elif step.required:
                fields.append((step.key, step.display_label))

        keyboard = get_edit_fields_keyboard(fields)
        await callback.message.edit_text(
            "Выберите поле для редактирования:", reply_markup=keyboard
        )

    async def _on_confirm_cancel(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer("Заявка отменена")
        await state.clear()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())

    # ------------------------------------------------------------------
    # Accept pre-filled value
    # ------------------------------------------------------------------

    async def _on_accept_prefill(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Accept a pre-filled value from AI and advance."""
        await callback.answer()
        # callback_data: step:{key}:__accept__
        key = callback.data.split(":")[1]
        step_index = None
        step_cfg = None
        for i, step in enumerate(self.steps):
            if step.key == key:
                step_index = i
                step_cfg = step
                break
        if step_index is not None:
            data = await state.get_data()
            prefilled = data.get(key, "")
            await callback.message.edit_text(
                f"{step_cfg.prompt_text}\n\n\u2705 {prefilled}"
            )
            await self._advance(callback.message, state, step_index)

    # ------------------------------------------------------------------
    # Edit flow
    # ------------------------------------------------------------------

    async def _on_edit_field_select(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        field_key = callback.data.split(":", 1)[1]

        if field_key == "back":
            await self._show_confirmation(callback.message, state, edit=True)
            return

        # Find the step for this field
        for i, step in enumerate(self.steps):
            if step.key == field_key:
                await state.update_data(__editing_field__=field_key)
                await self._send_step(callback.message, state, i, edit=True)
                return

    # ------------------------------------------------------------------
    # Step input handlers (factories)
    # ------------------------------------------------------------------

    def _make_text_handler(self, step: StepConfig) -> Callable:
        async def handler(message: Message, state: FSMContext) -> None:
            text = message.text.strip()

            if step.step_type == StepType.PHONE_INPUT:
                from src.utils.phone import validate_phone

                phone = validate_phone(text)
                if not phone:
                    await message.answer(
                        "Неверный формат телефона. Введите номер в формате "
                        "+7XXXXXXXXXX или поделитесь контактом."
                    )
                    return
                await state.update_data(**{step.key: phone})
            else:
                if step.validator:
                    validated = step.validator(text)
                    if validated is None:
                        await message.answer(step.error_text)
                        return
                    await state.update_data(**{step.key: validated})
                else:
                    await state.update_data(**{step.key: text})

            step_index = self._state_to_step[step.state.state]
            # Remove reply keyboard if phone step
            if step.step_type == StepType.PHONE_INPUT:
                await message.answer("Принято", reply_markup=ReplyKeyboardRemove())
            await self._advance(message, state, step_index)

        return handler

    def _make_button_handler(self, step: StepConfig) -> Callable:
        async def handler(callback: CallbackQuery, state: FSMContext) -> None:
            await callback.answer()
            # callback_data format: step:{key}:{value}
            value = callback.data.split(":", 2)[2]
            data = await state.get_data()
            is_editing = bool(data.get("__editing_field__"))

            # Handle __accept__ — keep pre-filled value, just advance
            if value == "__accept__":
                step_index = self._state_to_step[step.state.state]
                prefilled = data.get(step.key, "")
                if is_editing:
                    await self._advance(callback.message, state, step_index, edit=True)
                else:
                    await callback.message.edit_text(
                        f"{step.prompt_text}\n\n\u2705 {prefilled}"
                    )
                    await self._advance(callback.message, state, step_index)
                return

            # Handle __custom__ — prompt for text input instead of advancing
            if value == "__custom__" and step.custom_input_prompt:
                step_index = self._state_to_step[step.state.state]
                nav_kb = self._build_nav_keyboard(step_index)
                await callback.message.edit_text(
                    step.custom_input_prompt, reply_markup=nav_kb
                )
                return

            # Find label for display
            display_value = value
            if step.buttons:
                for label, val in step.buttons:
                    if val == value:
                        display_value = label
                        break

            await state.update_data(**{step.key: display_value})
            step_index = self._state_to_step[step.state.state]

            if is_editing:
                # Edit flow: replace in place and return to confirmation
                await self._advance(callback.message, state, step_index, edit=True)
            else:
                # Normal flow: show selected value, send next step as new message
                await callback.message.edit_text(
                    f"{step.prompt_text}\n\n\u2705 {display_value}"
                )
                await self._advance(callback.message, state, step_index)

        return handler

    def _make_phone_handler(self, step: StepConfig) -> Callable:
        async def handler(message: Message, state: FSMContext) -> None:
            from src.utils.phone import validate_phone

            phone_number = message.contact.phone_number
            phone = validate_phone(phone_number)
            if not phone:
                await message.answer(
                    "Не удалось обработать номер телефона. "
                    "Попробуйте ввести вручную в формате +7XXXXXXXXXX."
                )
                return

            await state.update_data(**{step.key: phone})
            step_index = self._state_to_step[step.state.state]
            await message.answer("Принято", reply_markup=ReplyKeyboardRemove())
            await self._advance(message, state, step_index)

        return handler

    def _make_photo_handler(self, step: StepConfig) -> Callable:
        async def handler(message: Message, state: FSMContext) -> None:
            # Get the largest photo
            file_id = message.photo[-1].file_id
            data = await state.get_data()
            photos = data.get(step.key, [])
            photos.append(file_id)
            await state.update_data(**{step.key: photos})
            count = len(photos)
            await message.answer(
                f"Фото добавлено ({count} шт.). "
                "Отправьте ещё или нажмите \"Готово\"."
            )

        return handler

    def _make_photo_done_handler(self, step: StepConfig) -> Callable:
        async def handler(callback: CallbackQuery, state: FSMContext) -> None:
            await callback.answer()
            step_index = self._state_to_step[step.state.state]
            data = await state.get_data()
            is_editing = bool(data.get("__editing_field__"))
            photos = data.get(step.key, [])
            if is_editing:
                await self._advance(callback.message, state, step_index, edit=True)
            else:
                await callback.message.edit_text(
                    f"{step.prompt_text}\n\n\u2705 {len(photos)} фото"
                )
                await self._advance(callback.message, state, step_index)

        return handler
