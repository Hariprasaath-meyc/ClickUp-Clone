from enum import StrEnum


class InvitationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"