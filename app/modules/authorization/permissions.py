from enum import StrEnum


class Permission(StrEnum):
    # Workspace
    WORKSPACE_CREATE = "workspace.create"
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_UPDATE = "workspace.update"
    WORKSPACE_DELETE = "workspace.delete"

    # Members
    MEMBERS_READ = "members.read"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_UPDATE_ROLE = "members.update_role"
    MEMBERS_REMOVE = "members.remove"

    # Roles and permissions
    ROLES_READ = "roles.read"
    ROLES_CREATE = "roles.create"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    PERMISSIONS_MANAGE = "permissions.manage"

    # Tasks
    TASKS_CREATE = "tasks.create"
    TASKS_READ = "tasks.read"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"
    TASKS_ASSIGN = "tasks.assign"

    # Task comment permissions
    COMMENTS_CREATE = "comments.create"
    COMMENTS_READ = "comments.read"
    COMMENTS_UPDATE = "comments.update"
    COMMENTS_DELETE = "comments.delete"

# Task tag permissions
    TAGS_CREATE = "tags.create"
    TAGS_READ = "tags.read"
    TAGS_UPDATE = "tags.update"
    TAGS_DELETE = "tags.delete"