from __future__ import annotations

import logging

from src.services.amocrm.client import AmoCRMClient

logger = logging.getLogger(__name__)


class NotesService:
    """AmoCRM notes operations."""

    def __init__(self, client: AmoCRMClient) -> None:
        self._client = client

    async def add_to_lead(self, lead_id: int, text: str) -> int:
        """Add a text note to a lead. Returns the note ID."""
        body = [
            {
                "note_type": "common",
                "params": {"text": text},
            }
        ]

        result = await self._client.post(
            f"/api/v4/leads/{lead_id}/notes", json=body
        )
        note_id = result["_embedded"]["notes"][0]["id"]
        logger.info("Added note %d to AmoCRM lead %d", note_id, lead_id)
        return note_id
