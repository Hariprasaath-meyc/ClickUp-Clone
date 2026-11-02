from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.security.role_service import RoleService
from app.modules.workspaces.security.permission_service import PermissionService


class AuthorizationService:

    @staticmethod
    async def require_permission(
        db: AsyncSession,
        user_id: UUID,
        workspace_id: UUID,
        permission_key: str,
    ) -> None:

        # Step 1: Retrieve the user's role in this workspace.
        role = await RoleService.get_user_role(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        # Step 2: Ensure the user belongs to this workspace.
        if role is None:
            raise PermissionError(
                "You are not a member of this workspace."
            )

        # Step 3: Check whether the role has the required permission.
        allowed = await PermissionService.has_permission(
            db=db,
            workspace_id=workspace_id,
            role_id=role.id,
            permission_key=permission_key,
        )

        # Step 4: Deny access if permission is missing.
        if not allowed:
            raise PermissionError(
                "You do not have permission to perform this action."
            )