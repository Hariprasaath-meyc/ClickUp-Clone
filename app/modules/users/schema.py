import strawberry
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.users.types import MeResult, UserProfileResult


@strawberry.type
class UserQuery:
    @strawberry.field
    async def me(
        self,
        info: strawberry.Info,
    ) -> MeResult:

        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("No application profile exists for this account.")

        profile = await UserRepository.get_profile_by_user_id(
            db,
            user.id,
        )

        if profile is None:
            raise GraphQLError("User profile not found.")

        return MeResult(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            profile=UserProfileResult(
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            ),
        )
