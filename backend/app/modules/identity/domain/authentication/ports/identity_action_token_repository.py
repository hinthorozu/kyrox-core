from datetime import datetime
from typing import Protocol

from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class IdentityActionTokenRepository(Protocol):
    def add(self, token: IdentityActionToken) -> IdentityActionToken: ...

    def update(self, token: IdentityActionToken) -> IdentityActionToken: ...

    def get_by_token_hash(self, token_hash: TokenHash) -> IdentityActionToken | None: ...

    def invalidate_outstanding_for_user_purpose(
        self,
        user_id: UserId,
        purpose: IdentityActionTokenPurpose,
        invalidated_at: datetime,
    ) -> int: ...
