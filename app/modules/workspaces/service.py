from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.users.models import User
from app.modules.workspaces.models import (
    Role,
   
    Workspace,
    WorkspaceMember,
)
from app.modules.workspaces.repository import WorkspaceRepository


async def create_workspace(
    db: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    slug: str,
) -> Workspace:

    # 1. Verify that the creator exists.
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

    # Generate the workspace ID.
    await db.flush()

    # 3. Retrieve the existing global OWNER role.
    result = await db.execute(
        select(Role).where(Role.role_key == "OWNER")
    )
    owner_role = result.scalar_one_or_none()

    if owner_role is None:
        raise RuntimeError(
            "Global OWNER role has not been seeded."
        )

    # 4. Assign the global OWNER role to the creator.
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role_id=owner_role.id,
    )

    db.add(membership)

    # 5. Flush pending changes.
    await db.flush()

    return workspace



@require_permission(Permission.WORKSPACE_READ)
async def get_workspace(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> Workspace:

    workspace = await WorkspaceRepository.get_by_id(
        db=db,
        workspace_id=workspace_id,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    return workspace


async def get_workspace_by_slug(
    db: AsyncSession,
    *,
    slug: str,
    user_id: UUID,
) -> Workspace:

    # 1. Resolve workspace using slug.
    workspace = await WorkspaceRepository.get_by_slug(
        db=db,
        slug=slug,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    # 2. Delegate to the protected method.
    return await get_workspace(
        db=db,
        workspace_id=workspace.id,
        user_id=user_id,
    )


@require_permission(Permission.WORKSPACE_UPDATE)
async def update_workspace(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    name: str,
    slug: str,
) -> Workspace:

    # 1. Retrieve workspace.
    workspace = await WorkspaceRepository.get_by_id(
        db=db,
        workspace_id=workspace_id,
    )

    if workspace is None:
        raise ValueError("Workspace not found.")

    # 2. Execute update.
    return await WorkspaceRepository.update(
        db,
        workspace,
        name=name,
        slug=slug,
    )


@require_permission(Permission.WORKSPACE_DELETE)
async def delete_workspace(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> Workspace:

    # 1. Retrieve workspace.
    workspace = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
        )
    )
    workspace = workspace.scalar_one_or_none()

    if workspace is None:
        raise ValueError("Workspace does not exist.")

    # 2. Check deletion status.
    if workspace.deleted_at is not None:
        raise ValueError("This workspace has already been deleted.")

    # 3. Perform soft deletion.
    return await WorkspaceRepository.soft_delete(
        db=db,
        workspace=workspace,
    )

