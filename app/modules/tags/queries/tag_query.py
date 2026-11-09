import uuid

import strawberry
from strawberry.types import Info

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tags.services import TagService
from app.modules.tags.types import TagType
from app.modules.users.repository import UserRepository


@strawberry.type
class TagQuery:
    @strawberry.field
    async def workspace_tags(
        self,
        info: Info,
        workspace_id: uuid.UUID,
    ) -> list[TagType]:

        db = info.context["db"]

        claims = require_authenticated_user(info)

        user = await UserRepository.get_by_cognito_sub(
            session=db,
            cognito_sub=claims["sub"],
        )

        if user is None:
            raise ValueError("User not found.")

        tags = await TagService.get_workspace_tags(
            db=db,
            workspace_id=workspace_id,
            user_id=user.id,
        )

        return [
            TagType(
                id=tag.id,
                workspace_id=tag.workspace_id,
                name=tag.name,
                created_by=tag.created_by,
                created_at=tag.created_at,
            )
            for tag in tags
        ]
