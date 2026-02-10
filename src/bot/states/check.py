from aiogram.fsm.state import State, StatesGroup


class CheckStates(StatesGroup):
    check_type = State()
    car_brand = State()
    vin = State()
    name = State()
    phone = State()
    comment = State()
