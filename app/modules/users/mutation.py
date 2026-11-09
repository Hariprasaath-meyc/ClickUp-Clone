import strawberry
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.users.types import (
    UpdateMyProfileInput,
    UserProfileResult,
)


@strawberry.type
class UserMutation:
    @strawberry.mutation
    async def update_my_profile(
        self,
        info: strawberry.Info,
        input: UpdateMyProfileInput,
    ) -> UserProfileResult:

        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        profile = await UserRepository.get_profile_by_user_id(
            db,
            user.id,
        )

        if profile is None:
            raise GraphQLError("User profile not found.")

        if input.display_name is not None:
            display_name = input.display_name.strip()

            if not display_name:
                raise GraphQLError("Display name cannot be empty.")

            if len(display_name) > 100:
                raise GraphQLError("Display name cannot exceed 100 characters.")

            profile.display_name = display_name

        if input.avatar_url is not None:
            profile.avatar_url = input.avatar_url

        try:
            await db.commit()
            await db.refresh(profile)

        except Exception:
            await db.rollback()
            raise

        return UserProfileResult(
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
