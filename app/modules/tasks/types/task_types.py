
import uuid
from datetime import datetime

import strawberry

from app.modules.tasks.enums import TaskStatus, TaskPriority

from strawberry import UNSET
from strawberry import Maybe


@strawberry.input
class CreateTaskInput:
    workspace_id: uuid.UUID
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None
    parent_task_id: uuid.UUID | None = None


@strawberry.type
class TaskAssigneeType:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    assigned_by: uuid.UUID
    assigned_at: datetime

@strawberry.type
class TaskType:
    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_task_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    created_by: uuid.UUID
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    assignees: list[TaskAssigneeType]


@strawberry.type
class TaskResult:
    success: bool
    message: str
    task: TaskType | None = None


@strawberry.input
class UpdateTaskInput:
    task_id: uuid.UUID
    workspace_id: uuid.UUID

    title: Maybe[str] = None
    description: Maybe[str | None] = None
    status: Maybe[TaskStatus] = None
    priority: Maybe[TaskPriority] = None
    due_date: Maybe[datetime | None] = None


@strawberry.input
class AssignTaskInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    user_ids: list[uuid.UUID]


@strawberry.input
class UnassignTaskInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    user_ids: list[uuid.UUID]


@strawberry.input
class DeleteTaskInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    


@strawberry.type
class TaskAssignmentResult:
    success: bool
    message: str
    assignees: list[TaskAssigneeType]


@strawberry.type
class TaskUnassignmentResult:
    success: bool
    message: str
    removed_count: int

@strawberry.type
class DeleteTaskResult:
    success: bool
    message: str