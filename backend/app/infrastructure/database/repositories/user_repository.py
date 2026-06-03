from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.user import UserModel


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_cognito_sub(self, cognito_sub: str) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.cognito_sub == cognito_sub)
        )
        return result.scalar_one_or_none()
