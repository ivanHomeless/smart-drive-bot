from unittest.mock import MagicMock

from aiogram.types import Contact, Message

from src.bot.filters.phone import PhoneFilter


async def test_phone_filter_text_valid():
    msg = MagicMock(spec=Message)
    msg.contact = None
    msg.text = "+79991234567"

    f = PhoneFilter()
    result = await f(msg)
    assert result == {"phone": "+79991234567"}


async def test_phone_filter_text_invalid():
    msg = MagicMock(spec=Message)
    msg.contact = None
    msg.text = "not a phone"

    f = PhoneFilter()
    result = await f(msg)
    assert result is False


async def test_phone_filter_contact():
    contact = MagicMock(spec=Contact)
    contact.phone_number = "+79991234567"
    msg = MagicMock(spec=Message)
    msg.contact = contact
    msg.text = None

    f = PhoneFilter()
    result = await f(msg)
    assert result == {"phone": "+79991234567"}


async def test_phone_filter_no_text_no_contact():
    msg = MagicMock(spec=Message)
    msg.contact = None
    msg.text = None

    f = PhoneFilter()
    result = await f(msg)
    assert result is False
