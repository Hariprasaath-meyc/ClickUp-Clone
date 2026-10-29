import strawberry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.profile_models import UserProfile
from app.modules.users.types import UserType, UserProfileType


@strawberry.type
class UserQuery:

    @strawberry.field
    async def me(
        self,
        info: strawberry.Info,
    ) -> UserType:
        session: AsyncSession = info.context["db"]
        current_user = info.context["current_user"]

        result = await session.execute(
            select(User).where(
                User.cognito_sub == current_user["sub"]
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("User not found")

        profile_result = await session.execute(
            select(UserProfile).where(
                UserProfile.user_id == user.id
            )
        )
        profile = profile_result.scalar_one_or_none()

        return UserType(
            id=user.id,
            email=user.email,
            profile=(
                UserProfileType(
                    id=profile.id,
                    display_name=profile.display_name,
                    avatar_url=profile.avatar_url,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                )
                if profile
                else None
            ),
        )