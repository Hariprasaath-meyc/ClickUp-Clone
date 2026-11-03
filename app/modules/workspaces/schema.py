
from uuid import UUID

import strawberry
from strawberry.types import Info
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository

from app.modules.workspaces.repositories.invitation_repository import InvitationRepository
from app.modules.workspaces.repository import WorkspaceRepository

from app.modules.workspaces.security.authorization_service import AuthorizationService
from app.modules.workspaces.security.member_service import MemberService
from app.modules.workspaces.security.role_service import RoleService
from app.modules.workspaces.types import (
    WorkspaceInvitationType,
    WorkspaceMemberType,
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

        # Check workspace.read permission
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

        # Check workspace.read permission
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
    
    @strawberry.field
    async def workspace_members(
        self,
        info: Info,
        workspace_id: strawberry.ID,
    ) -> list[WorkspaceMemberType]:

        db: AsyncSession = info.context["db"]

        # 1. Authenticate the user.
        claims = require_authenticated_user(info)

        # 2. Retrieve the local PostgreSQL user.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

        # 3. Check members.read permission.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=UUID(str(workspace_id)),
                permission_key="members.read",
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # 4. Retrieve workspace members.
        members = await MemberService.get_workspace_members(
            db=db,
            workspace_id=UUID(str(workspace_id)),
        )

        # 5. Convert ORM results into GraphQL response types.
        return [
    WorkspaceMemberType(
        user_id=strawberry.ID(str(user.id)),
        display_name=profile.display_name,
        email=user.email,
        role=role.name,
        joined_at=membership.joined_at,
    )
    for user, profile, role, membership in members
]

    @strawberry.field
    async def workspace_invitations(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
    ) -> list[WorkspaceInvitationType]:

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

        # Step 3: Validate workspace UUID.
        try:
            parsed_workspace_id = UUID(str(workspace_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        # Step 4: Check authorization.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=parsed_workspace_id,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Step 5: Retrieve invitations.
        try:
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
                            if invitation.accepted_by else None
                        ),
                        expires_at=invitation.expires_at,
                        created_at=invitation.created_at,
                        accepted_at=invitation.accepted_at,
                    )
                )

            return results

        except Exception:
            raise