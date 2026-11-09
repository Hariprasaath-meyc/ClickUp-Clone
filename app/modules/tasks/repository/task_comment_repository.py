import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import TaskComment


class TaskCommentRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> TaskComment:

        comment = TaskComment(
            workspace_id=workspace_id,
            task_id=task_id,
            user_id=user_id,
            content=content,
        )

        db.add(comment)
        await db.flush()

        return comment

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        comment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> TaskComment | None:

        result = await db.execute(
            select(TaskComment).where(
                TaskComment.id == comment_id,
                TaskComment.workspace_id == workspace_id,
                TaskComment.task_id == task_id,
                TaskComment.deleted_at.is_(None),
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_task_comments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> list[TaskComment]:

        result = await db.execute(
            select(TaskComment)
            .where(
                TaskComment.workspace_id == workspace_id,
                TaskComment.task_id == task_id,
                TaskComment.deleted_at.is_(None),
            )
            .order_by(TaskComment.created_at.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        comment: TaskComment,
        content: str,
    ) -> TaskComment:

        comment.content = content

        await db.flush()

        return comment

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        comment: TaskComment,
    ) -> TaskComment:

        comment.deleted_at = func.now()

        await db.flush()

        return comment
