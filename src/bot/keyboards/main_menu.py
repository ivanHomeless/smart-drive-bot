from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [
        ("Продать авто", "service:sell"),
        ("Купить авто", "service:buy"),
        ("Подбор авто", "service:find"),
        ("Проверка авто", "service:check"),
        ("Юридическая помощь", "service:legal"),
        ("Задать вопрос", "service:freetext"),
    ]
    for label, callback in buttons:
        builder.add(InlineKeyboardButton(text=label, callback_data=callback))
    builder.adjust(2)
    return builder.as_markup()


WELCOME_TEXT = (
    "Добро пожаловать в CarQuery AI!\n\n"
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
