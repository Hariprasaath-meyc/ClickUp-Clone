
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "task_id"],
            ["tasks.workspace_id", "tasks.id"],
            name="fk_task_assignees_workspace_task",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            [
                "workspace_members.workspace_id",
                "workspace_members.user_id",
            ],
            name="fk_task_assignees_workspace_member",
            ondelete="CASCADE",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
