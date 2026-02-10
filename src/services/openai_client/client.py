from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from src.config import settings
from src.services.openai_client.models import AIResponse
from src.services.openai_client.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 500
REQUEST_TIMEOUT = 10


class OpenAIClient:
    """OpenAI API client with smart fallback (mini -> full model)."""

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def classify(self, user_message: str) -> AIResponse:
        """Classify user message: detect intent and extract entities.

        Uses gpt-4o-mini first. If confidence is low, JSON is invalid,
        or intent is empty, retries with gpt-4o (smart fallback).
        """
        truncated = user_message[:MAX_MESSAGE_LENGTH]

        # 1. Try primary model
        response = await self._call_model(truncated, model=settings.OPENAI_MODEL)

        # 2. Check if fallback is needed
        if self._needs_fallback(response):
            logger.info(
                "Smart fallback triggered: intent=%s confidence=%.2f model=%s",
                response.intent, response.confidence, response.model_used,
            )
            fallback = await self._call_model(
                truncated, model=settings.OPENAI_FALLBACK_MODEL,
            )
            fallback.used_fallback = True
            return fallback

        return response

    async def _call_model(self, message: str, model: str) -> AIResponse:
        """Make a single API call and parse the response."""
        start = time.monotonic()
        try:
            completion = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                timeout=REQUEST_TIMEOUT,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            raw = completion.choices[0].message.content or ""
            logger.debug("OpenAI response (model=%s, %dms): %s", model, elapsed_ms, raw)
            return self._parse_response(raw, model)

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.exception("OpenAI API error (model=%s, %dms)", model, elapsed_ms)
            return AIResponse(
                intent="unknown",
                confidence=0.0,
                reply="",
                model_used=model,
            )

    def _parse_response(self, raw: str, model: str) -> AIResponse:
        """Parse JSON response from the model."""
        try:
            # Strip potential markdown code fences
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first line (```json) and last line (```)
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)

            data: dict[str, Any] = json.loads(text)

            entities = data.get("entities", {})
            # Ensure entities is a dict with expected keys
            if not isinstance(entities, dict):
                entities = {}

            return AIResponse(
                intent=data.get("intent", "") or "",
                confidence=float(data.get("confidence", 0.0)),
                entities=entities,
                reply=data.get("reply", ""),
                model_used=model,
            )

        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse OpenAI response: %s (raw: %s)", exc, raw[:200])
            return AIResponse(
                intent="",
                confidence=0.0,
                reply=raw[:200] if raw else "",
                model_used=model,
            )

    def _needs_fallback(self, response: AIResponse) -> bool:
        """Check if the primary model response needs smart fallback."""
        if not response.intent:
            return True
        if response.confidence < settings.OPENAI_SMART_FALLBACK_CONFIDENCE:
            return True
        return False
