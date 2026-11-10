from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class CreateWorkspacePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    slug: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.lower()


class UpdateWorkspacePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: UUID

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is not None:
            return value.lower()
        return value

    @model_validator(mode="after")
    def validate_update_fields(self):
        if self.name is None and self.slug is None:
            raise ValueError("Provide at least one field to update.")

        return self


class DeleteWorkspacePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    workspace_id: UUID


class WorkspaceIdQueryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID


class WorkspaceSlugQueryPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    slug: str = Field(min_length=1, max_length=100)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.lower()
