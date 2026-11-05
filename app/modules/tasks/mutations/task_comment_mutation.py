import strawberry

from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tasks.types.task_comment_types import DeleteTaskCommentInput, DeleteTaskCommentResult, UpdateTaskCommentInput
from app.modules.users.repository import UserRepository

from app.modules.tasks.services import TaskCommentService
from app.modules.tasks.types import (
    CreateTaskCommentInput,
    TaskCommentType,
    TaskCommentResult,
)


@strawberry.type
class TaskCommentMutation:

    @strawberry.mutation
    async def create_task_comment(
        self,
        info: strawberry.Info,
        input: CreateTaskCommentInput,
    ) -> TaskCommentResult:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            comment = await TaskCommentService.create_comment(
                db=db,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                user_id=user.id,
                content=input.content,
            )

            await db.commit()
            await db.refresh(comment)

            return TaskCommentResult(
                success=True,
                message="Comment created successfully.",
                comment=TaskCommentType(
                    id=comment.id,
                    workspace_id=comment.workspace_id,
                    task_id=comment.task_id,
                    user_id=comment.user_id,
                    content=comment.content,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                ),
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
                "Unable to create comment."
            ) from exc

    @strawberry.mutation
    async def update_task_comment(
        self,
        info: strawberry.Info,
        input: UpdateTaskCommentInput,
    ) -> TaskCommentResult:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            comment = await TaskCommentService.update_comment(
                db=db,
                comment_id=input.comment_id,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                user_id=user.id,
                content=input.content,
            )

            await db.commit()
            await db.refresh(comment)

            return TaskCommentResult(
                success=True,
                message="Comment updated successfully.",
                comment=TaskCommentType(
                    id=comment.id,
                    workspace_id=comment.workspace_id,
                    task_id=comment.task_id,
                    user_id=comment.user_id,
                    content=comment.content,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                ),
            )

        except GraphQLError:
            await db.rollback()
            raise

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError("Unable to update comment.") from exc

    @strawberry.mutation
    async def delete_task_comment(
        self,
        info: strawberry.Info,
        input: DeleteTaskCommentInput,
    ) -> DeleteTaskCommentResult:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            await TaskCommentService.delete_comment(
                db=db,
                comment_id=input.comment_id,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                user_id=user.id,
            )

            await db.commit()

            return DeleteTaskCommentResult(
                success=True,
                message="Comment deleted successfully.",
            )

        except GraphQLError:
            await db.rollback()
            raise

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError("Unable to delete comment.") from exc