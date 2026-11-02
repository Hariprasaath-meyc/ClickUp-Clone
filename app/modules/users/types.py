from datetime import datetime

import strawberry


@strawberry.type
class UserProfileResult:
    display_name: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class MeResult:
    id: strawberry.ID
    email: str
    profile: UserProfileResult


@strawberry.input
class UpdateMyProfileInput:
    display_name: str | None = None
    avatar_url: str | None = None