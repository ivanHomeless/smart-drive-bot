from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Lead


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        service_type: str,
        data: dict,
        status: str = "draft",
    ) -> Lead:
        lead = Lead(
            user_id=user_id,
            service_type=service_type,
            data=data,
            status=status,
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def update_status(
        self,
        lead_id: int,
        status: str,
        amo_lead_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if amo_lead_id is not None:
            values["amo_lead_id"] = amo_lead_id
        if error_message is not None:
            values["error_message"] = error_message
        if status == "sent":
            values["sent_at"] = datetime.now(timezone.utc)

        await self.session.execute(
            update(Lead).where(Lead.id == lead_id).values(**values)
        )
        await self.session.flush()

    async def get_failed_leads(self, max_retries: int = 5) -> list[Lead]:
        result = await self.session.execute(
            select(Lead)
            .where(Lead.status == "error")
            .where(Lead.retry_count < max_retries)
            .order_by(Lead.created_at)
        )
        return list(result.scalars().all())

    async def increment_retry(self, lead_id: int) -> None:
        await self.session.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(retry_count=Lead.retry_count + 1)
        )
        await self.session.flush()
