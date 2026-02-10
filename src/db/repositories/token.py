from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AmoToken


class TokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_current(self) -> AmoToken | None:
        result = await self.session.execute(
            select(AmoToken).order_by(AmoToken.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, token: AmoToken) -> AmoToken:
        self.session.add(token)
        await self.session.flush()
        return token
