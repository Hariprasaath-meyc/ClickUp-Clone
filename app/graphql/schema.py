from graphql import GraphQLError
import strawberry

from app.modules.auth.mutation import AuthMutation

from app.modules.users.schema import UserQuery
from app.modules.users.mutation import UserMutation

from app.modules.workspaces.schema import WorkspaceQuery
from app.modules.workspaces.mutation import WorkspaceMutation


@strawberry.type
class Query(
    UserQuery,
    WorkspaceQuery,
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
    WorkspaceMutation,
):
    pass



schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)