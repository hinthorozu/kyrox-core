from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.exceptions.identity_action_token import (
    IdentityActionTokenConsumedError,
    IdentityActionTokenExpiredError,
    IdentityActionTokenInvalidatedError,
    IdentityActionTokenPurposeMismatchError,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


@dataclass(slots=True)
class IdentityActionToken:
    id: IdentityActionTokenId
    user_id: UserId
    purpose: IdentityActionTokenPurpose
    token_hash: TokenHash
    expires_at: datetime
    created_at: datetime
    consumed_at: datetime | None = None
    invalidated_at: datetime | None = None

    def is_available(self, now: datetime) -> bool:
        return (
            self.consumed_at is None
            and self.invalidated_at is None
            and now < self.expires_at
        )

    def invalidate(self, now: datetime) -> None:
        if self.consumed_at is None and self.invalidated_at is None:
            self.invalidated_at = now

    def consume(
        self,
        now: datetime,
        expected_purpose: IdentityActionTokenPurpose,
    ) -> None:
        if self.purpose is not expected_purpose:
            raise IdentityActionTokenPurposeMismatchError("Identity action token purpose mismatch")
        if self.invalidated_at is not None:
            raise IdentityActionTokenInvalidatedError("Identity action token is invalidated")
        if self.consumed_at is not None:
            raise IdentityActionTokenConsumedError("Identity action token was already consumed")
        if now >= self.expires_at:
            raise IdentityActionTokenExpiredError("Identity action token has expired")
        self.consumed_at = now
