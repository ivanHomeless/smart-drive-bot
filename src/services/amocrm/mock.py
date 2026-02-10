from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_NEXT_ID = 1000


def _next_id() -> int:
    global _NEXT_ID
    _NEXT_ID += 1
    return _NEXT_ID


class MockAmoCRMClient:
    """Mock AmoCRM client for development without real API access.

    Logs all calls and returns fake but structurally valid responses.
    """

    async def get(self, path: str, params: dict | None = None) -> dict:
        logger.info("[MOCK] GET %s params=%s", path, params)

        if "/contacts" in path and params and "query" in params:
            # Simulate contact not found
            return {"_embedded": {"contacts": []}}

        return {}

    async def post(self, path: str, json: Any = None) -> dict:
        logger.info("[MOCK] POST %s body=%s", path, json)

        if "/contacts" in path:
            contact_id = _next_id()
            logger.info("[MOCK] Created contact %d", contact_id)
            return {
                "_embedded": {
                    "contacts": [{"id": contact_id, "request_id": "0"}]
                }
            }

        if "/notes" in path:
            note_id = _next_id()
            # Extract lead_id from path like /api/v4/leads/123/notes
            parts = path.split("/")
            lead_id = int(parts[-2]) if len(parts) >= 3 else 0
            logger.info("[MOCK] Created note %d for lead %d", note_id, lead_id)
            return {
                "_embedded": {
                    "notes": [
                        {"id": note_id, "entity_id": lead_id, "request_id": "0"}
                    ]
                }
            }

        if "/leads" in path:
            lead_id = _next_id()
            logger.info("[MOCK] Created lead %d", lead_id)
            return {
                "_embedded": {
                    "leads": [{"id": lead_id, "request_id": "0"}]
                }
            }

        return {}

    async def patch(self, path: str, json: Any = None) -> dict:
        logger.info("[MOCK] PATCH %s body=%s", path, json)
        return {}
