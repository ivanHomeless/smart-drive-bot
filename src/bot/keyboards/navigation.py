from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_nav_keyboard(show_back: bool = True, show_skip: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if show_back:
        builder.add(InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="nav:back"))
    builder.add(InlineKeyboardButton(text="\U0001f3e0 В начало", callback_data="nav:home"))
    if show_skip:
        builder.add(InlineKeyboardButton(text="\u23ed Пропустить", callback_data="nav:skip"))
    builder.adjust(3)
    return builder.as_markup()


def get_reset_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="\u2705 Да, сбросить", callback_data="confirm_reset:yes"))
    builder.add(InlineKeyboardButton(text="\u274c Нет, продолжить", callback_data="confirm_reset:no"))
    builder.adjust(2)
    return builder.as_markup()
