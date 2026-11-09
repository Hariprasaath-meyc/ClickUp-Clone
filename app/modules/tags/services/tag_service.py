import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.permissions import Permission
from app.modules.tags.repository import (
    TagRepository,
    TaskTagRepository,
)
from app.modules.tasks.enums import TaskHistoryAction
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.services import TaskHistoryService
from app.modules.workspaces.security.authorization_service import (
    AuthorizationService,
)


class TagService:
    @staticmethod
    async def assign_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_names: list[str],
        user_id: uuid.UUID,
    ):

        # 1. Check permission
        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_UPDATE.value,
        )

        # 2. Validate task existence
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 3. Validate tag names
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

        # 4. Process each tag
        for name in normalized_names:
            # Check whether tag already exists
            tag = await TagRepository.get_by_name(
                db=db,
                workspace_id=workspace_id,
                name=name,
            )

            # Create tag if it doesn't exist
            if tag is None:
                tag = await TagRepository.create(
                    db=db,
                    workspace_id=workspace_id,
                    name=name,
                    created_by=user_id,
                )

            # Check whether already assigned
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

        # 5. Record audit history
        if assigned_tag_ids:
            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=user_id,
                action=TaskHistoryAction.TASK_TAG_ADDED,
                changes={"tag_ids": [str(tag_id) for tag_id in assigned_tag_ids]},
            )

        # 6. Return current task tags
        return await TaskTagRepository.get_task_tags(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
        )

    @staticmethod
    async def remove_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        tag_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:

        # 1. Check permission
        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_UPDATE.value,
        )

        # 2. Validate task existence
        task = await TaskRepository.get_by_id(
            db=db,
            task_id=task_id,
            workspace_id=workspace_id,
        )

        if task is None:
            raise ValueError("Task not found.")

        # 3. Validate input
        if not tag_ids:
            raise ValueError("At least one tag ID is required.")

        tag_ids = list(dict.fromkeys(tag_ids))

        # 4. Retrieve current assignments
        existing_assignments = await TaskTagRepository.get_task_tags(
            db=db,
            workspace_id=workspace_id,
            task_id=task_id,
        )

        existing_tag_ids = {assignment.tag_id for assignment in existing_assignments}

        # Only remove tags actually assigned to this task
        removed_tag_ids = [tag_id for tag_id in tag_ids if tag_id in existing_tag_ids]

        if not removed_tag_ids:
            return 0

        # 5. Remove associations
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

        # 6. Record audit history
        if removed_count:
            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                actor_id=user_id,
                action=TaskHistoryAction.TASK_TAG_REMOVED,
                changes={"tag_ids": [str(tag_id) for tag_id in removed_tag_ids]},
            )

        return removed_count

    @staticmethod
    async def get_workspace_tags(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        await AuthorizationService.require_permission(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            permission_key=Permission.TASKS_READ.value,
        )

        return await TagRepository.get_workspace_tags(
            db=db,
            workspace_id=workspace_id,
        )
