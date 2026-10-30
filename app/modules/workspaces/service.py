
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permission_seeder import seed_permissions
from app.modules.authorization.role_policies import ROLE_POLICIES
from app.modules.users.models import User
from app.modules.workspaces.models import (
    Permission,
    Role,
    RolePermission,
    Workspace,
    WorkspaceMember,
)


async def create_workspace(
    db: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    slug: str,
) -> Workspace:
        # 1. Verify that the creator exists in our PostgreSQL users table.
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("User does not exist.")

        # 2. Create the workspace.
        workspace = Workspace(
            name=name,
            slug=slug,
            created_by=user.id,
        )
        db.add(workspace)

        # Generate the workspace ID and insert it before creating
        # records that depend on it.
        await db.flush()

        # 3. Create the predefined roles.
        roles = {
            "OWNER": Role(
                workspace_id=workspace.id,
                role_key="OWNER",
                name="Owner",
                is_system_role=True,
            ),
            "ADMIN": Role(
                workspace_id=workspace.id,
                role_key="ADMIN",
                name="Admin",
                is_system_role=True,
            ),
            "MEMBER": Role(
                workspace_id=workspace.id,
                role_key="MEMBER",
                name="Member",
                is_system_role=True,
            ),
        }

        db.add_all(roles.values())
        await db.flush()

        # 4. Ensure that all predefined permissions exist.
        await seed_permissions(db)

        # 5. Retrieve the permission records from PostgreSQL.
        permission_keys = {
            permission.value
            for policy in ROLE_POLICIES.values()
            for permission in policy
        }

        result = await db.execute(
            select(Permission).where(
                Permission.permission_key.in_(permission_keys)
            )
        )

        permissions_by_key = {
            permission.permission_key: permission
            for permission in result.scalars().all()
        }

        # 6. Map each role to its configured permissions.
        role_permission_mappings = []

        for role_key, policy in ROLE_POLICIES.items():
            role = roles[role_key]

            for permission in policy:
                permission_model = permissions_by_key.get(
                    permission.value
                )

                if permission_model is None:
                    raise RuntimeError(
                        f"Permission was not seeded: {permission.value}"
                    )

                role_permission_mappings.append(
                    RolePermission(
                        workspace_id=workspace.id,
                        role_id=role.id,
                        permission_id=permission_model.id,
                    )
                )

        db.add_all(role_permission_mappings)

        # 7. Assign the workspace creator the OWNER role.
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role_id=roles["OWNER"].id,
        )

        db.add(membership)

        # 8. Flush pending changes so database constraints are checked.
        await db.flush()

        return workspace
