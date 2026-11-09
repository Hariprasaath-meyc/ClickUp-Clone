import uuid
from datetime import datetime

import strawberry


@strawberry.type
class TaskHistoryType:
    id: uuid.UUID
    workspace_id: uuid.UUID
    task_id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    changes: strawberry.scalars.JSON | None
    created_at: datetime
