import logging

import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.workspaces.schemas.workspace import (
    CreateWorkspacePayload,
    DeleteWorkspacePayload,
    UpdateWorkspacePayload,
)
from app.modules.workspaces.service import (
    create_workspace,
    delete_workspace,
    update_workspace,
)
from app.modules.workspaces.types import (
    CreateWorkspaceInput,
    DeleteWorkspaceInput,
    UpdateWorkspaceInput,
    WorkspaceResult,
    WorkspaceType,
)

logger = logging.getLogger(__name__)


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

        # 1. Validate payload
        try:
            payload = CreateWorkspacePayload(
                name=input.name,
                slug=input.slug,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 2. Resolve local user
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            # 3. Execute business operation
            workspace = await create_workspace(
                db=db,
                user_id=user.id,
                name=payload.name,
                slug=payload.slug,
            )

            # 4. Commit transaction
            await db.commit()

            # 5. Construct GraphQL response
            return WorkspaceResult(
                success=True,
                message="Workspace created successfully.",
                workspace=WorkspaceType(
                    id=strawberry.ID(str(workspace.id)),
                    name=workspace.name,
                    slug=workspace.slug,
                    created_by=strawberry.ID(str(workspace.created_by)),
                    created_at=workspace.created_at,
                    updated_at=workspace.updated_at,
                    deleted_at=workspace.deleted_at,
                ),
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "The workspace could not be created. The slug may already be in use."
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

        # 1. Authenticate user
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # 2. Validate payload
        try:
            payload = UpdateWorkspacePayload(
                id=str(input.id),
                name=input.name,
                slug=input.slug,
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 3. Resolve local user
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            # 4. Execute decorated service method
            workspace = await update_workspace(
                db=db,
                workspace_id=payload.id,
                user_id=user.id,
                name=payload.name,
                slug=payload.slug,
            )

            # 5. Commit transaction
            await db.commit()
            await db.refresh(workspace)

            # 6. Construct response
            return WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                deleted_at=workspace.deleted_at,
            )

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(
                str(exc),
                extensions={"code": "FORBIDDEN"},
            ) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to update workspace. The slug may already be in use."
            ) from exc

        except Exception:
            await db.rollback()
            raise

    # Delete workspace
    @strawberry.mutation
    async def delete_workspace(
        self,
        info: Info,
        input: DeleteWorkspaceInput,
    ) -> WorkspaceResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate user
            claims = require_authenticated_user(info)

            # 2. Validate payload
            payload = DeleteWorkspacePayload(
                workspace_id=str(input.workspace_id),
            )

            # 3. Resolve local user
            user = await UserRepository.get_by_cognito_sub(
                session=db,
                cognito_sub=claims["sub"],
            )

            if user is None:
                raise ValueError("User not found.")

            # 4. Execute business operation
            workspace = await delete_workspace(
                db=db,
                workspace_id=payload.workspace_id,
                user_id=user.id,
            )

            # 5. Construct response before commit
            workspace_type = WorkspaceType(
                id=strawberry.ID(str(workspace.id)),
                name=workspace.name,
                slug=workspace.slug,
                created_by=strawberry.ID(str(workspace.created_by)),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                deleted_at=workspace.deleted_at,
            )

            # 6. Commit transaction
            await db.commit()

            return WorkspaceResult(
                success=True,
                message="Workspace deleted successfully.",
                workspace=workspace_type,
            )

        except ValidationError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            return WorkspaceResult(
                success=False,
                message=str(exc),
                workspace=None,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError("Unable to delete workspace.") from exc

        except Exception as exc:
            await db.rollback()
            logger.exception("Workspace deletion failed.")
            raise GraphQLError("Unable to delete workspace.") from exc
