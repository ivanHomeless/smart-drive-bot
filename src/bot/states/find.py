from aiogram.fsm.state import State, StatesGroup


class FindStates(StatesGroup):
    purpose = State()
    budget = State()
    brand_preference = State()
    body_type = State()
    name = State()
    phone = State()
    comment = State()
