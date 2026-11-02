from uuid import UUID

import strawberry

from graphql import GraphQLError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.workspaces.models import WorkspaceMember
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.types import (
    WorkspaceType,
    SlugAvailabilityType,
)


@strawberry.type
class WorkspaceQuery:

    @strawberry.field
    async def my_workspaces(
        self,
        info: strawberry.Info,
    ) -> list[WorkspaceType]:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        workspaces = await WorkspaceRepository.get_user_workspaces(
            db=db,
            user_id=user.id,
        )

        return [
            WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )
            for workspace in workspaces
        ]

    @strawberry.field
    async def get_workspace(
        self,
        info: strawberry.Info,
        id: strawberry.ID,
    ) -> WorkspaceType:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            workspace_id = UUID(str(id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        workspace = await WorkspaceRepository.get_by_id(
            db=db,
            workspace_id=workspace_id,
        )

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        membership_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )

        if membership_result.scalar_one_or_none() is None:
            raise GraphQLError(
                "You do not have access to this workspace."
            )

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    @strawberry.field
    async def check_slug_availability(
        self,
        info: strawberry.Info,
        slug: str,
    ) -> SlugAvailabilityType:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        normalized_slug = slug.strip().lower()

        if not normalized_slug or len(normalized_slug) > 100:
            raise GraphQLError(
                "Slug must be between 1 and 100 characters."
            )

        is_taken = await WorkspaceRepository.is_slug_taken(
            db=db,
            slug=normalized_slug,
        )

        return SlugAvailabilityType(
            slug=normalized_slug,
            available=not is_taken,
        )

    @strawberry.field
    async def get_workspace_by_slug(
        self,
        info: strawberry.Info,
        slug: str,
    ) -> WorkspaceType:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        normalized_slug = slug.strip().lower()

        if not normalized_slug or len(normalized_slug) > 100:
            raise GraphQLError(
                "Slug must be between 1 and 100 characters."
            )

        workspace = await WorkspaceRepository.get_by_slug(
            db=db,
            slug=normalized_slug,
        )

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        membership_result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )

        if membership_result.scalar_one_or_none() is None:
            raise GraphQLError(
                "You do not have access to this workspace."
            )

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )