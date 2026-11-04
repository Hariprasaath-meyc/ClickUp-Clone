from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.invitation_models import WorkspaceInvitation
from app.modules.workspaces.enums import InvitationStatus
from sqlalchemy.orm import selectinload

class InvitationRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        invitation: WorkspaceInvitation,
    ) -> WorkspaceInvitation:
        db.add(invitation)
        await db.flush()
        return invitation

    @staticmethod
    async def get_by_token_hash(
        db: AsyncSession,
        token_hash: str,
    ) -> WorkspaceInvitation | None:
        result = await db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        invitation_id: UUID,
    ) -> WorkspaceInvitation | None:
        result = await db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.id == invitation_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_by_email(
        db: AsyncSession,
        workspace_id: UUID,
        email_normalized: str,
    ) -> WorkspaceInvitation | None:
        result = await db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email_normalized == email_normalized,
                WorkspaceInvitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        invitation: WorkspaceInvitation,
    ) -> WorkspaceInvitation:
        await db.flush()
        return invitation

    @staticmethod
    async def get_workspace_invitations(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[WorkspaceInvitation]:
        result = await db.execute(
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.workspace_id == workspace_id)
            .order_by(WorkspaceInvitation.created_at.desc())
        )
        return list(result.scalars().all())


     #Get Pending Invitations
    @staticmethod
    async def get_pending_invitations(
        db: AsyncSession,
        workspace_id: UUID,
    ):
        result = await db.execute(
            select(WorkspaceInvitation)
            .options(selectinload(WorkspaceInvitation.role))
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.status == InvitationStatus.PENDING,
            )
        )

        return result.scalars().all()