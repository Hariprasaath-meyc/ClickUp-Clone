"""seed initial permissions"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "91a2290799df"
down_revision: Union[str, Sequence[str], None] = "45cf4ab463d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    ("workspace.create", "Workspace Create"),
    ("workspace.read", "Workspace Read"),
    ("workspace.update", "Workspace Update"),
    ("workspace.delete", "Workspace Delete"),

    ("members.read", "Members Read"),
    ("members.invite", "Members Invite"),
    ("members.update_role", "Members Update Role"),
    ("members.remove", "Members Remove"),

    ("roles.read", "Roles Read"),
    ("roles.create", "Roles Create"),
    ("roles.update", "Roles Update"),
    ("roles.delete", "Roles Delete"),
    ("permissions.manage", "Permissions Manage"),

    ("tasks.create", "Tasks Create"),
    ("tasks.read", "Tasks Read"),
    ("tasks.update", "Tasks Update"),
    ("tasks.delete", "Tasks Delete"),
    ("tasks.assign", "Tasks Assign"),

    ("comments.create", "Comments Create"),
    ("comments.read", "Comments Read"),
    ("comments.update", "Comments Update"),
    ("comments.delete", "Comments Delete"),

    ("tags.create", "Tags Create"),
    ("tags.read", "Tags Read"),
    ("tags.update", "Tags Update"),
    ("tags.delete", "Tags Delete"),
]


def upgrade() -> None:
    connection = op.get_bind()

    for permission_key, description in PERMISSIONS:
        connection.execute(
            sa.text("""
                INSERT INTO permissions (
                    id,
                    permission_key,
                    description
                )
                VALUES (
                    :id,
                    :permission_key,
                    :description
                )
                ON CONFLICT (permission_key) DO NOTHING
            """),
            {
                "id": uuid.uuid4(),
                "permission_key": permission_key,
                "description": description,
            },
        )


def downgrade() -> None:
    # Intentionally retain permission records.
    # They may be referenced by role-permission mappings.
    pass