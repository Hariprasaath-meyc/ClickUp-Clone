from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.models import Workspace


class WorkspaceAccessService:

    @staticmethod
    async def require_active_workspace(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> Workspace:

        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.deleted_at.is_(None),
            )
        )

        workspace = result.scalar_one_or_none()

        if workspace is None:
            raise ValueError(
                "Workspace not found or has been deleted."
            )

        return workspace