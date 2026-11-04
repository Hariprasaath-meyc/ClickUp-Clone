
import strawberry

from uuid import UUID

from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository

from app.modules.workspaces.repositories.invitation_repository import (
    InvitationRepository,
)
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.security.role_service import RoleService
from app.modules.workspaces.types import WorkspaceInvitationType


@strawberry.type
class InvitationQuery:

    # Get all invitations belonging to a workspace
    @strawberry.field
    async def workspace_invitations(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
    ) -> list[WorkspaceInvitationType]:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        try:
            parsed_workspace_id = UUID(str(workspace_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=parsed_workspace_id,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        invitations = await InvitationRepository.get_workspace_invitations(
            db=db,
            workspace_id=parsed_workspace_id,
        )

        results = []

        for invitation in invitations:

            role = await RoleService.get_role_by_id(
                db=db,
                workspace_id=parsed_workspace_id,
                role_id=invitation.role_id,
            )

            results.append(
                WorkspaceInvitationType(
                    id=strawberry.ID(str(invitation.id)),
                    email=invitation.email,
                    role_key=role.role_key,
                    status=invitation.status.value,
                    invited_by=strawberry.ID(str(invitation.invited_by)),
                    accepted_by=(
                        strawberry.ID(str(invitation.accepted_by))
                        if invitation.accepted_by
                        else None
                    ),
                    expires_at=invitation.expires_at,
                    created_at=invitation.created_at,
                    accepted_at=invitation.accepted_at,
                )
            )

        return results

    # Get only pending invitations belonging to a workspace
    @strawberry.field
    async def pending_invitations(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
    ) -> list[WorkspaceInvitationType]:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        try:
            workspace_uuid = UUID(str(workspace_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=workspace_uuid,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        invitations = await InvitationRepository.get_pending_invitations(
            db=db,
            workspace_id=workspace_uuid,
        )

        results = []

        for invitation in invitations:

            role = await RoleService.get_role_by_id(
                db=db,
                workspace_id=workspace_uuid,
                role_id=invitation.role_id,
            )

            results.append(
                WorkspaceInvitationType(
                    id=strawberry.ID(str(invitation.id)),
                    email=invitation.email,
                    role_key=role.role_key,
                    status=invitation.status.value,
                    invited_by=strawberry.ID(str(invitation.invited_by)),
                    accepted_by=(
                        strawberry.ID(str(invitation.accepted_by))
                        if invitation.accepted_by
                        else None
                    ),
                    expires_at=invitation.expires_at,
                    created_at=invitation.created_at,
                    accepted_at=invitation.accepted_at,
                )
            )

        return results
