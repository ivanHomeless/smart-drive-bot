from aiogram.fsm.state import State, StatesGroup


class BuyStates(StatesGroup):
    car_brand = State()
    budget = State()
    year_from = State()
    transmission = State()
    drive = State()
    name = State()
    phone = State()
    comment = State()
