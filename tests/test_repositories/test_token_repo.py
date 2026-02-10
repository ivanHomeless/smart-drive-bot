from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AmoToken
from src.db.repositories.token import TokenRepository


async def test_save_and_get_token(db_session: AsyncSession):
    repo = TokenRepository(db_session)
    token = AmoToken(
        access_token="acc_123",
        refresh_token="ref_456",
        expires_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    saved = await repo.save(token)
    assert saved.id is not None

    current = await repo.get_current()
    assert current is not None
    assert current.access_token == "acc_123"
    assert current.refresh_token == "ref_456"


async def test_get_current_returns_latest(db_session: AsyncSession):
    repo = TokenRepository(db_session)

    token1 = AmoToken(
        access_token="old",
        refresh_token="old_ref",
        expires_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    await repo.save(token1)

    token2 = AmoToken(
        access_token="new",
        refresh_token="new_ref",
        expires_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    await repo.save(token2)

    current = await repo.get_current()
    assert current.access_token == "new"


async def test_get_current_empty(db_session: AsyncSession):
    repo = TokenRepository(db_session)
    assert await repo.get_current() is None
