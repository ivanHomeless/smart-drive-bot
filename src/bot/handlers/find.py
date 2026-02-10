from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.handlers.buy import BUDGET_BUTTONS, validate_budget
from src.bot.states.find import FindStates


class FindHandler(BaseDialogHandler):
    service_type = "find"
    states_group = FindStates
    steps = [
        StepConfig(
            key="purpose",
            state=FindStates.purpose,
            prompt_text="Для каких целей подбираете авто?",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("Для города", "Для города"),
                ("Для семьи", "Для семьи"),
                ("Для бизнеса", "Для бизнеса"),
                ("Для бездорожья", "Для бездорожья"),
                ("Другое", "__custom__"),
            ],
            custom_input_prompt="Опишите, для каких целей:",
            keyboard_columns=2,
        ),
        StepConfig(
            key="budget",
            state=FindStates.budget,
            prompt_text="Выберите бюджет:",
            step_type=StepType.BUTTON_SELECT,
            buttons=BUDGET_BUTTONS,
            custom_input_prompt="Введите максимальный бюджет (число):",
            validator=validate_budget,
            error_text="Укажите бюджет числом, например: 1500000",
            keyboard_columns=1,
        ),
        StepConfig(
            key="brand_preference",
            state=FindStates.brand_preference,
            prompt_text="Есть предпочтения по марке?",
            step_type=StepType.TEXT_INPUT,
            buttons=[
                ("Без разницы", "Без разницы"),
            ],
            keyboard_columns=1,
        ),
        StepConfig(
            key="body_type",
            state=FindStates.body_type,
            prompt_text="Тип кузова:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("Седан", "Седан"),
                ("Кроссовер", "Кроссовер"),
                ("Внедорожник", "Внедорожник"),
                ("Хэтчбек", "Хэтчбек"),
                ("Универсал", "Универсал"),
                ("Любой", "Любой"),
            ],
            keyboard_columns=2,
        ),
        StepConfig(
            key="name",
            state=FindStates.name,
            prompt_text="Как к вам обращаться?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="phone",
            state=FindStates.phone,
            prompt_text="Укажите ваш номер телефона:",
            step_type=StepType.PHONE_INPUT,
        ),
        StepConfig(
            key="comment",
            state=FindStates.comment,
            prompt_text="Комментарий:",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


find_handler = FindHandler()
