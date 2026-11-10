import strawberry
from graphql import GraphQLError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.users.repository import UserRepository
from app.modules.workspaces.schemas.membership import (
    ChangeMemberRolePayload,
    RemoveMemberPayload,
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

        # Step 2: Validate incoming payload using Pydantic.
        try:
            payload = ChangeMemberRolePayload(
                workspace_id=str(workspace_id),
                user_id=str(user_id),
                role_key=role_key,
            )
        except ValidationError as exc:
            raise GraphQLError(
                "Invalid input payload.",
                extensions={
                    "code": "VALIDATION_ERROR",
                    "details": exc.errors(include_input=False),
                },
            ) from exc

        # Step 3: Retrieve the local authenticated user.
        current_user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if current_user is None:
            raise GraphQLError("User not found.")

        # Step 4: Change member role.
        try:
            await MemberService.change_member_role(
                db=db,
                workspace_id=payload.workspace_id,
                user_id=current_user.id,
                target_user_id=payload.user_id,
                role_key=payload.role_key,
            )

            await db.commit()

            return True

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

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

        # Step 1: Authenticate the current user.
        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        # Step 2: Validate incoming payload using Pydantic.
        try:
            payload = RemoveMemberPayload(
                workspace_id=str(workspace_id),
                user_id=str(user_id),
            )
        except ValidationError as exc:
            raise GraphQLError(
                "Invalid input payload.",
                extensions={
                    "code": "VALIDATION_ERROR",
                    "details": exc.errors(include_input=False),
                },
            ) from exc

        # Step 3: Retrieve the local authenticated user.
        current_user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if current_user is None:
            raise GraphQLError("User not found.")

        # Step 4: Remove workspace member.
        try:
            await MemberService.remove_member_from_workspace(
                db=db,
                workspace_id=payload.workspace_id,
                user_id=current_user.id,
                target_user_id=payload.user_id,
            )

            await db.commit()

            return True

        except PermissionError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

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
