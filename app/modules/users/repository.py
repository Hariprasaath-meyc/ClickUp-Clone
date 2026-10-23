from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        cognito_sub: str,
        email: str,
        display_name: str,
    ) -> User:
        user = User(
            cognito_sub=cognito_sub,
            email=email,
            display_name=display_name,
        )

        session.add(user)

        await session.flush()
        await session.refresh(user)

        return user

    @staticmethod
    async def get_by_email(
        session: AsyncSession,
        email: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    
    @staticmethod
    async def get_by_cognito_sub(
        session: AsyncSession,
        cognito_sub: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.cognito_sub == cognito_sub
            )
        )
        return result.scalar_one_or_none()
