from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_nav_keyboard(show_back: bool = True, show_skip: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if show_back:
        builder.add(InlineKeyboardButton(text="Назад", callback_data="nav:back"))
    builder.add(InlineKeyboardButton(text="В начало", callback_data="nav:home"))
    if show_skip:
        builder.add(InlineKeyboardButton(text="Пропустить", callback_data="nav:skip"))
    builder.adjust(3)
    return builder.as_markup()


def get_reset_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Да, сбросить", callback_data="confirm_reset:yes"))
    builder.add(InlineKeyboardButton(text="Нет, продолжить", callback_data="confirm_reset:no"))
    builder.adjust(2)
    return builder.as_markup()
