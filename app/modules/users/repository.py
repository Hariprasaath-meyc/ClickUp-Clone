from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.users.models import User
from app.modules.users.profile_models import UserProfile


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
            profile=UserProfile(display_name=display_name),
        )

        session.add(user)
        await session.flush()

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
            select(User)
            .options(selectinload(User.profile))
            .where(User.cognito_sub == cognito_sub)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_profile_by_user_id(
        session: AsyncSession,
        user_id: UUID,
    ) -> UserProfile | None:
        result = await session.execute(
            select(UserProfile).where(
                UserProfile.user_id == user_id
            )
        )
        return result.scalar_one_or_none()