
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.tasks.models import Task


class TaskRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        task_data: dict,
    ) -> Task:
        task = Task(**task_data)

        db.add(task)

        await db.flush()

        return task

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Task | None:

        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_workspace_tasks(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[Task]:

        result = await db.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        task: Task,
        update_data: dict,
    ) -> Task:

        for field, value in update_data.items():
            setattr(task, field, value)

        await db.flush()

        return task
    
    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        task,
    ):
        task.deleted_at = datetime.now(timezone.utc)

        await db.flush()

        return task

    @staticmethod
    async def get_subtasks(
        db: AsyncSession,
        *,
        workspace_id: UUID,
        parent_task_id: UUID,
    ):
        result = await db.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.parent_task_id == parent_task_id,
                Task.deleted_at.is_(None),
            )
        )

        return result.scalars().all()


    @staticmethod
    async def restore(
        db: AsyncSession,
        task,
    ):
        task.deleted_at = None

        await db.flush()

        return task

    @staticmethod
    async def get_by_id_including_deleted(
        db: AsyncSession,
        *,
        task_id: UUID,
        workspace_id: UUID,
    ):
        result = await db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.workspace_id == workspace_id,
            )
        )

        return result.scalar_one_or_none()