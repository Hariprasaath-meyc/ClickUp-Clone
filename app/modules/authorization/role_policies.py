
from app.modules.authorization.permissions import Permission


ROLE_POLICIES: dict[str, set[Permission]] = {
    "OWNER": {
        # Workspace
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.WORKSPACE_DELETE,

        # Members
        Permission.MEMBERS_READ,
        Permission.MEMBERS_INVITE,
        Permission.MEMBERS_UPDATE_ROLE,
        Permission.MEMBERS_REMOVE,

        # Roles and permissions
        Permission.ROLES_READ,
        Permission.ROLES_CREATE,
        Permission.ROLES_UPDATE,
        Permission.ROLES_DELETE,
        Permission.PERMISSIONS_MANAGE,

        # Tasks
        Permission.TASKS_CREATE,
        Permission.TASKS_READ,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN,

        # Comments
        Permission.COMMENTS_CREATE,
        Permission.COMMENTS_READ,
        Permission.COMMENTS_UPDATE,
        Permission.COMMENTS_DELETE,

        # Tags
        Permission.TAGS_CREATE,
        Permission.TAGS_READ,
        Permission.TAGS_UPDATE,
        Permission.TAGS_DELETE,
    },

    "ADMIN": {
        # Workspace
        Permission.WORKSPACE_READ,

        # Members
        Permission.MEMBERS_READ,
        Permission.MEMBERS_INVITE,

        # Tasks
        Permission.TASKS_CREATE,
        Permission.TASKS_READ,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN,

        # Comments
        Permission.COMMENTS_CREATE,
        Permission.COMMENTS_READ,
        Permission.COMMENTS_UPDATE,
        Permission.COMMENTS_DELETE,

        # Tags
        Permission.TAGS_CREATE,
        Permission.TAGS_READ,
        Permission.TAGS_UPDATE,
        Permission.TAGS_DELETE,
    },

    "MEMBER": {
        # Workspace
        Permission.WORKSPACE_READ,

        # Tasks
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,

        # Comments
        Permission.COMMENTS_CREATE,
        Permission.COMMENTS_READ,
    },
}
