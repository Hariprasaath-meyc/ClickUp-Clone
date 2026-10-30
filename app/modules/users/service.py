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
            # Start the transaction before querying the database.
            async with session.begin():
                # 1. Retrieve an existing user by Cognito identity.
                user = await UserRepository.get_by_cognito_sub(
                    session,
                    cognito_sub,
                )

                if user is not None:
                    return user

                # 2. Prevent linking a different Cognito identity
                # to an email already associated with another user.
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

                # 3. Create the user and profile together.
                user = await UserRepository.create(
                    session,
                    cognito_sub=cognito_sub,
                    email=email,
                    display_name=display_name,
                )

                return user

        except IntegrityError as exc:
            raise ValueError(
                "Unable to create the user because the email "
                "or Cognito identity already exists."
            ) from exc