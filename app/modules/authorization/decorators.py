from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


from app.modules.authorization.permissions import Permission
from app.modules.workspaces.security.authorization_service import AuthorizationService
from app.modules.workspaces.security.workspace_access_service import (
    WorkspaceAccessService,
)


def require_permission(permission: Permission):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):

            # Extract the function arguments
            bound_arguments = signature(func).bind(*args, **kwargs)
            bound_arguments.apply_defaults()

            db: AsyncSession = bound_arguments.arguments["db"]
            user_id = bound_arguments.arguments["user_id"]
            workspace_id = bound_arguments.arguments["workspace_id"]


            # Step 1: Verify workspace is active.
            await WorkspaceAccessService.require_active_workspace(
                db=db,
                workspace_id=workspace_id,
            )
            
            # Step 2: Verify user permission.
            await AuthorizationService.require_permission(
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                permission_key=permission.value,
            )

            # Step 3: Execute service method.
            return await func(*args, **kwargs)

        return wrapper

    return decorator
