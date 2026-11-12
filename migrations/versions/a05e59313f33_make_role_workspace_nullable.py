"""make role workspace nullable

Revision ID: a05e59313f33
Revises: d0155519481f
Create Date: 2026-11-12 12:45:28.756742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a05e59313f33'
down_revision: Union[str, Sequence[str], None] = 'd0155519481f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "roles",
        "workspace_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "roles",
        "workspace_id",
        existing_type=sa.UUID(),
        nullable=False,
    )