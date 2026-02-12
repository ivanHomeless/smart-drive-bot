from datetime import date

from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.states.buy import BuyStates


def _buy_year_buttons() -> list[tuple[str, str]]:
    """Generate year-from buttons for buy branch."""
    current = date.today().year
    # Show current+1, then every year down 5, then a couple wider gaps
    years = [current + 1, current, current - 1, current - 2, current - 3,
             current - 5, current - 8]
    buttons = [(str(y), str(y)) for y in years]
    buttons.append(("Любой", "Любой"))
    buttons.append(("Другой", "__custom__"))
    return buttons


BUDGET_BUTTONS = [
    ("до 500 000", "до 500 000"),
    ("500 000 - 1 000 000", "500 000 - 1 000 000"),
    ("1 000 000 - 2 000 000", "1 000 000 - 2 000 000"),
    ("2 000 000 - 3 000 000", "2 000 000 - 3 000 000"),
    ("от 3 000 000", "от 3 000 000"),
    ("Указать свой", "__custom__"),
]


def validate_budget(text: str) -> str | None:
    cleaned = text.replace(" ", "").replace("руб", "").replace("р", "")
    try:
        val = int(cleaned)
        if val <= 0:
            return None
        return f"до {val:,}".replace(",", " ") + " руб."
    except ValueError:
        return None


class BuyHandler(BaseDialogHandler):
    service_type = "buy"
    states_group = BuyStates
    steps = [
        StepConfig(
            key="car_brand",
            state=BuyStates.car_brand,
            prompt_text="Какую марку/модель ищете?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="budget",
            state=BuyStates.budget,
            prompt_text="Выберите бюджет:",
            step_type=StepType.BUTTON_SELECT,
            buttons=BUDGET_BUTTONS,
            custom_input_prompt="Введите максимальный бюджет (число):",
            validator=validate_budget,
            error_text="Укажите бюджет числом, например: 1500000",
            keyboard_columns=1,
        ),
        StepConfig(
            key="year_from",
            state=BuyStates.year_from,
            prompt_text="Год выпуска от:",
            step_type=StepType.BUTTON_SELECT,
            buttons=_buy_year_buttons(),
            custom_input_prompt="Введите минимальный год выпуска:",
            keyboard_columns=3,
        ),
        StepConfig(
            key="transmission",
            state=BuyStates.transmission,
            prompt_text="Коробка передач:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("АКПП", "АКПП"),
                ("МКПП", "МКПП"),
                ("Робот", "Робот"),
                ("Вариатор", "Вариатор"),
                ("Любая", "Любая"),
            ],
            keyboard_columns=2,
        ),
        StepConfig(
            key="drive",
            state=BuyStates.drive,
            prompt_text="Привод:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("Передний", "Передний"),
                ("Задний", "Задний"),
                ("Полный", "Полный"),
                ("Любой", "Любой"),
            ],
            keyboard_columns=2,
        ),
        StepConfig(
            key="name",
            state=BuyStates.name,
            prompt_text="Как к вам обращаться?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="phone",
            state=BuyStates.phone,
            prompt_text="Укажите ваш номер телефона:",
            step_type=StepType.PHONE_INPUT,
        ),
        StepConfig(
            key="comment",
            state=BuyStates.comment,
            prompt_text="Дополнительные пожелания:",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


buy_handler = BuyHandler()
