from enum import StrEnum


class RefreshTokenRevokeReason(StrEnum):
    LOGOUT = "logout"
    ROTATED = "rotated"
    REUSE_DETECTED = "reuse_detected"
    SESSION_REVOKED = "session_revoked"
    ORGANIZATION_SUSPENDED = "organization_suspended"
    EXPIRED = "expired"
    ADMIN = "admin"
