from functools import wraps
from inspect import signature
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.types.task_types import TaskHistoryContext




def record_task_history(func: Callable):
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        bound = signature(func).bind(*args, **kwargs)
        bound.apply_defaults()

        # Execute the original service method.
        result = await func(*args, **kwargs)

        if not isinstance(result, TaskHistoryContext):
            raise TypeError(
                "Audited task operations must return TaskHistoryContext."
            )

        # Record history only when something changed.
        if result.changes:
            from app.modules.tasks.services.task_history_service import (
                TaskHistoryService,
            )

            db: AsyncSession = bound.arguments["db"]
            user_id = bound.arguments["user_id"]

            await TaskHistoryService.record_activity(
                db=db,
                workspace_id=result.task.workspace_id,
                task_id=result.task.id,
                actor_id=user_id,
                action=result.action,
                changes=result.changes,
            )

        # Preserve the original service method's return value.
        return result.result

    return wrapper