from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.user import UserRepository


async def test_create_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create_or_update(
        telegram_id=111,
        username="alice",
        first_name="Alice",
    )
    assert user.id is not None
    assert user.telegram_id == 111
    assert user.username == "alice"


async def test_get_by_telegram_id(db_session: AsyncSession):
    repo = UserRepository(db_session)
    await repo.create_or_update(telegram_id=222, username="bob")

    found = await repo.get_by_telegram_id(222)
    assert found is not None
    assert found.username == "bob"


async def test_get_by_telegram_id_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    found = await repo.get_by_telegram_id(999)
    assert found is None


async def test_update_existing_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user1 = await repo.create_or_update(telegram_id=333, username="old_name")
    user2 = await repo.create_or_update(telegram_id=333, username="new_name")

    assert user1.id == user2.id
    assert user2.username == "new_name"


async def test_update_phone(db_session: AsyncSession):
    repo = UserRepository(db_session)
    await repo.create_or_update(telegram_id=444)
    user = await repo.create_or_update(telegram_id=444, phone="+79991234567")
    assert user.phone == "+79991234567"
