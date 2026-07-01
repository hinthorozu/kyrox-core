from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.exceptions import (
    ExpiredRefreshTokenError,
    RevokedRefreshTokenError,
)
from app.modules.identity.domain.authentication.value_objects.client.ip_address import IpAddress
from app.modules.identity.domain.authentication.value_objects.client.user_agent import UserAgent
from app.modules.identity.domain.authentication.value_objects.identity.family_id import FamilyId
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import (
    RefreshTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


@dataclass
class RefreshToken:
    id: RefreshTokenId
    session_id: SessionId
    token_hash: TokenHash
    family_id: FamilyId
    expires_at: datetime
    created_at: datetime
    rotated_from: RefreshTokenId | None = None
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: RefreshTokenRevokeReason | None = None
    reuse_detected_at: datetime | None = None
    created_by_ip: IpAddress | None = None
    created_by_user_agent: UserAgent | None = None

    def is_expired(self, at: datetime) -> bool:
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        compare_at = at
        if compare_at.tzinfo is None:
            compare_at = compare_at.replace(tzinfo=UTC)
        return expires_at <= compare_at

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_used(self) -> bool:
        return self.used_at is not None

    def is_usable(self, at: datetime) -> bool:
        return not self.is_revoked() and not self.is_used() and not self.is_expired(at)

    def mark_used(self, at: datetime) -> None:
        self.used_at = at

    def revoke(self, at: datetime, reason: RefreshTokenRevokeReason) -> None:
        self.revoked_at = at
        self.revoked_reason = reason

    def mark_reuse_detected(self, at: datetime) -> None:
        self.reuse_detected_at = at
        self.revoke(at, RefreshTokenRevokeReason.REUSE_DETECTED)

    def assert_usable(self, at: datetime) -> None:
        if self.is_revoked():
            raise RevokedRefreshTokenError("Refresh token has been revoked")
        if self.is_used():
            raise RevokedRefreshTokenError("Refresh token has already been used")
        if self.is_expired(at):
            raise ExpiredRefreshTokenError("Refresh token has expired")
