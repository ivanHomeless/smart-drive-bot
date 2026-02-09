import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def dp(storage):
    return Dispatcher(storage=storage)
