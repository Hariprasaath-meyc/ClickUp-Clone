import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.decorators import require_permission
from app.modules.authorization.permissions import Permission
from app.modules.tags.repository import (
    TagRepository,
    TaskTagRepository,
)
from app.modules.tasks.decorators import record_task_history
from app.modules.tasks.enums import TaskHistoryAction
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.services import TaskHistoryService
from app.modules.tasks.types.task_types import TaskHistoryContext


class TagService:
    @staticmethod
    @require_permission(Permission.TASKS_UPDATE)
    @record_task_history
    async def assign_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_names: list[str],
        user_id: uuid.UUID,
    ):
        # 1. Validate task existence.
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Validate tag names.
        if not tag_names:
            raise ValueError("At least one tag name is required.")

        normalized_names = list(
            dict.fromkeys(
                name.strip().lower() for name in tag_names if name and name.strip()
            )
        )

        if not normalized_names:
            raise ValueError("Valid tag names are required.")

        assigned_tag_ids = []

        # 3. Process each tag.
        for name in normalized_names:
            tag = await TagRepository.get_by_name(
                db=db,
                workspace_id=workspace_id,
                name=name,
            )

            # Create tag if it doesn't exist.
            if tag is None:
                tag = await TagRepository.create(
                    db=db,
                    workspace_id=workspace_id,
                    name=name,
                    created_by=user_id,
                )

            # Check whether already assigned.
            existing_assignments = await TaskTagRepository.get_task_tags(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
            )

            existing_tag_ids = {
                assignment.tag_id for assignment in existing_assignments
            }

            if tag.id not in existing_tag_ids:
                await TaskTagRepository.assign_tag(
                    db=db,
                    workspace_id=workspace_id,
                    task_id=task_id,
                    tag_id=tag.id,
                    assigned_by=user_id,
                )

                assigned_tag_ids.append(tag.id)

        # 4. Record audit history.
        if assigned_tag_ids:
            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=user_id,
                action=TaskHistoryAction.TASK_TAG_ADDED,
                changes={"tag_ids": [str(tag_id) for tag_id in assigned_tag_ids]},
            )

        # 5. Return current task tags.
        task_tags = await TaskTagRepository.get_task_tags(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        return TaskHistoryContext(
            task=task,
            action=TaskHistoryAction.TASK_TAG_ADDED,
            changes={
                "tag_ids": [str(tag_id) for tag_id in assigned_tag_ids]
            },
            result=task_tags,
        )

    @staticmethod
    @require_permission(Permission.TASKS_UPDATE)
    @record_task_history
    async def remove_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:

        # 1. Validate task existence.
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 2. Validate input.
        if not tag_ids:
            raise ValueError("At least one tag ID is required.")

        tag_ids = list(dict.fromkeys(tag_ids))

        # 3. Retrieve current assignments.
        existing_assignments = await TaskTagRepository.get_task_tags(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        existing_tag_ids = {assignment.tag_id for assignment in existing_assignments}

        removed_tag_ids = [tag_id for tag_id in tag_ids if tag_id in existing_tag_ids]

        if not removed_tag_ids:
            return TaskHistoryContext(
                task=task,
                action=TaskHistoryAction.TASK_TAG_REMOVED,
                changes={},
                result=0,
            )

        # 4. Remove associations.
        removed_count = 0

        for tag_id in removed_tag_ids:
            removed = await TaskTagRepository.remove_tag(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                tag_id=tag_id,
            )

            if removed:
                removed_count += 1

        # 5. Return audit event.
        return TaskHistoryContext(
            task=task,
            action=TaskHistoryAction.TASK_TAG_REMOVED,
            changes={
                "tag_ids": [str(tag_id) for tag_id in removed_tag_ids]
            } if removed_count else {},
            result=removed_count,
        )

    @staticmethod
    @require_permission(Permission.TASKS_READ)
    async def get_workspace_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        return await TagRepository.get_workspace_tags(
            db=db,
            workspace_id=workspace_id,
        )
