from datetime import datetime

import strawberry


@strawberry.type
class WorkspaceType:
    id: strawberry.ID
    name: str
    slug: str
    created_by: strawberry.ID
    created_at: datetime
    updated_at: datetime


@strawberry.input
class UpdateWorkspaceInput:
    id: strawberry.ID
    name: str | None = None
    slug: str | None = None


@strawberry.type
class SlugAvailabilityType:
    slug: str
    available: bool