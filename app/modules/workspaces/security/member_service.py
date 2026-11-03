from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.profile_models import UserProfile
from app.modules.workspaces.models import (
    Role,
    WorkspaceMember,
)


class MemberService:

    @staticmethod
    async def get_workspace_members(
        db: AsyncSession,
        workspace_id: UUID,
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
                (Role.id == WorkspaceMember.role_id)
                & (Role.workspace_id == WorkspaceMember.workspace_id),
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