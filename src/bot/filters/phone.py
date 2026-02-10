from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.utils.phone import validate_phone


class PhoneFilter(BaseFilter):
    """Filter that validates phone from text or shared contact.

    On match, sets data['phone'] to normalized E.164 phone string.
    """

    async def __call__(self, message: Message) -> bool | dict:
        # Check shared contact first
        if message.contact and message.contact.phone_number:
            phone = validate_phone(message.contact.phone_number)
            if phone:
                return {"phone": phone}

        # Try text input
        if message.text:
            phone = validate_phone(message.text)
            if phone:
                return {"phone": phone}

        return False
