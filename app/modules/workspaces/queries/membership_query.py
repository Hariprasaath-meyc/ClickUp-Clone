import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.workspaces.schemas.membership import (
    WorkspaceMemberQueryPayload,
    WorkspaceMembersQueryPayload,
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

        # Step 1: Authenticate the current user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Validate payload.
        try:
            payload = WorkspaceMembersQueryPayload(
                workspace_id=str(workspace_id),
            )
        except ValidationError as exc:
            raise GraphQLError(
                "Invalid workspace ID.",
                extensions={"code": "VALIDATION_ERROR"},
            ) from exc

        # Step 3: Retrieve authenticated local user.
        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User account not found.")

        # Step 4: Retrieve workspace members.
        try:
            members = await MemberService.get_workspace_members(
                db=db,
                workspace_id=payload.workspace_id,
                user_id=user.id,
            )

            # Step 5: Construct GraphQL response.
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

        except PermissionError as exc:
            raise GraphQLError(
                str(exc),
                extensions={"code": "FORBIDDEN"},
            ) from exc

        except ValueError as exc:
            raise GraphQLError(
                str(exc),
                extensions={"code": "WORKSPACE_UNAVAILABLE"},
            ) from exc

    # Get a specific member using user ID
    @strawberry.field
    async def workspace_member(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
        user_id: strawberry.ID,
    ) -> WorkspaceMemberType | None:

        # Step 1: Authenticate the current user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Validate payload.
        try:
            payload = WorkspaceMemberQueryPayload(
                workspace_id=str(workspace_id),
                user_id=str(user_id),
            )
        except ValidationError as exc:
            raise GraphQLError(
                "Invalid workspace member payload.",
                extensions={"code": "VALIDATION_ERROR"},
            ) from exc

        # Step 3: Retrieve authenticated local user.
        current_user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if current_user is None:
            raise GraphQLError("User account not found.")

        # Step 4: Retrieve specific workspace member.
        try:
            member = await MemberService.get_workspace_member(
                db=db,
                workspace_id=payload.workspace_id,
                user_id=current_user.id,
                target_user_id=payload.user_id,
            )

            if member is None:
                return None

            # Step 5: Construct GraphQL response.
            member_user, profile, role, membership = member

            return WorkspaceMemberType(
                user_id=strawberry.ID(str(member_user.id)),
                display_name=profile.display_name,
                email=member_user.email,
                role=role.name,
                joined_at=membership.joined_at,
            )

        except PermissionError as exc:
            raise GraphQLError(
                str(exc),
                extensions={"code": "FORBIDDEN"},
            ) from exc

        except ValueError as exc:
            raise GraphQLError(
                str(exc),
                extensions={"code": "WORKSPACE_UNAVAILABLE"},
            ) from exc