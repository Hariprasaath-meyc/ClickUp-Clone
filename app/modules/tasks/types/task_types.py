from datetime import datetime
from uuid import UUID

import strawberry
from strawberry import Maybe

from app.modules.tasks.enums import TaskPriority, TaskStatus

# Task Inputs


@strawberry.input
class CreateTaskInput:
    workspace_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None
    parent_task_id: UUID | None = None


@strawberry.input
class UpdateTaskInput:
    task_id: UUID
    workspace_id: UUID
    title: Maybe[str] = None
    description: Maybe[str | None] = None
    status: Maybe[TaskStatus] = None
    priority: Maybe[TaskPriority] = None
    due_date: Maybe[datetime | None] = None


@strawberry.input
class AssignTaskInput:
    workspace_id: UUID
    task_id: UUID
    user_ids: list[UUID]


@strawberry.input
class UnassignTaskInput:
    workspace_id: UUID
    task_id: UUID
    user_ids: list[UUID]


@strawberry.input
class DeleteTaskInput:
    workspace_id: UUID
    task_id: UUID


# Task Output Types


@strawberry.type
class TaskAssigneeType:
    workspace_id: UUID
    task_id: UUID
    user_id: UUID
    assigned_by: UUID
    assigned_at: datetime


@strawberry.type
class TaskType:
    id: UUID
    workspace_id: UUID
    parent_task_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    created_by: UUID
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    assignees: list[TaskAssigneeType]


# Task Results


@strawberry.type
class TaskResult:
    success: bool
    message: str
    task: TaskType | None = None


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


@strawberry.input
class RestoreTaskInput:
    workspace_id: UUID
    task_id: UUID


