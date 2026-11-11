
import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas.workspace import (
    WorkspaceIdQueryPayload,
    WorkspaceSlugQueryPayload,
)
from app.modules.workspaces.service import (
    get_workspace,
    get_workspace_by_slug,
)
from app.modules.workspaces.types import (
    SlugAvailabilityType,
    WorkspaceType,
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

        # 1. Authenticate user
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # 2. Validate payload
        try:
            payload = WorkspaceIdQueryPayload(id=str(id))
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 3. Resolve local user from PostgreSQL
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        # 4. Call decorated service method
        try:
            workspace = await get_workspace(
                db=db,
                workspace_id=payload.id,
                user_id=user.id,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        # 5. Construct response
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

        try:
            payload = WorkspaceSlugQueryPayload(slug=slug)
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        is_taken = await WorkspaceRepository.is_slug_taken(
            db=db,
            slug=payload.slug,
        )

        return SlugAvailabilityType(
            slug=payload.slug,
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

        # 1. Validate payload
        try:
            payload = WorkspaceSlugQueryPayload(slug=slug)
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 2. Resolve local user
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        # 3. Call decorated service method
        try:
            workspace = await get_workspace_by_slug(
                db=db,
                slug=payload.slug,
                user_id=user.id,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

        # 4. Construct response
        return WorkspaceType(
            id=strawberry.ID(str(workspace.id)),
            name=workspace.name,
            slug=workspace.slug,
            created_by=strawberry.ID(str(workspace.created_by)),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            deleted_at=workspace.deleted_at,
        )
