"""Add user profiles and migrate display names."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bdf4f0cf79a1"
down_revision: Union[str, Sequence[str], None] = "7402578119a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the profile table.
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_user_profiles_user_id",
        ),
    )

    # 2. Copy existing display names into the new table.
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO user_profiles (
                id,
                user_id,
                display_name
            )
            SELECT
                gen_random_uuid(),
                id,
                display_name
            FROM users
            """
        )
    )

    # 3. Verify every existing user received a profile.
    missing_profiles = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM users u
            LEFT JOIN user_profiles p ON p.user_id = u.id
            WHERE p.id IS NULL
            """
        )
    ).scalar_one()

    if missing_profiles:
        raise RuntimeError(
            f"Migration aborted: {missing_profiles} users have no profile."
        )

    # 4. Remove the old column only after the data transfer succeeds.
    op.drop_column("users", "display_name")

    # 5. Add updated_at to users.
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Restore display_name on users.
    op.add_column(
        "users",
        sa.Column(
            "display_name",
            sa.String(100),
            nullable=True,
        ),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE users u
            SET display_name = p.display_name
            FROM user_profiles p
            WHERE p.user_id = u.id
            """
        )
    )

    # Restore the original NOT NULL constraint.
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.String(100),
        nullable=False,
    )

    op.drop_column("users", "updated_at")
    op.drop_table("user_profiles")