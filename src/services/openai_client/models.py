from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIResponse:
    """Structured response from OpenAI classification."""

    intent: str = "unknown"
    confidence: float = 0.0
    entities: dict[str, str | None] = field(default_factory=dict)
    reply: str = ""
    model_used: str = ""
    used_fallback: bool = False

    @property
    def has_intent(self) -> bool:
        return self.intent not in ("unknown", "faq", "")

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7
