import asyncio
import selectors
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionFactory
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


async def main():
    unique_id = uuid4().hex
    test_email = f"db-test-{unique_id}@example.com"
    test_sub = f"local-test-{unique_id}"

    async with SessionFactory() as session:
        try:
            user = await UserRepository.create(
                session,
                cognito_sub=test_sub,
                email=test_email,
                display_name="Database Test User",
            )

            # Commit makes the profile persistent.
            await session.commit()

            user_id = user.id

            print("Created user:")
            print("ID:", user_id)
            print("Email:", user.email)
            print("Created at:", user.created_at)

        except Exception:
            await session.rollback()
            raise

    # Open a fresh session to verify persistence.
    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        saved_user = result.scalar_one_or_none()

        assert saved_user is not None
        assert saved_user.email == test_email

        print("\nRetrieved user from PostgreSQL:")
        print("ID:", saved_user.id)
        print("Email:", saved_user.email)
        print("Name:", saved_user.display_name)

    print("\nDatabase CRUD test passed!")


if __name__ == "__main__":
   asyncio.run(
    main(),
    loop_factory=lambda: asyncio.SelectorEventLoop(
        selectors.SelectSelector()
    ),
)