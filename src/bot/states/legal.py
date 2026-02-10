from aiogram.fsm.state import State, StatesGroup


class LegalStates(StatesGroup):
    question_type = State()
    description = State()
    name = State()
    phone = State()
    comment = State()
