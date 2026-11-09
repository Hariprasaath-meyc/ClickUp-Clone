import uuid

import strawberry
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tasks.services import TaskHistoryService
from app.modules.tasks.types import TaskHistoryType
from app.modules.users.repository import UserRepository


@strawberry.type
class TaskHistoryQuery:
    @strawberry.field
    async def task_history(
        self,
        info: strawberry.Info,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> list[TaskHistoryType]:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            history = await TaskHistoryService.get_task_history(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
                user_id=user.id,
            )

            return [
                TaskHistoryType(
                    id=item.id,
                    workspace_id=item.workspace_id,
                    task_id=item.task_id,
                    actor_id=item.actor_id,
                    action=item.action,
                    changes=item.changes,
                    created_at=item.created_at,
                )
                for item in history
            ]

        except GraphQLError:
            raise

        except PermissionError as exc:
            raise GraphQLError(str(exc)) from exc

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
