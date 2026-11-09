import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums import TaskHistoryAction
from app.modules.tasks.repository import (
    TaskCommentRepository,
    TaskRepository,
)
from app.modules.tasks.services.task_history_service import TaskHistoryService
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)


class TaskCommentService:
    @staticmethod
    async def create_comment(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ):

        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_READ,
        )

        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        if not content or not content.strip():
            raise ValueError("Comment cannot be empty.")

        comment = await TaskCommentRepository.create(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            user_id=user_id,
            content=content.strip(),
        )

        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=user_id,
            action=TaskHistoryAction.COMMENT_CREATED,
            changes={
                "comment_id": str(comment.id),
                "content": comment.content,
            },
        )

        return comment

    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ):

        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_READ,
        )

        comment = await TaskCommentRepository.get_by_id(
            db=db,
            comment_id=comment_id,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        if comment is None:
            raise ValueError("Comment not found.")

        if comment.user_id != user_id:
            raise ValueError("You can only edit your own comments.")

        if not content or not content.strip():
            raise ValueError("Comment cannot be empty.")

        old_content = comment.content
        new_content = content.strip()

        await TaskCommentRepository.update(
            db=db,
            comment=comment,
            content=new_content,
        )

        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=user_id,
            action=TaskHistoryAction.COMMENT_UPDATED,
            changes={
                "comment_id": str(comment.id),
                "content": {
                    "old": old_content,
                    "new": new_content,
                },
            },
        )

        return comment

    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ):

        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_READ,
        )

        comment = await TaskCommentRepository.get_by_id(
            db=db,
            comment_id=comment_id,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        if comment is None:
            raise ValueError("Comment not found.")

        if comment.user_id != user_id:
            raise ValueError("You can only delete your own comments.")

        await TaskCommentRepository.soft_delete(
            db=db,
            comment=comment,
        )

        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=user_id,
            action=TaskHistoryAction.COMMENT_DELETED,
            changes={
                "comment_id": str(comment.id),
                "content": comment.content,
            },
        )

        return True
