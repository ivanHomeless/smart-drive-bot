from datetime import date

from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.states.sell import SellStates


def _year_buttons(count: int = 10) -> list[tuple[str, str]]:
    """Generate year buttons from current+1 down to current+1-count, plus 'Старше'."""
    current = date.today().year
    buttons = [(str(y), str(y)) for y in range(current + 1, current + 1 - count, -1)]
    buttons.append(("Старше", "__custom__"))
    return buttons


def validate_mileage(text: str) -> str | None:
    cleaned = text.replace(" ", "").replace("км", "").replace("km", "")
    try:
        val = int(cleaned)
        if val < 0:
            return None
        return f"{val:,}".replace(",", " ") + " км"
    except ValueError:
        return None


class SellHandler(BaseDialogHandler):
    service_type = "sell"
    states_group = SellStates
    steps = [
        StepConfig(
            key="car_brand",
            state=SellStates.car_brand,
            prompt_text="Укажите марку и модель автомобиля:",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="year",
            state=SellStates.year,
            prompt_text="Выберите год выпуска:",
            step_type=StepType.BUTTON_SELECT,
            buttons=_year_buttons(10),
            custom_input_prompt="Введите год выпуска:",
            keyboard_columns=3,
        ),
        StepConfig(
            key="mileage",
            state=SellStates.mileage,
            prompt_text="Укажите пробег (км):",
            step_type=StepType.TEXT_INPUT,
            validator=validate_mileage,
            error_text="Укажите пробег числом, например: 85000",
        ),
        StepConfig(
            key="price",
            state=SellStates.price,
            prompt_text="Укажите желаемую цену или выберите вариант:",
            step_type=StepType.TEXT_INPUT,
            buttons=[
                ("На ваше усмотрение", "На ваше усмотрение"),
            ],
            keyboard_columns=1,
        ),
        StepConfig(
            key="photos",
            state=SellStates.photos,
            prompt_text="Отправьте фото автомобиля (можно несколько).\n"
            "Когда закончите, нажмите \"Готово\".",
            step_type=StepType.PHOTO_UPLOAD,
            required=False,
        ),
        StepConfig(
            key="name",
            state=SellStates.name,
            prompt_text="Как к вам обращаться?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="phone",
            state=SellStates.phone,
            prompt_text="Укажите ваш номер телефона:",
            step_type=StepType.PHONE_INPUT,
        ),
        StepConfig(
            key="comment",
            state=SellStates.comment,
            prompt_text="Дополнительный комментарий:",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


sell_handler = SellHandler()
