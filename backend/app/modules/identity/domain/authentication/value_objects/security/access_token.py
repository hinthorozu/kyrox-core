from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    sub: UserId
    email: Email
    sid: SessionId
    exp: datetime
    iat: datetime
    jti: UUID


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str

    @classmethod
    def create(cls, raw: str) -> "AccessToken":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("Access token cannot be empty")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Access token cannot be empty")
