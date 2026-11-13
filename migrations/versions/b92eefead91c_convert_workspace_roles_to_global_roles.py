
"""Convert workspace-specific roles into global roles.

Revision ID: b92eefead91c
Revises: a05e59313f33
"""

import uuid

import sqlalchemy as sa
from alembic import op


revision = "b92eefead91c"
down_revision = "a05e59313f33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove old composite foreign keys.
    op.drop_constraint(
        "fk_role_permissions_workspace_role",
        "role_permissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_workspace_members_workspace_role",
        "workspace_members",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_workspace_invitations_workspace_role",
        "workspace_invitations",
        type_="foreignkey",
    )

    # 2. Remove the old role_permissions primary key.
    op.drop_constraint(
        "role_permissions_pkey",
        "role_permissions",
        type_="primary",
    )

    # 3. Create exactly three global roles.
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("role_key", sa.String(50)),
        sa.column("name", sa.String(100)),
        sa.column("is_system_role", sa.Boolean()),
    )

    role_ids = {
        "OWNER": uuid.uuid4(),
        "ADMIN": uuid.uuid4(),
        "MEMBER": uuid.uuid4(),
    }

    op.bulk_insert(
        roles_table,
        [
            {
                "id": role_ids["OWNER"],
                "workspace_id": None,
                "role_key": "OWNER",
                "name": "Owner",
                "is_system_role": True,
            },
            {
                "id": role_ids["ADMIN"],
                "workspace_id": None,
                "role_key": "ADMIN",
                "name": "Admin",
                "is_system_role": True,
            },
            {
                "id": role_ids["MEMBER"],
                "workspace_id": None,
                "role_key": "MEMBER",
                "name": "Member",
                "is_system_role": True,
            },
        ],
    )

    # 4. Update existing memberships to use global role IDs.
    op.execute(
        """
        UPDATE workspace_members AS wm
        SET role_id = global_role.id
        FROM roles AS old_role
        JOIN roles AS global_role
          ON global_role.role_key = old_role.role_key
         AND global_role.workspace_id IS NULL
        WHERE wm.role_id = old_role.id
          AND old_role.workspace_id IS NOT NULL;
        """
    )

    # 5. Update existing invitations to use global role IDs.
    op.execute(
        """
        UPDATE workspace_invitations AS wi
        SET role_id = global_role.id
        FROM roles AS old_role
        JOIN roles AS global_role
          ON global_role.role_key = old_role.role_key
         AND global_role.workspace_id IS NULL
        WHERE wi.role_id = old_role.id
          AND old_role.workspace_id IS NOT NULL;
        """
    )

    # 6. Remove old workspace-specific role permission mappings.
    op.execute("DELETE FROM role_permissions;")

    # 7. Remove old workspace-specific role records.
    op.execute(
        "DELETE FROM roles WHERE workspace_id IS NOT NULL;"
    )

    # 8. Remove workspace-specific role constraints.
    op.drop_constraint(
        "roles_workspace_id_fkey",
        "roles",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_roles_workspace_id_id",
        "roles",
        type_="unique",
    )
    op.drop_constraint(
        "uq_roles_workspace_role_key",
        "roles",
        type_="unique",
    )

    # 9. Remove workspace-specific columns from roles.
    op.drop_column("roles", "workspace_id")
    op.drop_column("roles", "is_system_role")

    # 10. Make role_key globally unique.
    op.create_unique_constraint(
        "uq_roles_role_key",
        "roles",
        ["role_key"],
    )

    # 11. Convert role_permissions into a global mapping table.
    op.drop_column("role_permissions", "workspace_id")

    op.create_primary_key(
        "role_permissions_pkey",
        "role_permissions",
        ["role_id", "permission_id"],
    )

    # 12. Add direct role foreign keys.
    op.create_foreign_key(
        "fk_role_permissions_role",
        "role_permissions",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_workspace_members_role",
        "workspace_members",
        "roles",
        ["role_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_workspace_invitations_role",
        "workspace_invitations",
        "roles",
        ["role_id"],
        ["id"],
    )

    # 13. Validate that all required permission records exist.
    op.execute(
        """
        DO $$
        DECLARE
            missing_count INTEGER;
        BEGIN
            SELECT COUNT(*)
            INTO missing_count
            FROM (
                VALUES
                    ('workspace.create'),
                    ('workspace.read'),
                    ('workspace.update'),
                    ('workspace.delete'),
                    ('members.read'),
                    ('members.invite'),
                    ('members.update_role'),
                    ('members.remove'),
                    ('roles.read'),
                    ('roles.create'),
                    ('roles.update'),
                    ('roles.delete'),
                    ('permissions.manage'),
                    ('tasks.create'),
                    ('tasks.read'),
                    ('tasks.update'),
                    ('tasks.delete'),
                    ('tasks.assign'),
                    ('comments.create'),
                    ('comments.read'),
                    ('comments.update'),
                    ('comments.delete'),
                    ('tags.create'),
                    ('tags.read'),
                    ('tags.update'),
                    ('tags.delete')
            ) AS expected(permission_key)
            LEFT JOIN permissions p
              ON p.permission_key = expected.permission_key
            WHERE p.id IS NULL;

            IF missing_count > 0 THEN
                RAISE EXCEPTION
                    'Missing % required permission records. '
                    'Seed permissions before applying this migration.',
                    missing_count;
            END IF;
        END $$;
        """
    )

    # 14. Insert global role-permission mappings.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM (
            VALUES
                -- OWNER
                ('OWNER', 'workspace.create'),
                ('OWNER', 'workspace.read'),
                ('OWNER', 'workspace.update'),
                ('OWNER', 'workspace.delete'),

                ('OWNER', 'members.read'),
                ('OWNER', 'members.invite'),
                ('OWNER', 'members.update_role'),
                ('OWNER', 'members.remove'),

                ('OWNER', 'roles.read'),
                ('OWNER', 'roles.create'),
                ('OWNER', 'roles.update'),
                ('OWNER', 'roles.delete'),
                ('OWNER', 'permissions.manage'),

                ('OWNER', 'tasks.create'),
                ('OWNER', 'tasks.read'),
                ('OWNER', 'tasks.update'),
                ('OWNER', 'tasks.delete'),
                ('OWNER', 'tasks.assign'),

                ('OWNER', 'comments.create'),
                ('OWNER', 'comments.read'),
                ('OWNER', 'comments.update'),
                ('OWNER', 'comments.delete'),

                ('OWNER', 'tags.create'),
                ('OWNER', 'tags.read'),
                ('OWNER', 'tags.update'),
                ('OWNER', 'tags.delete'),

                -- ADMIN
                ('ADMIN', 'workspace.read'),

                ('ADMIN', 'members.read'),
                ('ADMIN', 'members.invite'),

                ('ADMIN', 'tasks.create'),
                ('ADMIN', 'tasks.read'),
                ('ADMIN', 'tasks.update'),
                ('ADMIN', 'tasks.delete'),
                ('ADMIN', 'tasks.assign'),

                ('ADMIN', 'comments.create'),
                ('ADMIN', 'comments.read'),
                ('ADMIN', 'comments.update'),
                ('ADMIN', 'comments.delete'),

                ('ADMIN', 'tags.create'),
                ('ADMIN', 'tags.read'),
                ('ADMIN', 'tags.update'),
                ('ADMIN', 'tags.delete'),

                -- MEMBER
                ('MEMBER', 'workspace.read'),

                ('MEMBER', 'tasks.create'),
                ('MEMBER', 'tasks.read'),
                ('MEMBER', 'tasks.update'),

                ('MEMBER', 'comments.create'),
                ('MEMBER', 'comments.read')

        ) AS policy(role_key, permission_key)
        JOIN roles r
          ON r.role_key = policy.role_key
        JOIN permissions p
          ON p.permission_key = policy.permission_key;
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "This migration is forward-only. "
        "Restore the previous database backup to reverse it."
    )
