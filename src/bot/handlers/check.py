from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.states.check import CheckStates


class CheckHandler(BaseDialogHandler):
    service_type = "check"
    states_group = CheckStates
    steps = [
        StepConfig(
            key="check_type",
            state=CheckStates.check_type,
            prompt_text="Выберите тип проверки:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("Техническая диагностика", "Техническая диагностика"),
                ("Юридическая проверка", "Юридическая проверка"),
                ("Комплексная проверка", "Комплексная проверка"),
            ],
            keyboard_columns=1,
        ),
        StepConfig(
            key="car_brand",
            state=CheckStates.car_brand,
            prompt_text="Укажите марку и модель автомобиля:",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="vin",
            state=CheckStates.vin,
            prompt_text="Укажите VIN или госномер (если есть):",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
        StepConfig(
            key="name",
            state=CheckStates.name,
            prompt_text="Как к вам обращаться?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="phone",
            state=CheckStates.phone,
            prompt_text="Укажите ваш номер телефона:",
            step_type=StepType.PHONE_INPUT,
        ),
        StepConfig(
            key="comment",
            state=CheckStates.comment,
            prompt_text="Комментарий:",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


check_handler = CheckHandler()
