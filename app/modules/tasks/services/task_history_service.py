import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums.task_history_action import TaskHistoryAction
from app.modules.tasks.repository import (
    TaskHistoryRepository,
    TaskRepository,
)


class TaskHistoryService:
    @staticmethod
    @require_permission(Permission.TASKS_READ)
    async def get_task_history(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ):

        # Verify that the task belongs to this workspace
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # Retrieve activity records
        history = await TaskHistoryRepository.get_task_history(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        return history

    @staticmethod
    async def record_activity(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: TaskHistoryAction,
        changes: dict[str, Any] | None = None,
    ):

        return await TaskHistoryRepository.create(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=actor_id,
            action=action.value,
            changes=changes,
        )
