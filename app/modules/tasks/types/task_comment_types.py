import uuid
from datetime import datetime

import strawberry


@strawberry.input
class CreateTaskCommentInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    content: str


@strawberry.input
class UpdateTaskCommentInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    comment_id: uuid.UUID
    content: str


@strawberry.input
class DeleteTaskCommentInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    comment_id: uuid.UUID


@strawberry.type
class TaskCommentType:
    id: uuid.UUID
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class TaskCommentResult:
    success: bool
    message: str
    comment: TaskCommentType | None = None


@strawberry.type
class DeleteTaskCommentResult:
    success: bool
    message: str
