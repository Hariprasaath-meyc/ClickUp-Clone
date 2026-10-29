from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class UserService:

    @staticmethod
    async def create_from_cognito(
        session: AsyncSession,
        *,
        cognito_sub: str,
        email: str,
        display_name: str,
    ) -> User:
        try:
            async with session.begin():
                user = await UserRepository.create(
                    session,
                    cognito_sub=cognito_sub,
                    email=email,
                    display_name=display_name,
                )

            return user

        except IntegrityError as exc:
            raise ValueError(
                "Unable to create the user. "
                "The email or Cognito identity may already exist."
            ) from exc