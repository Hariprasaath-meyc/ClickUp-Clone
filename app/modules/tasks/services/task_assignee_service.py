
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.tasks.repository import (
    TaskRepository,
    TaskAssigneeRepository,
)
from app.modules.workspaces.models import WorkspaceMember
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)


class TaskAssigneeService:

    @staticmethod
    async def assign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        assigned_by: uuid.UUID,
    ):

        # 1. Check assignment permission
        await AuthorizationService.require_permission(
            db,
            assigned_by,
            workspace_id,
            Permission.TASKS_ASSIGN.value,
        )

        # 2. Validate task existence
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 3. Validate input
        if not user_ids:
            raise ValueError("At least one assignee is required.")

        # Remove duplicate IDs from the request
        user_ids = list(dict.fromkeys(user_ids))

        # 4. Verify that all users are workspace members
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

        # 5. Retrieve existing assignments
        existing_assignments = (
            await TaskAssigneeRepository.get_task_assignees(
                db,
                workspace_id,
                task_id,
            )
        )

        existing_user_ids = {
            assignment.user_id
            for assignment in existing_assignments
        }

        # 6. Assign only users who are not already assigned
        new_user_ids = [
            user_id
            for user_id in user_ids
            if user_id not in existing_user_ids
        ]

        if new_user_ids:
            await TaskAssigneeRepository.assign_users(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                user_ids=new_user_ids,
                assigned_by=assigned_by,
            )

        # 7. Return all current assignments
        return await TaskAssigneeRepository.get_task_assignees(
            db,
            workspace_id,
            task_id,
        )

    @staticmethod
    async def unassign_users(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        requested_by: uuid.UUID,
    ) -> int:

        # 1. Check assignment permission
        await AuthorizationService.require_permission(
            db,
            requested_by,
            workspace_id,
            Permission.TASKS_ASSIGN.value,
        )

        # 2. Validate task existence
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 3. Validate input
        if not user_ids:
            raise ValueError("At least one user ID is required.")

        user_ids = list(dict.fromkeys(user_ids))

        # 4. Remove selected assignments
        return await TaskAssigneeRepository.unassign_users(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            user_ids=user_ids,
        )
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