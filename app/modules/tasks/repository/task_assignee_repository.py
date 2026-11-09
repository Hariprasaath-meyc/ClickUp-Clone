import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import Task, TaskAssignee


class TaskAssigneeRepository:
    @staticmethod
    async def assign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        assigned_by: uuid.UUID,
    ) -> list[TaskAssignee]:

        assignments = [
            TaskAssignee(
                workspace_id=workspace_id,
                task_id=task_id,
                user_id=user_id,
                assigned_by=assigned_by,
            )
            for user_id in user_ids
        ]

        db.add_all(assignments)

        await db.flush()

        return assignments

    @staticmethod
    async def get_task_assignees(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> list[TaskAssignee]:

        result = await db.execute(
            select(TaskAssignee).where(
                TaskAssignee.workspace_id == workspace_id,
                TaskAssignee.task_id == task_id,
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def unassign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
    ) -> int:

        result = await db.execute(
            delete(TaskAssignee).where(
                TaskAssignee.workspace_id == workspace_id,
                TaskAssignee.task_id == task_id,
                TaskAssignee.user_id.in_(user_ids),
            )
        )

        await db.flush()

        return result.rowcount or 0

    @staticmethod
    async def get_user_assigned_tasks(
        db: AsyncSession,
        user_id: uuid.UUID,
    ):
        result = await db.execute(
            select(Task)
            .join(
                TaskAssignee,
                (TaskAssignee.workspace_id == Task.workspace_id)
                & (TaskAssignee.task_id == Task.id),
            )
            .where(
                TaskAssignee.user_id == user_id,
                Task.deleted_at.is_(None),
            )
            .order_by(TaskAssignee.assigned_at.desc())
        )

        return result.scalars().all()
