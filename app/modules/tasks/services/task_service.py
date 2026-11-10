import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.tasks.enums import TaskHistoryAction, TaskPriority, TaskStatus
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.services.task_history_service import TaskHistoryService


class TaskService:
    @staticmethod
    @require_permission(Permission.TASKS_CREATE)
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
        # 1. Validate the parent task if creating a subtask.
        if parent_task_id is not None:
            parent_task = await TaskRepository.get_by_id(
                db,
                parent_task_id,
                workspace_id,
            )

            if parent_task is None:
                raise ValueError("Parent task not found in this workspace.")

            # 2. Enforce the one-level subtask restriction.
            if parent_task.parent_task_id is not None:
                raise ValueError("A subtask cannot have another subtask.")

        # 3. Prepare trusted task data.
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

        # 4. Create the task through the repository.
        task = await TaskRepository.create(
            db=db,
            task_data=task_data,
        )

        # 5. Record task creation history.
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
                "due_date": (task.due_date.isoformat() if task.due_date else None),
                "parent_task_id": (
                    str(task.parent_task_id) if task.parent_task_id else None
                ),
            },
        )

        return task

    @staticmethod
    @require_permission(Permission.TASKS_UPDATE)
    async def update_task(
        db: AsyncSession,
        *,
        task_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        update_data: dict,
    ):
        # 1. Retrieve the existing task.
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Allow only editable fields.
        allowed_fields = {
            "title",
            "description",
            "status",
            "priority",
            "due_date",
        }

        update_data = {
            key: value for key, value in update_data.items() if key in allowed_fields
        }

        if not update_data:
            raise ValueError("No valid fields provided for update.")

        # 3. Validate title.
        if "title" in update_data:
            if not update_data["title"] or not update_data["title"].strip():
                raise ValueError("Task title cannot be empty.")

            update_data["title"] = update_data["title"].strip()

        # 4. Capture existing values before updating.
        old_values = {field: getattr(task, field) for field in update_data}

        # 5. Update through repository.
        task = await TaskRepository.update(
            db=db,
            task=task,
            update_data=update_data,
        )

        # 6. Compare old and new values.
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

        # 7. Record history only if something actually changed.
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
    @require_permission(Permission.TASKS_READ)
    async def get_workspace_tasks(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        return await TaskRepository.get_workspace_tasks(
            db,
            workspace_id,
        )

    @staticmethod
    @require_permission(Permission.TASKS_READ)
    async def get_task_by_id(
        db: AsyncSession,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        task = await TaskRepository.get_by_id(
            db,
            task_id,
            workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        return task

    @staticmethod
    @require_permission(Permission.TASKS_DELETE)
    async def delete_task(
        db: AsyncSession,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        # 1. Retrieve task.
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Capture task details before deletion.
        changes = {
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_by": str(task.created_by),
        }

        # 3. Soft-delete task.
        await TaskRepository.soft_delete(
            db=db,
            task=task,
        )

        # 4. Record deletion activity.
        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
            actor_id=user_id,
            action=TaskHistoryAction.TASK_DELETED,
            changes=changes,
        )

        return True

    @staticmethod
    @require_permission(Permission.TASKS_READ)
    async def get_subtasks(
        db: AsyncSession,
        *,
        workspace_id: UUID,
        parent_task_id: UUID,
        user_id: UUID,
    ):
        # 1. Verify that the parent task exists in this workspace.
        parent_task = await TaskRepository.get_by_id(
            db,
            workspace_id=workspace_id,
            task_id=parent_task_id,
        )

        if parent_task is None:
            raise ValueError("Parent task not found.")

        # 2. Retrieve subtasks.
        return await TaskRepository.get_subtasks(
            db,
            workspace_id=workspace_id,
            parent_task_id=parent_task_id,
        )

    @staticmethod
    @require_permission(Permission.TASKS_UPDATE)
    async def restore_task(
        db: AsyncSession,
        *,
        task_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ):
        # 1. Retrieve the task, including soft-deleted tasks.
        task = await TaskRepository.get_by_id_including_deleted(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        if task.deleted_at is None:
            raise ValueError("Task is already active.")

        # 2. Restore task.
        await TaskRepository.restore(
            db=db,
            task=task,
        )

        # 3. Record restoration history.
        await TaskHistoryService.record_activity(
            db=db,
            workspace_id=workspace_id,
            task_id=task.id,
            actor_id=user_id,
            action=TaskHistoryAction.TASK_RESTORED,
            changes={"deleted_at": None},
        )

        return task
