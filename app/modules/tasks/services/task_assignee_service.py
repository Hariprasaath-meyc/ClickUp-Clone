import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums import TaskHistoryAction
from app.modules.tasks.repository import (
    TaskAssigneeRepository,
    TaskRepository,
)
from app.modules.tasks.services.task_history_service import TaskHistoryService
from app.modules.workspaces.models import WorkspaceMember


class TaskAssigneeService:

    @staticmethod
    @require_permission(Permission.TASKS_ASSIGN)
    async def assign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ):

        # 1. Validate task existence
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Validate input
        if not user_ids:
            raise ValueError("At least one assignee is required.")

        # Remove duplicate IDs from the request
        user_ids = list(dict.fromkeys(user_ids))

        # 3. Verify that all users are workspace members
        result = await db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id.in_(user_ids),
            )
        )

        member_ids = set(result.scalars().all())
        requested_ids = set(user_ids)

        invalid_ids = requested_ids - member_ids

        if invalid_ids:
            raise ValueError(
                "One or more users are not members of this workspace."
            )

        # 4. Retrieve existing assignments
        existing_assignments = await TaskAssigneeRepository.get_task_assignees(
            db,
            workspace_id,
            task_id,
        )

        existing_user_ids = {
            assignment.user_id for assignment in existing_assignments
        }

        # 5. Assign only users who are not already assigned
        new_user_ids = [
            assignee_id
            for assignee_id in user_ids
            if assignee_id not in existing_user_ids
        ]

        if new_user_ids:
            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=user_id,
                action=TaskHistoryAction.TASK_ASSIGNED,
                changes={
                    "assigned_user_ids": [
                        str(assignee_id) for assignee_id in new_user_ids
                    ]
                },
            )

        # 6. Return all current assignments
        return await TaskAssigneeRepository.get_task_assignees(
            db,
            workspace_id,
            task_id,
        )

    @staticmethod
    @require_permission(Permission.TASKS_ASSIGN)
    async def unassign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:

        # 1. Validate task existence
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Validate input
        if not user_ids:
            raise ValueError("At least one user ID is required.")

        user_ids = list(dict.fromkeys(user_ids))

        # 3. Retrieve existing assignments
        existing_assignments = await TaskAssigneeRepository.get_task_assignees(
            db,
            workspace_id,
            task_id,
        )

        existing_user_ids = {
            assignment.user_id for assignment in existing_assignments
        }

        removed_user_ids = [
            assignee_id
            for assignee_id in user_ids
            if assignee_id in existing_user_ids
        ]

        if not removed_user_ids:
            return 0

        # 4. Remove assignments
        removed_count = await TaskAssigneeRepository.unassign_users(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            user_ids=removed_user_ids,
        )

        # 5. Record audit history
        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=user_id,
            action=TaskHistoryAction.TASK_UNASSIGNED,
            changes={
                "unassigned_user_ids": [
                    str(assignee_id) for assignee_id in removed_user_ids
                ]
            },
        )

        return removed_count

    @staticmethod
    async def get_my_assigned_tasks(
        db: AsyncSession,
        user_id: uuid.UUID,
    ):
        # Find all tasks assigned to this user
        tasks = await TaskAssigneeRepository.get_user_assigned_tasks(
            db=db,
            user_id=user_id,
        )

        return tasks