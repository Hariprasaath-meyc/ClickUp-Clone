from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.workspaces.models import Permission as PermissionModel


async def seed_permissions(db: AsyncSession) -> None:
    """
    Insert missing permission records into PostgreSQL.

    Existing permissions are preserved, making repeated calls safe
    against duplicate permission keys.
    """

    result = await db.execute(
        select(PermissionModel.permission_key)
    )

    existing_keys = set(result.scalars().all())

    missing_permissions = [
        PermissionModel(
            permission_key=permission.value,
            description=permission.name.replace("_", " ").title(),
        )
        for permission in Permission
        if permission.value not in existing_keys
    ]

    if missing_permissions:
        db.add_all(missing_permissions)
        await db.flush()