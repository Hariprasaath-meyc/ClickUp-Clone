from uuid import UUID

import strawberry
from graphql import GraphQLError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.auth.service import AuthService
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)
from app.modules.workspaces.services.invitation_service import (
    InvitationService,
)
from app.modules.workspaces.types import (
    AcceptInvitationInput,
    CreateInvitationInput,
    CreateInvitationResult,
    DeclineInvitationInput,
    InvitationResult,
    ResendInvitationInput,
    RevokeInvitationInput,
)


@strawberry.type
class InvitationMutation:
    # Create invitation
    @strawberry.mutation
    async def invite_member(
        self,
        info: strawberry.Info,
        input: CreateInvitationInput,
    ) -> CreateInvitationResult:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found. Please log in again.")

        try:
            workspace_id = UUID(str(input.workspace_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace ID.") from exc

        email = input.email.strip()

        if not email:
            raise GraphQLError("Email address is required.")


        try:
            invitation, raw_token = await InvitationService.create_invitation(
                db=db,
                workspace_id=workspace_id,
                email=email,
                role_key=input.role_key,
                user_id=user.id,
            )

            await db.commit()
            await db.refresh(invitation)

            return CreateInvitationResult(
                id=strawberry.ID(str(invitation.id)),
                email=invitation.email,
                status=invitation.status.value,
                expires_at=invitation.expires_at,
                token=raw_token,
            )

        except IntegrityError as exc:
            await db.rollback()
            raise GraphQLError("Unable to create invitation.") from exc

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception:
            await db.rollback()
            raise

    # Accept invitation
    @strawberry.mutation
    async def accept_invitation(
        self,
        info: strawberry.Info,
        input: AcceptInvitationInput,
    ) -> InvitationResult:

        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]
        access_token = info.context.get("access_token")

        if not access_token:
            raise GraphQLError("Authentication required.")

        try:
            identity = await AuthService.get_authenticated_identity(
                access_token=access_token,
            )

            if identity["cognito_sub"] != claims["sub"]:
                raise GraphQLError("Invalid authentication identity.")

            user = await UserRepository.get_by_cognito_sub(
                db,
                identity["cognito_sub"],
            )

            if user is None:
                raise GraphQLError("User not found.")

            invitation = await InvitationService.accept_invitation(
                db=db,
                raw_token=input.token,
                user_id=user.id,
                verified_email=identity["email"],
            )

            await db.commit()
            await db.refresh(invitation)

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

    # Revoke invitation
    @strawberry.mutation
    async def revoke_invitation(
        self,
        info: strawberry.Info,
        input: RevokeInvitationInput,
    ) -> InvitationResult:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        user = await UserRepository.get_by_cognito_sub(
            db,
            claims["sub"],
        )

        if user is None:
            raise GraphQLError("User not found.")

        try:
            workspace_id = UUID(str(input.workspace_id))
            invitation_id = UUID(str(input.invitation_id))
        except ValueError as exc:
            raise GraphQLError("Invalid workspace or invitation ID.") from exc

        

        invitation = await InvitationService.revoke_invitation(
        db=db,
        invitation_id=invitation_id,
        workspace_id=workspace_id,
        user_id=user.id,
    )
        

        await db.commit()
        await db.refresh(invitation)

        return InvitationResult(
            id=strawberry.ID(str(invitation.id)),
            email=invitation.email,
            status=invitation.status.value,
            expires_at=invitation.expires_at,
        )

        

    # Decline invitation
    @strawberry.mutation
    async def decline_invitation(
        self,
        info: strawberry.Info,
        input: DeclineInvitationInput,
    ) -> InvitationResult:

        claims = require_authenticated_user(info)

        db: AsyncSession = info.context["db"]
        access_token = info.context.get("access_token")

        if not access_token:
            raise GraphQLError("Authentication required.")

        try:
            identity = await AuthService.get_authenticated_identity(
                access_token=access_token,
            )

            if identity["cognito_sub"] != claims["sub"]:
                raise GraphQLError("Invalid authentication identity.")

            try:
                invitation_id = UUID(str(input.invitation_id))
            except ValueError as exc:
                raise GraphQLError("Invalid invitation ID.") from exc

            invitation = await InvitationService.decline_invitation(
                db=db,
                invitation_id=invitation_id,
                verified_email=identity["email"],
            )

            await db.commit()
            await db.refresh(invitation)

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

    # Resend invitation
    @strawberry.mutation
    async def resend_invitation(
        self,
        info: strawberry.Info,
        input: ResendInvitationInput,
    ) -> CreateInvitationResult:

        claims = require_authenticated_user(info)
        db: AsyncSession = info.context["db"]

        try:
            user = await UserRepository.get_by_cognito_sub(
                session=db,
                cognito_sub=claims["sub"],
            )

            if user is None:
                raise ValueError("User not found.")

            try:
                workspace_id = UUID(str(input.workspace_id))
                invitation_id = UUID(str(input.invitation_id))
            except ValueError as exc:
                raise ValueError("Invalid workspace or invitation ID.") from exc

           

            invitation, raw_token = await InvitationService.resend_invitation(
                db=db,
                invitation_id=invitation_id,
                workspace_id=workspace_id,
                user_id=user.id,
            )

            await db.commit()
            await db.refresh(invitation)

            return CreateInvitationResult(
                id=strawberry.ID(str(invitation.id)),
                email=invitation.email,
                status=invitation.status.value,
                expires_at=invitation.expires_at,
                token=raw_token,
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
