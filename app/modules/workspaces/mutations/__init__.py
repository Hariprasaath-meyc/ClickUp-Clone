import strawberry

from app.modules.workspaces.mutations.invitation_mutation import InvitationMutation
from app.modules.workspaces.mutations.membership_mutation import MembershipMutation
from app.modules.workspaces.mutations.workspace_mutation import WorkspaceMutation


@strawberry.type
class Mutation(
    WorkspaceMutation,
    InvitationMutation,
    MembershipMutation,
):
    pass
