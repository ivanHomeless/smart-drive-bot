from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.bot.keyboards.main_menu import WELCOME_TEXT, get_main_menu_keyboard

router = Router()


@router.callback_query(lambda c: c.data == "nav:home")
async def nav_home(callback: CallbackQuery, state: FSMContext) -> None:
    """Reset dialog and return to the main menu."""
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())
    await callback.answer()
