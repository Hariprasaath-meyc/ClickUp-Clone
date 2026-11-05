import strawberry
from strawberry.types import Info
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tags.types.tag_types import RemoveTagsInput, RemoveTagsResult
from app.modules.users.repository import UserRepository

from app.modules.tags.services import TagService

from app.modules.tags.types import (
    AssignTagsInput,
    TagResult,
    TagType,
)
import logging

logger = logging.getLogger(__name__)

@strawberry.type
class TagMutation:

    @strawberry.mutation
    async def assign_tags(
        self,
        info: strawberry.Info,
        input: AssignTagsInput,
    ) -> TagResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate requester
            claims = require_authenticated_user(info)

            # 2. Resolve Cognito identity to local user
            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # 3. Assign tags through service
            task_tags = await TagService.assign_tags(
                db=db,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                tag_names=input.tag_names,
                user_id=user.id,
            )

            # 4. Commit transaction
            await db.commit()

            # 5. Map ORM objects to GraphQL types
            tags = [
                TagType(
                    id=item.tag.id,
                    workspace_id=item.tag.workspace_id,
                    name=item.tag.name,
                    created_by=item.tag.created_by,
                    created_at=item.tag.created_at,
                )
                for item in task_tags
            ]

            return TagResult(
                success=True,
                message="Tags assigned successfully.",
                tags=tags,
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to assign tags."
            ) from exc

    @strawberry.mutation
    async def remove_tags(
        self,
        info: Info,
        input: RemoveTagsInput,
    ) -> RemoveTagsResult:

        db = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db, claims["sub"]
            )

            if user is None:
                raise ValueError("User not found.")

            removed_count = await TagService.remove_tags(
                db=db,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                tag_ids=input.tag_ids,
                user_id=user.id,
            )

            await db.commit()

            return RemoveTagsResult(
                success=True,
                message="Tags removed successfully.",
                removed_count=removed_count,
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            logger.exception("Unexpected error while removing tags.")
            raise GraphQLError("Unable to remove tags.") from exc