
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.models.models import Role, WorkspaceMember


class RoleService:

    @staticmethod
    async def get_user_role(
        db: AsyncSession,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Role | None:

        result = await db.execute(
            select(Role)
            .join(
                WorkspaceMember,
                WorkspaceMember.role_id == Role.id,
            )
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_role_by_key(
        db: AsyncSession,
        role_key: str,
    ) -> Role | None:

        result = await db.execute(
            select(Role).where(
                Role.role_key == role_key,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_roles(
        db: AsyncSession,
    ) -> list[Role]:

        result = await db.execute(
            select(Role)
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_role_by_id(
        db: AsyncSession,
        role_id: UUID,
    ) -> Role | None:

        result = await db.execute(
            select(Role).where(
                Role.id == role_id,
            )
        )

        return result.scalar_one_or_none()
