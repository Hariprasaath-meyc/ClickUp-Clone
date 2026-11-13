
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.users.models import User
from app.modules.users.profile_models import UserProfile
from app.modules.workspaces.models import Role, WorkspaceMember
from app.modules.workspaces.security.role_service import RoleService


class MemberService:

    @staticmethod
    @require_permission(Permission.MEMBERS_READ)
    async def get_workspace_members(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[tuple[User, UserProfile, Role, WorkspaceMember]]:

        result = await db.execute(
            select(User, UserProfile, Role, WorkspaceMember)
            .join(
                WorkspaceMember,
                WorkspaceMember.user_id == User.id,
            )
            .join(
                UserProfile,
                UserProfile.user_id == User.id,
            )
            .join(
                Role,
                Role.id == WorkspaceMember.role_id,
            )
            .where(
                WorkspaceMember.workspace_id == workspace_id,
            )
        )

        return list(result.all())

    @staticmethod
    async def is_workspace_member(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:

        result = await db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )

        return result.scalar_one_or_none() is not None

    @staticmethod
    @require_permission(Permission.MEMBERS_READ)
    async def get_workspace_member(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
    ) -> tuple[User, UserProfile | None, Role, WorkspaceMember] | None:

        result = await db.execute(
            select(User, UserProfile, Role, WorkspaceMember)
            .join(
                WorkspaceMember,
                WorkspaceMember.user_id == User.id,
            )
            .outerjoin(
                UserProfile,
                UserProfile.user_id == User.id,
            )
            .join(
                Role,
                Role.id == WorkspaceMember.role_id,
            )
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                User.id == target_user_id,
            )
        )

        return result.one_or_none()

    @staticmethod
    @require_permission(Permission.MEMBERS_UPDATE_ROLE)
    async def change_member_role(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        role_key: str,
        target_user_id: UUID,
    ) -> WorkspaceMember:

        # 1. Retrieve target membership and current role.
        result = await db.execute(
            select(WorkspaceMember, Role)
            .join(
                Role,
                Role.id == WorkspaceMember.role_id,
            )
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
            )
        )

        membership_data = result.one_or_none()

        if membership_data is None:
            raise ValueError("Workspace member not found.")

        membership, current_role = membership_data

        # 2. Prevent modification of OWNER.
        if current_role.role_key == "OWNER":
            raise ValueError("The OWNER role cannot be changed.")

        # 3. Retrieve the requested global role.
        new_role = await RoleService.get_role_by_key(
            db=db,
            role_key=role_key.strip().upper(),
        )

        if new_role is None:
            raise ValueError("Role not found.")

        # 4. Prevent assigning OWNER.
        if new_role.role_key == "OWNER":
            raise ValueError("The OWNER role cannot be assigned.")

        # 5. Check whether the member already has this role.
        if membership.role_id == new_role.id:
            raise ValueError(
                f"Member already has the {new_role.role_key} role."
            )

        # 6. Update membership.
        membership.role_id = new_role.id

        await db.flush()

        return membership

    @staticmethod
    @require_permission(Permission.MEMBERS_REMOVE)
    async def remove_member_from_workspace(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
    ) -> None:

        # 1. Retrieve target membership and current role.
        result = await db.execute(
            select(WorkspaceMember, Role)
            .join(
                Role,
                Role.id == WorkspaceMember.role_id,
            )
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
            )
        )

        membership_data = result.one_or_none()

        if membership_data is None:
            raise ValueError("Workspace member not found.")

        membership, current_role = membership_data

        # 2. Prevent removing the OWNER.
        if current_role.role_key == "OWNER":
            raise ValueError("The workspace OWNER cannot be removed.")

        # 3. Remove workspace membership.
        await db.delete(membership)

        await db.flush()
