
import strawberry

from uuid import UUID

from graphql import GraphQLError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository

from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.service import create_workspace

from app.modules.workspaces.types import (
    CreateWorkspaceInput,
    UpdateWorkspaceInput,
    WorkspaceResult,
    WorkspaceType,
)


@strawberry.type
class WorkspaceMutation:

    # Create workspace
    @strawberry.mutation
    async def create_workspace(
        self,
        info: strawberry.Info,
        input: CreateWorkspaceInput,
    ) -> WorkspaceResult:

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

        name = input.name.strip()
        slug = input.slug.strip().lower()

        if not name or len(name) > 100:
            raise GraphQLError(
                "Workspace name must be between 1 and 100 characters."
            )

        if not slug or len(slug) > 100:
            raise GraphQLError(
                "Workspace slug must be between 1 and 100 characters."
            )

        try:
            workspace = await create_workspace(
                db=db,
                user_id=user.id,
                name=name,
                slug=slug,
            )

            await db.commit()

            return WorkspaceResult(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "The workspace could not be created. "
                "The slug may already be in use."
            ) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise

    # Update workspace
    @strawberry.mutation
    async def update_workspace(
        self,
        info: strawberry.Info,
        input: UpdateWorkspaceInput,
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

        # Validate workspace ID
        try:
            workspace_id = UUID(str(input.id))
        except ValueError as exc:
            raise GraphQLError(
                "Invalid workspace ID."
            ) from exc

        # Retrieve workspace
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id
            )
        )

        workspace = result.scalar_one_or_none()

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        # Check authorization
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace.id,
                permission_key="workspace.update",
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Validate update fields
        name = (
            input.name.strip()
            if input.name is not None
            else None
        )

        slug = (
            input.slug.strip().lower()
            if input.slug is not None
            else None
        )

        if name is not None and not 1 <= len(name) <= 100:
            raise GraphQLError(
                "Workspace name must be between 1 and 100 characters."
            )

        if slug is not None and not 1 <= len(slug) <= 100:
            raise GraphQLError(
                "Slug must be between 1 and 100 characters."
            )

        if name is None and slug is None:
            raise GraphQLError(
                "Provide at least one field to update."
            )

        # Update workspace
        try:
            workspace = await WorkspaceRepository.update(
                db,
                workspace,
                name=name,
                slug=slug,
            )

            await db.commit()
            await db.refresh(workspace)

            return WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to update workspace. "
                "The slug may already be in use."
            ) from exc

        except Exception:
            await db.rollback()
            raise
