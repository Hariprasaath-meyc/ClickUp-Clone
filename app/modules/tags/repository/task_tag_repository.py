import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.tags.models import TaskTag


class TaskTagRepository:

    @staticmethod
    async def assign_tag(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> TaskTag:

        task_tag = TaskTag(
            workspace_id=workspace_id,
            task_id=task_id,
            tag_id=tag_id,
            assigned_by=assigned_by,
        )

        db.add(task_tag)

        await db.flush()

        return task_tag

    @staticmethod
    async def get_task_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,    
        task_id: uuid.UUID,
    ) -> list[TaskTag]:

        result = await db.execute(
            select(TaskTag)
            .options(selectinload(TaskTag.tag))
            .where(
                TaskTag.workspace_id == workspace_id,
                TaskTag.task_id == task_id,
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def remove_tag(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> bool:

        result = await db.execute(
            delete(TaskTag).where(
                TaskTag.workspace_id == workspace_id,
                TaskTag.task_id == task_id,
                TaskTag.tag_id == tag_id,
            )
        )

        await db.flush()

        return result.rowcount > 0