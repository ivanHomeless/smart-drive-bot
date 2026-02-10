from aiogram.fsm.state import State, StatesGroup


class SellStates(StatesGroup):
    car_brand = State()
    year = State()
    mileage = State()
    price = State()
    photos = State()
    name = State()
    phone = State()
    comment = State()
