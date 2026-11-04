
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums import TaskPriority, TaskStatus
from app.modules.tasks.repository import TaskRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)


class TaskService:

    @staticmethod
    async def create_task(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: datetime | None = None,
        parent_task_id: uuid.UUID | None = None,
    ):

        # 1. Check whether the user has permission to create tasks.
        await AuthorizationService.require_permission(
            db,
            user_id,
            workspace_id,
            Permission.TASKS_CREATE.value,
        )

        # 2. Validate the parent task if creating a subtask.
        if parent_task_id is not None:

            parent_task = await TaskRepository.get_by_id(
                db,
                parent_task_id,
                workspace_id,
            )

            if parent_task is None:
                raise ValueError(
                    "Parent task not found in this workspace."
                )

            # 3. Enforce the one-level subtask restriction.
            if parent_task.parent_task_id is not None:
                raise ValueError(
                    "A subtask cannot have another subtask."
                )

        # 4. Prepare trusted task data.
        task_data = {
            "workspace_id": workspace_id,
            "parent_task_id": parent_task_id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "created_by": user_id,
            "due_date": due_date,
        }

        # 5. Create the task through the repository.
        return await TaskRepository.create(
            db,
            task_data,
        )

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: dict,
    ):

        # 1. Check permission
        await AuthorizationService.require_permission(
            db,
            user_id,
            workspace_id,
            Permission.TASKS_UPDATE.value,
        )

        # 2. Retrieve the existing task
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 3. Allow only editable fields
        allowed_fields = {
            "title",
            "description",
            "status",
            "priority",
            "due_date",
        }

        update_data = {
            key: value
            for key, value in update_data.items()
            if key in allowed_fields
        }

        if not update_data:
            raise ValueError("No valid fields provided for update.")

        # 4. Validate title
        if "title" in update_data:
            if not update_data["title"] or not update_data["title"].strip():
                raise ValueError("Task title cannot be empty.")

            update_data["title"] = update_data["title"].strip()

        # 5. Update through repository
        return await TaskRepository.update(
            db,
            task,
            update_data,
        )

    @staticmethod
    async def get_workspace_tasks(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):

        # 1. Check read permission
        await AuthorizationService.require_permission(
            db,
            user_id,
            workspace_id,
            Permission.TASKS_READ.value,
        )

        # 2. Retrieve workspace tasks
        return await TaskRepository.get_workspace_tasks(
            db,
            workspace_id,
        )

    @staticmethod
    async def get_task_by_id(
        db: AsyncSession,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):

        # 1. Check read permission
        await AuthorizationService.require_permission(
            db,
            user_id,
            workspace_id,
            Permission.TASKS_READ.value,
        )

        # 2. Retrieve task
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        return task
