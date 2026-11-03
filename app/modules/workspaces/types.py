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

@strawberry.input
class CreateWorkspaceInput:
    name: str
    slug: str


@strawberry.type
class WorkspaceResult:
    id: strawberry.ID
    name: str
    slug: str
    created_by: strawberry.ID
    created_at: datetime

@strawberry.type
class WorkspaceMemberType:
    user_id: strawberry.ID
    display_name: str
    email: str
    role: str
    joined_at: datetime

@strawberry.input
class CreateInvitationInput:
    workspace_id: strawberry.ID
    email: str
    role_key: str

@strawberry.type
class InvitationResult:
    id: strawberry.ID
    email: str
    status: str
    expires_at: datetime
   

@strawberry.input
class AcceptInvitationInput:
    token: str

@strawberry.type
class CreateInvitationResult:
    id: strawberry.ID
    email: str
    status: str
    expires_at: datetime
    token: str

@strawberry.type
class WorkspaceInvitationType:
    id: strawberry.ID
    email: str
    role_key: str
    status: str
    invited_by: strawberry.ID
    accepted_by: strawberry.ID | None
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None

@strawberry.input
class RevokeInvitationInput:
    workspace_id: strawberry.ID
    invitation_id: strawberry.ID