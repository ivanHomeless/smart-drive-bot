from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.main_menu import HELP_TEXT, RESET_WARNING_TEXT, WELCOME_TEXT, get_main_menu_keyboard
from src.bot.keyboards.navigation import get_reset_confirm_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer(RESET_WARNING_TEXT, reply_markup=get_reset_confirm_keyboard())
        return
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer(RESET_WARNING_TEXT, reply_markup=get_reset_confirm_keyboard())
        return
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())


@router.callback_query(lambda c: c.data == "confirm_reset:yes")
async def confirm_reset_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_reset:no")
async def confirm_reset_no(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer("Продолжаем текущий диалог")
