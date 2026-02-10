from __future__ import annotations

import logging

from src.config import settings
from src.services.amocrm.client import AmoCRMClient
from src.services.amocrm.models import CustomFieldValue
from src.utils.formatters import SERVICE_TYPE_LABELS

logger = logging.getLogger(__name__)

# Mapping of data keys to AmoCRM custom field settings attribute names
FIELD_MAPPING = {
    "car_brand": "AMOCRM_FIELD_CAR_BRAND",
    "year": "AMOCRM_FIELD_CAR_YEAR",
    "budget": "AMOCRM_FIELD_BUDGET",
    "mileage": "AMOCRM_FIELD_MILEAGE",
    "transmission": "AMOCRM_FIELD_TRANSMISSION",
    "drive": "AMOCRM_FIELD_DRIVE_TYPE",
    "body_type": "AMOCRM_FIELD_BODY_TYPE",
    "vin": "AMOCRM_FIELD_VIN_NUMBER",
    "check_type": "AMOCRM_FIELD_CHECK_TYPE",
}


class LeadsService:
    """AmoCRM leads operations."""

    def __init__(self, client: AmoCRMClient) -> None:
        self._client = client

    async def create(
        self,
        title: str,
        contact_id: int,
        service_type: str,
        data: dict,
    ) -> int:
        """Create a lead linked to a contact. Returns the lead ID."""
        custom_fields = self._build_custom_fields(service_type, data)

        body = [
            {
                "name": title,
                "pipeline_id": settings.AMOCRM_PIPELINE_ID,
                "status_id": settings.AMOCRM_STATUS_ID,
                "responsible_user_id": settings.AMOCRM_RESPONSIBLE_USER_ID,
                "custom_fields_values": [
                    {"field_id": cf.field_id, "values": cf.values}
                    for cf in custom_fields
                ],
                "_embedded": {
                    "contacts": [{"id": contact_id}],
                },
            }
        ]

        result = await self._client.post("/api/v4/leads", json=body)
        lead_id = result["_embedded"]["leads"][0]["id"]
        logger.info("Created AmoCRM lead %d: %s", lead_id, title)
        return lead_id

    def _build_custom_fields(
        self, service_type: str, data: dict
    ) -> list[CustomFieldValue]:
        fields = []

        # Service type
        if settings.AMOCRM_FIELD_SERVICE_TYPE:
            label = SERVICE_TYPE_LABELS.get(service_type, service_type)
            fields.append(
                CustomFieldValue(
                    field_id=settings.AMOCRM_FIELD_SERVICE_TYPE,
                    values=[{"value": label}],
                )
            )

        # Source
        if settings.AMOCRM_FIELD_SOURCE:
            fields.append(
                CustomFieldValue(
                    field_id=settings.AMOCRM_FIELD_SOURCE,
                    values=[{"value": "Telegram Bot"}],
                )
            )

        # Data fields
        for data_key, settings_attr in FIELD_MAPPING.items():
            value = data.get(data_key)
            field_id = getattr(settings, settings_attr, 0)
            if value and field_id:
                fields.append(
                    CustomFieldValue(
                        field_id=field_id,
                        values=[{"value": str(value)}],
                    )
                )

        return fields
