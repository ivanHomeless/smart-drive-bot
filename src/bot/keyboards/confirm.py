from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation screen keyboard: Send / Edit / Cancel."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Отправить", callback_data="confirm:send"),
        InlineKeyboardButton(text="Изменить", callback_data="confirm:edit"),
        InlineKeyboardButton(text="Отменить", callback_data="confirm:cancel"),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_edit_fields_keyboard(
    fields: list[tuple[str, str]],
) -> InlineKeyboardMarkup:
    """Keyboard with editable field buttons for the edit flow.

    Args:
        fields: list of (field_key, display_label) tuples.
    """
    builder = InlineKeyboardBuilder()
    for key, label in fields:
        builder.add(
            InlineKeyboardButton(text=label, callback_data=f"edit_field:{key}")
        )
    builder.add(
        InlineKeyboardButton(text="Назад к подтверждению", callback_data="edit_field:back")
    )
    builder.adjust(1)
    return builder.as_markup()
