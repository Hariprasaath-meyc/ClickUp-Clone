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
            # 1. Retrieve existing user
            user = await UserRepository.get_by_cognito_sub(
                session,
                cognito_sub,
            )

            if user is not None:
                return user

            # 2. Check whether email already exists
            existing_email_user = (
                await UserRepository.get_by_email(
                    session,
                    email,
                )
            )

            if existing_email_user is not None:
                raise ValueError(
                    "This email is already associated with "
                    "another user account."
                )

            # 3. Create user and profile
            user = await UserRepository.create(
                session,
                cognito_sub=cognito_sub,
                email=email,
                display_name=display_name,
            )

            await session.flush()

            return user

        except IntegrityError as exc:
            raise ValueError(
                "Unable to create the user because the email "
                "or Cognito identity already exists."
            ) from exc