import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base
from app.modules.registered_users.enums.registration_status import (
    RegistrationStatus,
)


class RegisteredUser(Base):
    __tablename__ = "registered_users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    cognito_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    registration_status: Mapped[RegistrationStatus] = mapped_column(
        SQLEnum(
            RegistrationStatus,
            name="registration_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=RegistrationStatus.PENDING,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )