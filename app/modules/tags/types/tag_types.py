import uuid
import strawberry

from datetime import datetime


@strawberry.input
class AssignTagsInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    tag_names: list[str]


@strawberry.input
class RemoveTagsInput:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    tag_ids: list[uuid.UUID]


@strawberry.type
class TagType:
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    created_by: uuid.UUID
    created_at: datetime


@strawberry.type
class TaskTagType:
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    tag_id: uuid.UUID
    assigned_by: uuid.UUID
    assigned_at: datetime
    tag: TagType


@strawberry.type
class TagResult:
    success: bool
    message: str
    tags: list[TagType]


@strawberry.type
class RemoveTagsResult:
    success: bool
    message: str
    removed_count: int