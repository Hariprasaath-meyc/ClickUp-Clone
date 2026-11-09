"""add declined invitation status

Revision ID: ad51488c4707
Revises: fcef9fa59825
Create Date: 2026-11-04 10:01:30.560734

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad51488c4707"
down_revision: str | Sequence[str] | None = "fcef9fa59825"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE invitation_status ADD VALUE IF NOT EXISTS 'DECLINED'")


def downgrade() -> None:
    """Downgrade schema."""
