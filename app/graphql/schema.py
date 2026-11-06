

import strawberry
from graphql import GraphQLError

from app.modules.auth.mutation import AuthMutation

from app.modules.tags.mutations.tag_mutation import TagMutation
from app.modules.tags.queries.tag_query import TagQuery
from app.modules.tasks.mutations.task_comment_mutation import TaskCommentMutation
from app.modules.tasks.queries.task_history_query import TaskHistoryQuery
from app.modules.users.schema import UserQuery
from app.modules.users.mutation import UserMutation
from app.modules.tasks.queries import TaskQuery
from app.modules.workspaces.mutations.membership_mutation import MembershipMutation
from app.modules.workspaces.queries import (
    WorkspaceQuery,
    InvitationQuery,
    MembershipQuery,
)
from app.modules.tasks.mutations import TaskMutation
from app.modules.workspaces.mutations import (
    Mutation as WorkspaceMutations,
)



@strawberry.type
class Query(
    UserQuery,
    WorkspaceQuery,
    InvitationQuery,
    MembershipQuery,
    TaskQuery,
    TaskHistoryQuery,
    TagQuery,

    

):
    @strawberry.field
    def hello(self) -> str:
        return "ClickUp Clone GraphQL API is running"

    @strawberry.field
    def test_expected_error(self) -> str:
        raise GraphQLError("This is an expected error.")

    @strawberry.field
    def test_unexpected_error(self) -> str:
        raise RuntimeError("Testing centralized error handling")


@strawberry.type
class Mutation(
    AuthMutation,
    UserMutation,
    WorkspaceMutations,
    MembershipMutation,
    TaskMutation,
    TaskCommentMutation,
    TagMutation
    
    
):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
