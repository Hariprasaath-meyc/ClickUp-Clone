
import strawberry

from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import require_authenticated_user
from app.modules.tasks.types.task_types import DeleteTaskInput, DeleteTaskResult, RestoreTaskInput
from app.modules.users.repository import UserRepository
from app.modules.tasks.services import TaskService
from app.modules.tasks.types import (
    CreateTaskInput,
    TaskResult,
    TaskType,
)
from app.modules.tasks.types import UpdateTaskInput
from app.modules.tasks.services import TaskAssigneeService
from app.modules.tasks.repository import TaskAssigneeRepository
from app.modules.tasks.types import (
    AssignTaskInput,
    UnassignTaskInput,
    TaskAssigneeType,
    TaskAssignmentResult,
    TaskUnassignmentResult,
)

@strawberry.type
class TaskMutation:

    @strawberry.mutation
    async def create_task(
        self,
        info: strawberry.Info,
        input: CreateTaskInput,
    ) -> TaskResult:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            task = await TaskService.create_task(
                db=db,
                workspace_id=input.workspace_id,
                user_id=user.id,
                title=input.title,
                description=input.description,
                status=input.status,
                priority=input.priority,
                due_date=input.due_date,
                parent_task_id=input.parent_task_id,
            )

            # Retrieve current task assignments
            assignments = await TaskAssigneeRepository.get_task_assignees(
                db=db,
                workspace_id=task.workspace_id,
                task_id=task.id,
            )

            await db.commit()

            return TaskResult(
                success=True,
                message="Task created successfully.",
                task=TaskType(
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
                ),
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to create task."
            ) from exc

    @strawberry.mutation
    async def update_task(
        self,
        info: strawberry.Info,
        input: UpdateTaskInput,
    ) -> TaskResult:

        db: AsyncSession = info.context["db"]

        try:
            claims = require_authenticated_user(info)

            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            update_data = {}

            if input.title is not None:
                update_data["title"] = input.title.value

            if input.description is not None:
                update_data["description"] = input.description.value

            if input.status is not None:
                update_data["status"] = input.status.value

            if input.priority is not None:
                update_data["priority"] = input.priority.value

            if input.due_date is not None:
                update_data["due_date"] = input.due_date.value

            task = await TaskService.update_task(
                db=db,
                task_id=input.task_id,
                workspace_id=input.workspace_id,
                user_id=user.id,
                update_data=update_data,
            )

            # Retrieve current task assignments
            assignments = await TaskAssigneeRepository.get_task_assignees(
                db=db,
                workspace_id=task.workspace_id,
                task_id=task.id,
            )

            await db.commit()

            return TaskResult(
                success=True,
                message="Task updated successfully.",
                task=TaskType(
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
                ),
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to update task."
            ) from exc

    @strawberry.mutation
    async def assign_task(
        self,
        info: strawberry.Info,
        input: AssignTaskInput,
    ) -> TaskAssignmentResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate requester
            claims = require_authenticated_user(info)

            # 2. Resolve local user
            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # 3. Call assignment service
            assignments = await TaskAssigneeService.assign_users(
                db=db,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                user_ids=input.user_ids,
                assigned_by=user.id,
            )

            # 4. Commit transaction
            await db.commit()

            return TaskAssignmentResult(
                success=True,
                message="Task assignees updated successfully.",
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

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to assign task."
            ) from exc

    @strawberry.mutation
    async def unassign_task(
        self,
        info: strawberry.Info,
        input: UnassignTaskInput,
    ) -> TaskUnassignmentResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate requester
            claims = require_authenticated_user(info)

            # 2. Resolve local user
            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # 3. Call unassignment service
            removed_count = await TaskAssigneeService.unassign_users(
                db=db,
                workspace_id=input.workspace_id,
                task_id=input.task_id,
                user_ids=input.user_ids,
                requested_by=user.id,
            )

            # 4. Commit transaction
            await db.commit()

            return TaskUnassignmentResult(
                success=True,
                message="Task unassignment completed.",
                removed_count=removed_count,
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to unassign task."
            ) from exc
        
    @strawberry.mutation
    async def delete_task(
        self,
        info: strawberry.Info,
        input: DeleteTaskInput,
    ) -> DeleteTaskResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate requester
            claims = require_authenticated_user(info)

            # 2. Resolve Cognito identity to local user
            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # 3. Call deletion service
            await TaskService.delete_task(
                db=db,
                task_id=input.task_id,
                workspace_id=input.workspace_id,
                user_id=user.id,
            )

            # 4. Commit task deletion and audit history together
            await db.commit()

            return DeleteTaskResult(
                success=True,
                message="Task deleted successfully.",
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to delete task."
            ) from exc

    @strawberry.mutation
    async def restore_task(
        self,
        info: strawberry.Info,
        input: RestoreTaskInput,
    ) -> TaskResult:

        db: AsyncSession = info.context["db"]

        try:
            # 1. Authenticate requester
            claims = require_authenticated_user(info)

            # 2. Resolve local user
            user = await UserRepository.get_by_cognito_sub(
                db,
                claims["sub"],
            )

            if user is None:
                raise GraphQLError("User account not found.")

            # 3. Restore task
            task = await TaskService.restore_task(
                db=db,
                task_id=input.task_id,
                workspace_id=input.workspace_id,
                user_id=user.id,
            )

            # 4. Retrieve task assignments
            assignments = await TaskAssigneeRepository.get_task_assignees(
                db=db,
                workspace_id=task.workspace_id,
                task_id=task.id,
            )

            # 5. Commit restoration and history
            await db.commit()

            return TaskResult(
                success=True,
                message="Task restored successfully.",
                task=TaskType(
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
                ),
            )

        except GraphQLError:
            await db.rollback()
            raise

        except ValueError as exc:
            await db.rollback()
            raise GraphQLError(str(exc)) from exc

        except Exception as exc:
            await db.rollback()
            raise GraphQLError(
                "Unable to restore task."
            ) from exc