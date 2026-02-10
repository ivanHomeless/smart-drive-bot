from __future__ import annotations

import logging

from src.config import settings
from src.services.amocrm.client import AmoCRMClient
from src.services.amocrm.models import CustomFieldValue

logger = logging.getLogger(__name__)


class ContactsService:
    """AmoCRM contacts operations."""

    def __init__(self, client: AmoCRMClient) -> None:
        self._client = client

    async def find_by_phone(self, phone: str) -> dict | None:
        """Search for a contact by phone number. Returns first match or None."""
        data = await self._client.get(
            "/api/v4/contacts",
            params={"query": phone, "limit": 1},
        )
        contacts = data.get("_embedded", {}).get("contacts", [])
        if contacts:
            return contacts[0]
        return None

    async def create(
        self,
        name: str,
        phone: str,
        telegram_id: int,
        telegram_username: str | None = None,
    ) -> int:
        """Create a new contact. Returns the contact ID."""
        custom_fields = [
            CustomFieldValue(
                field_id=settings.AMOCRM_FIELD_TELEGRAM_ID,
                values=[{"value": str(telegram_id)}],
            ),
        ]
        if telegram_username and settings.AMOCRM_FIELD_TELEGRAM_USERNAME:
            custom_fields.append(
                CustomFieldValue(
                    field_id=settings.AMOCRM_FIELD_TELEGRAM_USERNAME,
                    values=[{"value": telegram_username}],
                )
            )

        body = [
            {
                "name": name,
                "custom_fields_values": [
                    {"field_id": cf.field_id, "values": cf.values}
                    for cf in custom_fields
                ] + [
                    {
                        "field_code": "PHONE",
                        "values": [{"value": phone, "enum_code": "MOB"}],
                    }
                ],
                "tags_to_add": [{"name": "telegram_new"}],
            }
        ]

        data = await self._client.post("/api/v4/contacts", json=body)
        contact_id = data["_embedded"]["contacts"][0]["id"]
        logger.info("Created AmoCRM contact %d for phone %s", contact_id, phone)
        return contact_id

    async def update(self, contact_id: int, **fields) -> None:
        """Update an existing contact with new custom fields."""
        body = [
            {
                "id": contact_id,
                "tags_to_add": [{"name": "telegram_repeat"}],
            }
        ]
        await self._client.patch("/api/v4/contacts", json=body)
        logger.info("Updated AmoCRM contact %d", contact_id)
