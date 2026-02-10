from src.bot.handlers.base_dialog import BaseDialogHandler, StepConfig, StepType
from src.bot.states.legal import LegalStates


class LegalHandler(BaseDialogHandler):
    service_type = "legal"
    states_group = LegalStates
    steps = [
        StepConfig(
            key="question_type",
            state=LegalStates.question_type,
            prompt_text="Выберите тип вопроса:",
            step_type=StepType.BUTTON_SELECT,
            buttons=[
                ("Переоформление / постановка на учёт", "Переоформление"),
                ("Страхование (ОСАГО / КАСКО)", "Страхование"),
                ("Возврат авто / спор с продавцом", "Возврат / спор"),
                ("Другое", "__custom__"),
            ],
            custom_input_prompt="Опишите ваш вопрос:",
            keyboard_columns=1,
        ),
        StepConfig(
            key="description",
            state=LegalStates.description,
            prompt_text="Кратко опишите ситуацию:",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="name",
            state=LegalStates.name,
            prompt_text="Как к вам обращаться?",
            step_type=StepType.TEXT_INPUT,
        ),
        StepConfig(
            key="phone",
            state=LegalStates.phone,
            prompt_text="Укажите ваш номер телефона:",
            step_type=StepType.PHONE_INPUT,
        ),
        StepConfig(
            key="comment",
            state=LegalStates.comment,
            prompt_text="Комментарий:",
            step_type=StepType.TEXT_INPUT,
            required=False,
        ),
    ]


legal_handler = LegalHandler()
