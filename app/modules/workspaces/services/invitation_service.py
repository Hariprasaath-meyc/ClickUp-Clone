from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.enums import InvitationStatus
from app.modules.workspaces.invitation_models import WorkspaceInvitation
from app.modules.workspaces.models import WorkspaceMember
from app.modules.workspaces.repositories.invitation_repository import (
    InvitationRepository,
)
from app.modules.users.repository import UserRepository
from app.modules.workspaces.security.member_service import MemberService
from app.modules.workspaces.security.invitation_token import InvitationToken
from app.modules.workspaces.security.role_service import RoleService


class InvitationService:

    INVITATION_EXPIRY_DAYS = 7

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        workspace_id: UUID,
        email: str,
        role_key: str,
        invited_by: UUID,
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
            raise ValueError(
                "The selected role does not belong to this workspace."
            )

        if role.role_key == "OWNER":
            raise ValueError(
                "You cannot invite users with the Owner role."
            )

        # Step 3: Check for an existing pending invitation.
        existing_invitation = (
            await InvitationRepository.get_pending_by_email(
                db=db,
                workspace_id=workspace_id,
                email_normalized=normalized_email,
            )
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
                raise ValueError(
                    "This user is already a member of the workspace."
                )

        if existing_invitation is not None:
            raise ValueError(
                "A pending invitation already exists for this email."
            )

        # Step 3: Generate the raw invitation token.
        raw_token = InvitationToken.generate_token()

        # Step 4: Hash the token.
        token_hash = InvitationToken.hash_token(raw_token)

        # Step 5: Calculate expiration time.
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=InvitationService.INVITATION_EXPIRY_DAYS
        )

        # Step 6: Create invitation model.
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email.strip(),
            email_normalized=normalized_email,
            role_id=role.id,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Step 7: Save invitation.
        invitation = await InvitationRepository.create(
            db=db,
            invitation=invitation,
        )

        # Step 8: Return invitation and raw token.
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
        if invitation.expires_at <= datetime.now(timezone.utc):
            raise ValueError("This invitation has expired.")

        # Step 5: Verify invited email.
        if verified_email.strip().lower() != invitation.email_normalized:
            raise ValueError(
                "This invitation was sent to a different email address."
            )

        # Step 6: Prevent duplicate workspace membership.
        is_member = await MemberService.is_workspace_member(
            db=db,
            workspace_id=invitation.workspace_id,
            user_id=user_id,
        )

        if is_member:
            raise ValueError(
                "You are already a member of this workspace."
            )

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
        invitation.accepted_at = datetime.now(timezone.utc)

        await db.flush()

        return invitation
    
    @staticmethod
    async def revoke_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        workspace_id: UUID,
    ) -> WorkspaceInvitation:

        invitation = await InvitationRepository.get_by_id(
            db=db,
            invitation_id=invitation_id,
        )

        if invitation is None or invitation.workspace_id != workspace_id:
            raise ValueError("Invitation not found.")

        if invitation.status != InvitationStatus.PENDING:
            raise ValueError(
                "Only pending invitations can be revoked."
            )

        invitation.status = InvitationStatus.REVOKED

        await InvitationRepository.update(
            db=db,
            invitation=invitation,
        )

        return invitation