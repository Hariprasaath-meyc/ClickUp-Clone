from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChangeMemberRolePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    user_id: UUID
    role_key: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[A-Z]+$",
    )


class RemoveMemberPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    user_id: UUID


class WorkspaceMembersQueryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID


class WorkspaceMemberQueryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    user_id: UUID
