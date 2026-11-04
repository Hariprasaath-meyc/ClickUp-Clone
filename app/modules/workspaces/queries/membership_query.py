
import strawberry

from uuid import UUID

from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository

from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.security.member_service import MemberService
from app.modules.workspaces.types import WorkspaceMemberType


@strawberry.type
class MembershipQuery:

    # Get all members belonging to a workspace
    @strawberry.field
    async def workspace_members(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
    ) -> list[WorkspaceMemberType]:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

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

        members = await MemberService.get_workspace_members(
            db=db,
            workspace_id=parsed_workspace_id,
        )

        return [
            WorkspaceMemberType(
                user_id=strawberry.ID(str(member_user.id)),
                display_name=profile.display_name,
                email=member_user.email,
                role=role.name,
                joined_at=membership.joined_at,
            )
            for member_user, profile, role, membership in members
        ]

    # Get a specific member using user ID
    @strawberry.field
    async def workspace_member(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
        user_id: strawberry.ID,
    ) -> WorkspaceMemberType | None:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

        try:
            parsed_workspace_id = UUID(str(workspace_id))
            parsed_user_id = UUID(str(user_id))
        except ValueError as exc:
            raise GraphQLError(
                "Invalid workspace ID or user ID."
            ) from exc

        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=parsed_workspace_id,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        member = await MemberService.get_workspace_member(
            db=db,
            workspace_id=parsed_workspace_id,
            user_id=parsed_user_id,
        )

        if member is None:
            return None

        member_user, profile, role, membership = member

        return WorkspaceMemberType(
            user_id=strawberry.ID(str(member_user.id)),
            display_name=profile.display_name,
            email=member_user.email,
            role=role.name,
            joined_at=membership.joined_at,
        )
