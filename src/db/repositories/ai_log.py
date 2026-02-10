from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AiLog


class AiLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        user_message: str,
        ai_response: dict | None = None,
        intent: str | None = None,
        confidence: float | None = None,
        model_used: str | None = None,
        used_fallback: bool = False,
        latency_ms: int | None = None,
    ) -> AiLog:
        log = AiLog(
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response,
            intent=intent,
            confidence=confidence,
            model_used=model_used,
            used_fallback=used_fallback,
            latency_ms=latency_ms,
        )
        self.session.add(log)
        await self.session.flush()
        return log
