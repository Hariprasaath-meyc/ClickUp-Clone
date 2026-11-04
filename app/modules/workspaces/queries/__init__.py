import strawberry

from app.modules.workspaces.queries.workspace_query import WorkspaceQuery
from app.modules.workspaces.queries.invitation_query import InvitationQuery
from app.modules.workspaces.queries.membership_query import MembershipQuery


@strawberry.type
class Query(
    WorkspaceQuery,
    InvitationQuery,
    MembershipQuery,
):
    pass