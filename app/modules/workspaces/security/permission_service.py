from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.workspaces.models.models import (
    Permission as PermissionModel,
    RolePermission,
)




class PermissionService:

    @staticmethod
    async def get_role_permissions(
        db: AsyncSession,
        workspace_id: UUID,
        role_id: UUID,
    ) -> list[str]:

        result = await db.execute(
            select(PermissionModel.permission_key)
            .join(
                RolePermission,
                RolePermission.permission_id == PermissionModel.id,
            )
            .where(
                RolePermission.workspace_id == workspace_id,
                RolePermission.role_id == role_id,
            )
        )

        return list(result.scalars().all())


    @staticmethod
    async def has_permission(
        db: AsyncSession,
        workspace_id: UUID,
        role_id: UUID,
        permission_key: str,
    ) -> bool:

        result = await db.execute(
            select(PermissionModel.id)
            .join(
                RolePermission,
                RolePermission.permission_id == PermissionModel.id,
            )
            .where(
                RolePermission.workspace_id == workspace_id,
                RolePermission.role_id == role_id,
                PermissionModel.permission_key == permission_key,
            )
            .limit(1)
        )

        return result.scalar_one_or_none() is not None