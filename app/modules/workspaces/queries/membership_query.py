import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository
from app.modules.workspaces.schemas.membership import (
    WorkspaceMemberQueryPayload,
    WorkspaceMembersQueryPayload,
)
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

        # 1. Validate payload
        try:
            payload = WorkspaceMembersQueryPayload(
                workspace_id=str(workspace_id),
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 2. Resolve local user
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

        # 3. Check authorization
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=payload.workspace_id,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # 4. Retrieve workspace members
        members = await MemberService.get_workspace_members(
            db=db,
            workspace_id=payload.workspace_id,
        )

        # 5. Construct GraphQL response
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

        # 1. Validate payload
        try:
            payload = WorkspaceMemberQueryPayload(
                workspace_id=str(workspace_id),
                user_id=str(user_id),
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc

        # 2. Resolve local user
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

        # 3. Check authorization
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=user.id,
                workspace_id=payload.workspace_id,
                permission_key=Permission.MEMBERS_READ,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # 4. Retrieve specific member
        member = await MemberService.get_workspace_member(
            db=db,
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
        )

        if member is None:
            return None

        # 5. Construct GraphQL response
        member_user, profile, role, membership = member

        return WorkspaceMemberType(
            user_id=strawberry.ID(str(member_user.id)),
            display_name=profile.display_name,
            email=member_user.email,
            role=role.name,
            joined_at=membership.joined_at,
        )
