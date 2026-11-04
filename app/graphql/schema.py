
from graphql import GraphQLError
import strawberry

from app.modules.auth.mutation import AuthMutation

from app.modules.users.schema import UserQuery
from app.modules.users.mutation import UserMutation

# Import the newly separated workspace queries
from app.modules.workspaces.mutations.membership_mutation import MembershipMutation
from app.modules.workspaces.mutations.workspace_mutation import WorkspaceMutation
from app.modules.workspaces.queries.workspace_query import WorkspaceQuery
from app.modules.workspaces.queries.invitation_query import InvitationQuery
from app.modules.workspaces.queries.membership_query import MembershipQuery




@strawberry.type
class Query(
    UserQuery,
    WorkspaceQuery,
    InvitationQuery,
    MembershipQuery,

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
    MembershipMutation,
):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
