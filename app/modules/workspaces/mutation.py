
import strawberry

from uuid import UUID

from graphql import GraphQLError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.modules.auth.authorization import require_authenticated_user
from app.modules.auth.service import AuthService
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository

from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.security.authorization_service import AuthorizationService
from app.modules.workspaces.service import create_workspace


from app.modules.workspaces.services.invitation_service import InvitationService
from app.modules.workspaces.types import (
    AcceptInvitationInput,
    CreateInvitationInput,
    CreateInvitationResult,
    CreateWorkspaceInput,
    InvitationResult,
    RevokeInvitationInput,
    UpdateWorkspaceInput,
    WorkspaceType,
    WorkspaceResult,
)


@strawberry.type
class WorkspaceMutation:

    # Create Workspace Mutation
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

    # Update Workspace Mutation
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

        # Validate workspace ID.
        try:
            workspace_id = UUID(str(input.id))

        except ValueError as exc:
            raise GraphQLError(
                "Invalid workspace ID."
            ) from exc

        # Retrieve workspace.
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id
            )
        )

        workspace = result.scalar_one_or_none()

        if workspace is None:
            raise GraphQLError("Workspace not found.")

        # Check workspace.update permission.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace.id,
                permission_key="workspace.update",
            )

        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Validate update fields.
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

        # Update workspace.
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
        
    @strawberry.mutation
    async def invite_member(
        self,
        info: strawberry.Info,
        input: CreateInvitationInput,
    ) -> CreateInvitationResult:

        # Step 1: Authenticate user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Retrieve local user.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError(
                "User not found. Please log in again."
            )

        # Step 3: Validate UUIDs.
        try:
            workspace_id = UUID(str(input.workspace_id))
          
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        # Step 4: Validate email.
        email = input.email.strip()

        if not email:
            raise GraphQLError("Email address is required.")

        # Step 5: Check authorization.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace_id,
                permission_key=Permission.MEMBERS_INVITE,
            )

        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Step 6: Create invitation.
        try:
            invitation, raw_token = (
                await InvitationService.create_invitation(
                    db=db,
                    workspace_id=workspace_id,
                    email=email,
                    role_key=input.role_key,
                    invited_by=user.id,
                )
            )

            # Step 7: Commit transaction.
            await db.commit()
            await db.refresh(invitation)

            # Step 8: Return GraphQL result.
            return CreateInvitationResult(
                id=strawberry.ID(str(invitation.id)),
                email=invitation.email,
                status=invitation.status.value,
                expires_at=invitation.expires_at,
                token=raw_token,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to create invitation."
            ) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise
          
    @strawberry.mutation
    async def accept_invitation(
        self,
        info: strawberry.Info,
        input: AcceptInvitationInput,
    ) -> InvitationResult:

        # Step 1: Authenticate the user.
        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]
        access_token = info.context.get("access_token")

        if not access_token:
            raise GraphQLError("Authentication required.")

        try:
            # Step 2: Retrieve verified Cognito identity.
            identity = await AuthService.get_authenticated_identity(
                access_token=access_token,
            )

            # Step 3: Verify Cognito identity matches authenticated claims.
            if identity["cognito_sub"] != claims["sub"]:
                raise GraphQLError("Invalid authentication identity.")

            # Step 4: Retrieve local database user.
            user = await UserRepository.get_by_cognito_sub(
                db,
                identity["cognito_sub"],
            )

            if user is None:
                raise GraphQLError("User not found.")

            # Step 5: Accept invitation.
            invitation = await InvitationService.accept_invitation(
                db=db,
                raw_token=input.token,
                user_id=user.id,
                verified_email=identity["email"],
            )

            # Step 6: Commit transaction.
            await db.commit()
            await db.refresh(invitation)

            # Step 7: Return result.
            return InvitationResult(
                id=strawberry.ID(str(invitation.id)),
                email=invitation.email,
                status=invitation.status.value,
                expires_at=invitation.expires_at,
            )

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise

    @strawberry.mutation
    async def revoke_invitation(
        self,
        info: strawberry.Info,
        input: RevokeInvitationInput,
    ) -> InvitationResult:

        # Step 1: Authenticate user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Retrieve local user.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        # Step 3: Validate UUIDs.
        try:
            workspace_id = UUID(str(input.workspace_id))
            invitation_id = UUID(str(input.invitation_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace or invitation ID.") from exc

        # Step 4: Check authorization.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace_id,
                permission_key=Permission.MEMBERS_INVITE,
            )

            # Step 5: Revoke invitation.
            invitation = await InvitationService.revoke_invitation(
                db=db,
                invitation_id=invitation_id,
                workspace_id=workspace_id,
            )

            await db.commit()
            await db.refresh(invitation)

            return InvitationResult(
                id=strawberry.ID(str(invitation.id)),
                email=invitation.email,
                status=invitation.status.value,
                expires_at=invitation.expires_at,
            )

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise