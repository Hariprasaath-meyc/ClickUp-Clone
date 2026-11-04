"""add declined invitation status

Revision ID: ad51488c4707
Revises: fcef9fa59825
Create Date: 2026-11-04 10:01:30.560734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad51488c4707'
down_revision: Union[str, Sequence[str], None] = 'fcef9fa59825'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
     op.execute(
        "ALTER TYPE invitation_status ADD VALUE IF NOT EXISTS 'DECLINED'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
