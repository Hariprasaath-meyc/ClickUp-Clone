from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registered_users.models import RegisteredUser


class RegisteredUserRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        cognito_sub: str,
        email: str,
        display_name: str,
    ) -> RegisteredUser:

        registered_user = RegisteredUser(
            cognito_sub=cognito_sub,
            email=email,
            display_name=display_name,
        )

        db.add(registered_user)
        await db.flush()

        return registered_user

    @staticmethod
    async def get_by_cognito_sub(
        db: AsyncSession,
        cognito_sub: str,
    ) -> RegisteredUser | None:

        result = await db.execute(
            select(RegisteredUser).where(
                RegisteredUser.cognito_sub == cognito_sub
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        registered_user: RegisteredUser,
        status,
    ) -> RegisteredUser:

        registered_user.registration_status = status

        await db.flush()

        return registered_user

    @staticmethod
    async def get_by_email(
        db: AsyncSession,
        email: str,
    ) -> RegisteredUser | None:

        result = await db.execute(
            select(RegisteredUser).where(
                RegisteredUser.email == email
            )
        )

        return result.scalar_one_or_none()