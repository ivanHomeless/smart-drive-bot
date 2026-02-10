from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.lead import LeadRepository
from src.db.repositories.user import UserRepository


async def _create_user(session: AsyncSession) -> int:
    repo = UserRepository(session)
    user = await repo.create_or_update(telegram_id=100, username="test")
    return user.id


async def test_create_lead(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)
    lead = await repo.create(
        user_id=user_id,
        service_type="sell",
        data={"car_brand": "Toyota"},
    )
    assert lead.id is not None
    assert lead.service_type == "sell"
    assert lead.data["car_brand"] == "Toyota"
    assert lead.status == "draft"


async def test_update_status_to_sent(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)
    lead = await repo.create(user_id=user_id, service_type="buy", data={})

    await repo.update_status(lead.id, "sent", amo_lead_id=12345)
    await db_session.refresh(lead)

    assert lead.status == "sent"
    assert lead.amo_lead_id == 12345
    assert lead.sent_at is not None


async def test_update_status_to_error(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)
    lead = await repo.create(user_id=user_id, service_type="check", data={})

    await repo.update_status(lead.id, "error", error_message="CRM timeout")
    await db_session.refresh(lead)

    assert lead.status == "error"
    assert lead.error_message == "CRM timeout"


async def test_get_failed_leads(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)

    await repo.create(user_id=user_id, service_type="sell", data={}, status="error")
    await repo.create(user_id=user_id, service_type="buy", data={}, status="sent")
    await repo.create(user_id=user_id, service_type="find", data={}, status="error")

    failed = await repo.get_failed_leads()
    assert len(failed) == 2
    assert all(l.status == "error" for l in failed)


async def test_increment_retry(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)
    lead = await repo.create(user_id=user_id, service_type="sell", data={}, status="error")

    await repo.increment_retry(lead.id)
    await db_session.refresh(lead)
    assert lead.retry_count == 1

    await repo.increment_retry(lead.id)
    await db_session.refresh(lead)
    assert lead.retry_count == 2


async def test_get_failed_leads_respects_max_retries(db_session: AsyncSession):
    user_id = await _create_user(db_session)
    repo = LeadRepository(db_session)
    lead = await repo.create(user_id=user_id, service_type="sell", data={}, status="error")

    for _ in range(5):
        await repo.increment_retry(lead.id)

    failed = await repo.get_failed_leads(max_retries=5)
    assert len(failed) == 0
