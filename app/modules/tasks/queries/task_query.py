import uuid
from uuid import UUID

import strawberry
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tasks.repository import TaskAssigneeRepository
from app.modules.tasks.services import TaskService
from app.modules.tasks.services.task_assignee_service import TaskAssigneeService
from app.modules.tasks.types import TaskAssigneeType, TaskType
from app.modules.users.repository import UserRepository


@strawberry.type
class TaskQuery:
    @strawberry.field
    async def workspace_tasks(
        self,
        info: strawberry.Info,
        workspace_id: uuid.UUID,
    ) -> list[TaskType]:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            tasks = await TaskService.get_workspace_tasks(
                db=db,
                workspace_id=workspace_id,
                user_id=user.id,
            )

            return [
                TaskType(
                    id=task.id,
                    workspace_id=task.workspace_id,
                    parent_task_id=task.parent_task_id,
                    title=task.title,
                    description=task.description,
                    status=task.status,
                    priority=task.priority,
                    created_by=task.created_by,
                    due_date=task.due_date,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    deleted_at=task.deleted_at,
                    assignees=[
                        TaskAssigneeType(
                            workspace_id=item.workspace_id,
                            task_id=item.task_id,
                            user_id=item.user_id,
                            assigned_by=item.assigned_by,
                            assigned_at=item.assigned_at,
                        )
                        for item in await TaskAssigneeRepository.get_task_assignees(
                            db=db,
                            workspace_id=task.workspace_id,
                            task_id=task.id,
                        )
                    ],
                )
                for task in tasks
            ]

        except GraphQLError:
            raise

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    @strawberry.field
    async def task_by_id(
        self,
        info: strawberry.Info,
        task_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> TaskType:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            task = await TaskService.get_task_by_id(
                db=db,
                task_id=task_id,
                workspace_id=workspace_id,
                user_id=user.id,
            )

            # Fetch task assignments
            assignees = await TaskAssigneeRepository.get_task_assignees(
                db=db,
                workspace_id=workspace_id,
                task_id=task_id,
            )

            return TaskType(
                id=task.id,
                workspace_id=task.workspace_id,
                parent_task_id=task.parent_task_id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                created_by=task.created_by,
                due_date=task.due_date,
                created_at=task.created_at,
                updated_at=task.updated_at,
                deleted_at=task.deleted_at,
                assignees=[
                    TaskAssigneeType(
                        workspace_id=item.workspace_id,
                        task_id=item.task_id,
                        user_id=item.user_id,
                        assigned_by=item.assigned_by,
                        assigned_at=item.assigned_at,
                    )
                    for item in assignees
                ],
            )

        except GraphQLError:
            raise

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    @strawberry.field
    async def my_assigned_tasks(
        self,
        info: strawberry.Info,
    ) -> list[TaskType]:

        db: AsyncSession = info.context["db"]

        try:
            # Identify the authenticated user
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # Fetch all tasks assigned to this user
            tasks = await TaskAssigneeService.get_my_assigned_tasks(
                db=db,
                user_id=user.id,
            )

            return [
                TaskType(
                    id=task.id,
                    workspace_id=task.workspace_id,
                    parent_task_id=task.parent_task_id,
                    title=task.title,
                    description=task.description,
                    status=task.status,
                    priority=task.priority,
                    created_by=task.created_by,
                    due_date=task.due_date,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    deleted_at=task.deleted_at,
                    assignees=[
                        TaskAssigneeType(
                            workspace_id=item.workspace_id,
                            task_id=item.task_id,
                            user_id=item.user_id,
                            assigned_by=item.assigned_by,
                            assigned_at=item.assigned_at,
                        )
                        for item in await TaskAssigneeRepository.get_task_assignees(
                            db=db,
                            workspace_id=task.workspace_id,
                            task_id=task.id,
                        )
                    ],
                )
                for task in tasks
            ]

        except GraphQLError:
            raise

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc

    @strawberry.field
    async def subtasks(
        self,
        info: Info,
        workspace_id: UUID,
        parent_task_id: UUID,
    ) -> list[TaskType]:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            subtasks = await TaskService.get_subtasks(
                db=db,
                workspace_id=workspace_id,
                parent_task_id=parent_task_id,
                current_user_id=user.id,
            )

            result = []

            for task in subtasks:
                assignments = await TaskAssigneeRepository.get_task_assignees(
                    db=db,
                    workspace_id=task.workspace_id,
                    task_id=task.id,
                )

                result.append(
                    TaskType(
                        id=task.id,
                        workspace_id=task.workspace_id,
                        parent_task_id=task.parent_task_id,
                        title=task.title,
                        description=task.description,
                        status=task.status,
                        priority=task.priority,
                        created_by=task.created_by,
                        due_date=task.due_date,
                        created_at=task.created_at,
                        updated_at=task.updated_at,
                        deleted_at=task.deleted_at,
                        assignees=[
                            TaskAssigneeType(
                                workspace_id=item.workspace_id,
                                task_id=item.task_id,
                                user_id=item.user_id,
                                assigned_by=item.assigned_by,
                                assigned_at=item.assigned_at,
                            )
                            for item in assignments
                        ],
                    )
                )

            return result

        except GraphQLError:
            raise

        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
