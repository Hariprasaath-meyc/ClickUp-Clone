import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tags.models import Tag


class TagRepository:
    @staticmethod
    async def get_by_name(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        name: str,
    ) -> Tag | None:

        result = await db.execute(
            select(Tag).where(
                Tag.workspace_id == workspace_id,
                Tag.name == name,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        name: str,
        created_by: uuid.UUID,
    ) -> Tag:

        tag = Tag(
            workspace_id=workspace_id,
            name=name,
            created_by=created_by,
        )

        db.add(tag)

        await db.flush()

        return tag

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> Tag | None:

        result = await db.execute(
            select(Tag).where(
                Tag.id == tag_id,
                Tag.workspace_id == workspace_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_workspace_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[Tag]:

        result = await db.execute(
            select(Tag)
            .where(Tag.workspace_id == workspace_id)
            .order_by(Tag.created_at.desc())
        )

        return list(result.scalars().all())
