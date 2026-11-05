
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums import TaskPriority, TaskStatus
from app.modules.tasks.repository import TaskRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.tasks.services.task_history_service import TaskHistoryService
from app.modules.tasks.enums import TaskHistoryAction

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
        task = await TaskRepository.create(
        db=db,
        task_data=task_data,
    )

        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task.id,
            actor_id=user_id,
            action=TaskHistoryAction.TASK_CREATED,
            changes={
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "due_date": (
                    task.due_date.isoformat()
                    if task.due_date
                    else None
                ),
                "parent_task_id": (
                    str(task.parent_task_id)
                    if task.parent_task_id
                    else None
                ),
            },
        )

        return task

        

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

        
        # 5. Capture existing values before updating
        old_values = {
            field: getattr(task, field)
            for field in update_data
        }

        # 6. Update through repository
        task = await TaskRepository.update(
            db=db,
            task=task,
            update_data=update_data,
        )

        # 7. Compare old and new values
        changes = {}

        for field, old_value in old_values.items():
            new_value = getattr(task, field)

            if old_value != new_value:

                if isinstance(old_value, (TaskStatus, TaskPriority)):
                    old_value = old_value.value
                elif isinstance(old_value, datetime):
                    old_value = old_value.isoformat()

                if isinstance(new_value, (TaskStatus, TaskPriority)):
                    new_value = new_value.value
                elif isinstance(new_value, datetime):
                    new_value = new_value.isoformat()

                changes[field] = {
                    "old": old_value,
                    "new": new_value,
                }

        # 8. Record history only if something actually changed
        if changes:
            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=user_id,
                action=TaskHistoryAction.TASK_UPDATED,
                changes=changes,
            )

        return task

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
