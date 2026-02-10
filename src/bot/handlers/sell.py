from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.states.sell import SellStates


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
            buttons=[
                ("2024", "2024"),
                ("2023", "2023"),
                ("2022", "2022"),
                ("2021", "2021"),
                ("2020", "2020"),
                ("2019", "2019"),
                ("2018", "2018"),
                ("2017", "2017"),
                ("2016", "2016"),
                ("2015", "2015"),
                ("Старше", "__custom__"),
            ],
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
