
import strawberry

from uuid import UUID

from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository

from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.types import (
    WorkspaceType,
    SlugAvailabilityType,
)


@strawberry.type
class WorkspaceQuery:

    # Get all workspaces belonging to the authenticated user
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
            raise GraphQLError(
                "User not found. Please log in again."
            )

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
                deleted_at=workspace.deleted_at,
            )
            for workspace in workspaces
        ]

    # Get workspace using its ID
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
            raise GraphQLError(
                "User not found. Please log in again."
            )

        try:
            workspace_id = UUID(str(id))
        except ValueError as exc:
            raise GraphQLError(
                "Invalid workspace ID."
            ) from exc

        workspace = await WorkspaceRepository.get_by_id(
            db=db,
            workspace_id=workspace_id,
        )

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace.id,
                permission_key="workspace.read",
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            deleted_at=workspace.deleted_at,
        )

    # Check whether a workspace slug is available
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

    # Get workspace using its slug
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

        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace.id,
                permission_key="workspace.read",
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
