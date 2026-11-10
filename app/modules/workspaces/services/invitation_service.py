from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.users.repository import UserRepository
from app.modules.workspaces.enums import InvitationStatus
from app.modules.workspaces.models import WorkspaceMember
from app.modules.workspaces.models.invitation_models import WorkspaceInvitation
from app.modules.workspaces.repositories.invitation_repository import (
    InvitationRepository,
)
from app.modules.workspaces.security.invitation_token import InvitationToken
from app.modules.workspaces.security.member_service import MemberService
from app.modules.workspaces.security.role_service import RoleService


class InvitationService:
    INVITATION_EXPIRY_DAYS = 7

    @staticmethod
    @require_permission(Permission.MEMBERS_INVITE)
    async def create_invitation(
        db: AsyncSession,
        workspace_id: UUID,
        email: str,
        role_key: str,
        user_id: UUID,
    ) -> tuple[WorkspaceInvitation, str]:

        # Step 1: Normalize email.
        normalized_email = email.strip().lower()

        # Step 2: Validate the selected role.
        role = await RoleService.get_role_by_key(
            db=db,
            workspace_id=workspace_id,
            role_key=role_key.strip().upper(),
        )

        if role is None:
            raise ValueError("The selected role does not belong to this workspace.")

        if role.role_key == "OWNER":
            raise ValueError("You cannot invite users with the Owner role.")

        # Step 3: Check for an existing pending invitation.
        existing_invitation = await InvitationRepository.get_pending_by_email(
            db=db,
            workspace_id=workspace_id,
            email_normalized=normalized_email,
        )

        # Step 4: Check whether the email belongs to a registered user.
        existing_user = await UserRepository.get_by_email(
            session=db,
            email=normalized_email,
        )

        # Step 5: If the user exists, check workspace membership.
        if existing_user is not None:
            is_member = await MemberService.is_workspace_member(
                db=db,
                workspace_id=workspace_id,
                user_id=existing_user.id,
            )

            if is_member:
                raise ValueError("This user is already a member of the workspace.")

        if existing_invitation is not None:
            raise ValueError("A pending invitation already exists for this email.")

        # Step 6: Generate the raw invitation token.
        raw_token = InvitationToken.generate_token()

        # Step 7: Hash the token.
        token_hash = InvitationToken.hash_token(raw_token)

        # Step 8: Calculate expiration time.
        expires_at = datetime.now(UTC) + timedelta(
            days=InvitationService.INVITATION_EXPIRY_DAYS
        )

        # Step 9: Create invitation model.
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email.strip(),
            email_normalized=normalized_email,
            role_id=role.id,
            invited_by=user_id,
            status=InvitationStatus.PENDING,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Step 10: Save invitation.
        invitation = await InvitationRepository.create(
            db=db,
            invitation=invitation,
        )

        # Step 11: Return invitation and raw token.
        return invitation, raw_token

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        raw_token: str,
        user_id: UUID,
        verified_email: str,
    ) -> WorkspaceInvitation:

        # Step 1: Hash the received raw token.
        token_hash = InvitationToken.hash_token(raw_token)

        # Step 2: Find the invitation using its token hash.
        invitation = await InvitationRepository.get_by_token_hash(
            db=db,
            token_hash=token_hash,
        )

        if invitation is None:
            raise ValueError("Invalid invitation link.")

        # Step 3: Verify invitation status.
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError("This invitation is no longer valid.")

        # Step 4: Verify invitation expiry.
        if invitation.expires_at <= datetime.now(UTC):
            raise ValueError("This invitation has expired.")

        # Step 5: Verify invited email.
        if verified_email.strip().lower() != invitation.email_normalized:
            raise ValueError("This invitation was sent to a different email address.")

        # Step 6: Prevent duplicate workspace membership.
        is_member = await MemberService.is_workspace_member(
            db=db,
            workspace_id=invitation.workspace_id,
            user_id=user_id,
        )

        if is_member:
            raise ValueError("You are already a member of this workspace.")

        # Step 7: Create workspace membership.
        membership = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role_id=invitation.role_id,
        )

        db.add(membership)

        # Step 8: Update invitation status.
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_by = user_id
        invitation.accepted_at = datetime.now(UTC)

        await db.flush()

        return invitation

    @staticmethod
    async def revoke_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceInvitation:

        # 1. Retrieve invitation.
        invitation = await InvitationRepository.get_by_id(
            db=db,
            invitation_id=invitation_id,
        )

        if invitation is None or invitation.workspace_id != workspace_id:
            raise ValueError("Invitation not found.")

        # 2. Verify original inviter.
        if invitation.invited_by != user_id:
            raise ValueError("Only the user who sent this invitation can revoke it.")

        # 3. Verify invitation status.
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError("Only pending invitations can be revoked.")

        # 4. Revoke invitation.
        invitation.status = InvitationStatus.REVOKED

        await InvitationRepository.update(
            db=db,
            invitation=invitation,
        )

        return invitation

    @staticmethod
    async def decline_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        verified_email: str,
    ) -> WorkspaceInvitation:

        # Step 1: Retrieve invitation.
        invitation = await InvitationRepository.get_by_id(
            db=db,
            invitation_id=invitation_id,
        )

        if invitation is None:
            raise ValueError("Invitation not found.")

        # Step 2: Verify that the authenticated user is the recipient.
        if verified_email.strip().lower() != invitation.email_normalized:
            raise ValueError("You are not authorized to decline this invitation.")

        # Step 3: Check invitation status.
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError("Only pending invitations can be declined.")

        # Step 4: Verify invitation expiry before changing its status.
        if invitation.expires_at <= datetime.now(UTC):
            raise ValueError("This invitation has expired.")

        # Step 5: Update invitation status.
        invitation.status = InvitationStatus.DECLINED

        await InvitationRepository.update(
            db=db,
            invitation=invitation,
        )

        return invitation

    @staticmethod
    @require_permission(Permission.MEMBERS_INVITE)
    async def resend_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> tuple[WorkspaceInvitation, str]:

        # Step 1: Retrieve invitation.
        invitation = await InvitationRepository.get_by_id(
            db=db,
            invitation_id=invitation_id,
        )

        if invitation is None or invitation.workspace_id != workspace_id:
            raise ValueError("Invitation not found.")

        # Step 2: Verify original inviter.
        if invitation.invited_by != user_id:
            raise ValueError("Only the original inviter can resend this invitation.")

        # Step 3: Validate invitation status.
        if invitation.status not in {
            InvitationStatus.PENDING,
            InvitationStatus.EXPIRED,
        }:
            raise ValueError("This invitation cannot be resent.")

        # Step 4: Generate a new token.
        raw_token = InvitationToken.generate_token()
        token_hash = InvitationToken.hash_token(raw_token)

        # Step 5: Update invitation details.
        invitation.token_hash = token_hash
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.now(UTC) + timedelta(
            days=InvitationService.INVITATION_EXPIRY_DAYS
        )

        await InvitationRepository.update(
            db=db,
            invitation=invitation,
        )

        return invitation, raw_token

    @staticmethod
    @require_permission(Permission.MEMBERS_READ)
    async def get_workspace_invitations(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[WorkspaceInvitation]:

        return await InvitationRepository.get_workspace_invitations(
            db=db,
            workspace_id=workspace_id,
        )

    @staticmethod
    @require_permission(Permission.MEMBERS_READ)
    async def get_pending_invitations(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[WorkspaceInvitation]:

        return await InvitationRepository.get_pending_invitations(
            db=db,
            workspace_id=workspace_id,
        )
