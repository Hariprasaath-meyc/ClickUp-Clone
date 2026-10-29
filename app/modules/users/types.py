import strawberry
from datetime import datetime


@strawberry.type
class UserProfileResult:
    display_name: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.input
class UpdateMyProfileInput:
    display_name: str | None = None
    avatar_url: str | None = None