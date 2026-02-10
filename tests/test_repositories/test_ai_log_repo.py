from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.ai_log import AiLogRepository
from src.db.repositories.user import UserRepository


async def test_create_ai_log(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.create_or_update(telegram_id=500)

    repo = AiLogRepository(db_session)
    log = await repo.create(
        user_id=user.id,
        user_message="Хочу продать Toyota",
        ai_response={"intent": "sell", "confidence": 0.95},
        intent="sell",
        confidence=0.95,
        model_used="gpt-4o-mini",
        used_fallback=False,
        latency_ms=120,
    )
    assert log.id is not None
    assert log.intent == "sell"
    assert log.confidence == 0.95
    assert log.model_used == "gpt-4o-mini"
    assert log.used_fallback is False
    assert log.latency_ms == 120


async def test_create_ai_log_minimal(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.create_or_update(telegram_id=501)

    repo = AiLogRepository(db_session)
    log = await repo.create(
        user_id=user.id,
        user_message="Привет",
    )
    assert log.id is not None
    assert log.intent is None
    assert log.confidence is None
