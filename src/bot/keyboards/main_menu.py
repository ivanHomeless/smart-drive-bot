from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [
        ("\U0001f697 Продать авто", "service:sell"),
        ("\U0001f50d Купить авто", "service:buy"),
        ("\U0001f3af Подбор авто", "service:find"),
        ("\U0001f527 Проверка авто", "service:check"),
        ("\u2696\ufe0f Юридическая помощь", "service:legal"),
        ("\U0001f4ac Задать вопрос", "service:freetext"),
    ]
    for label, callback in buttons:
        builder.add(InlineKeyboardButton(text=label, callback_data=callback))
    builder.adjust(2)
    return builder.as_markup()


WELCOME_TEXT = (
    "\U0001f44b Добро пожаловать в CarQuery AI!\n\n"
    "Мы помогаем с покупкой, продажей, подбором\n"
    "и проверкой автомобилей, а также с юридическими вопросами.\n\n"
    "Выберите, что вас интересует:"
)

HELP_TEXT = (
    "CarQuery AI Bot — помощник по вопросам автомобилей.\n\n"
    "Доступные команды:\n"
    "/start — главное меню\n"
    "/help — эта справка\n"
    "/menu — показать меню услуг\n\n"
    "Вы также можете просто написать ваш вопрос, и AI поможет вам."
)

RESET_WARNING_TEXT = "У вас есть незавершённый диалог. Хотите сбросить его и вернуться в главное меню?"
