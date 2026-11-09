from uuid import UUID

import strawberry
from graphql import GraphQLError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.security.member_service import MemberService


@strawberry.type
class MembershipMutation:
    @strawberry.mutation
    async def change_member_role(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
        user_id: strawberry.ID,
        role_key: str,
    ) -> bool:

        # Step 1: Authenticate the current user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Retrieve the local user.
        current_user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if current_user is None:
            raise GraphQLError("User not found.")

        # Step 3: Validate UUIDs.
        try:
            workspace_uuid = UUID(str(workspace_id))
            member_uuid = UUID(str(user_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace or user ID.") from exc

        # Step 4: Check permission.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=current_user.id,
                workspace_id=workspace_uuid,
                permission_key=Permission.MEMBERS_UPDATE_ROLE,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Step 5: Change the member's role.
        try:
            await MemberService.change_member_role(
                db=db,
                workspace_id=workspace_uuid,
                user_id=member_uuid,
                role_key=role_key,
            )

            await db.commit()

            return True

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError("Unable to update member role.") from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "An unexpected error occurred while updating member role."
            ) from exc

    @strawberry.mutation
    async def remove_member_from_workspace(
        self,
        info: strawberry.Info,
        workspace_id: strawberry.ID,
        user_id: strawberry.ID,
    ) -> bool:

        # Step 1: Authenticate current user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Retrieve local user.
        current_user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if current_user is None:
            raise GraphQLError("User not found.")

        # Step 3: Validate UUIDs.
        try:
            workspace_uuid = UUID(str(workspace_id))
            member_uuid = UUID(str(user_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace or user ID.") from exc

        # Step 4: Check permission.
        try:
            await AuthorizationService.require_permission(
                db=db,
                user_id=current_user.id,
                workspace_id=workspace_uuid,
                permission_key=Permission.MEMBERS_REMOVE,
            )
        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        # Step 5: Remove member.
        try:
            await MemberService.remove_member_from_workspace(
                db=db,
                workspace_id=workspace_uuid,
                user_id=member_uuid,
            )

            await db.commit()

            return True

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError("Unable to remove workspace member.") from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "An unexpected error occurred while removing the member."
            ) from exc
