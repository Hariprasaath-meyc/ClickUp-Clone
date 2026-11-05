import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import TaskHistory


class TaskHistoryRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: str,
        changes: dict[str, Any] | None = None,
    ) -> TaskHistory:

        history = TaskHistory(
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=actor_id,
            action=action,
            changes=changes,
        )

        db.add(history)
        await db.flush()

        return history

    @staticmethod
    async def get_task_history(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> list[TaskHistory]:

        result = await db.execute(
            select(TaskHistory)
            .where(
                TaskHistory.workspace_id == workspace_id,
                TaskHistory.task_id == task_id,
            )
            .order_by(TaskHistory.created_at.desc())
        )

        return list(result.scalars().all())