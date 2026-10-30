from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.models import (
    Workspace,
    WorkspaceMember,
)


class WorkspaceRepository:

    @staticmethod
    async def get_user_workspaces(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[Workspace]:
        result = await db.execute(
            select(Workspace)
            .join(
                WorkspaceMember,
                Workspace.id == WorkspaceMember.workspace_id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )

        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> Workspace | None:
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        workspace: Workspace,
        *,
        name: str | None = None,
        slug: str | None = None,
    ) -> Workspace:
        if name is not None:
            workspace.name = name

        if slug is not None:
            workspace.slug = slug

        await db.flush()
        await db.refresh(workspace)

        return workspace

    @staticmethod
    async def is_slug_taken(
        db: AsyncSession,
        slug: str,
    ) -> bool:
        result = await db.execute(
            select(Workspace.id).where(
                Workspace.slug == slug
            )
        )

        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_by_slug(
        db: AsyncSession,
        slug: str,
    ) -> Workspace | None:
        result = await db.execute(
            select(Workspace).where(
                Workspace.slug == slug
            )
        )

        return result.scalar_one_or_none()