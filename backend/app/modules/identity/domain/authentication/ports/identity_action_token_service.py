from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class IdentityActionTokenService(Protocol):
    def generate(self) -> str: ...

    def derive(self, token_id: IdentityActionTokenId) -> str: ...

    def hash(self, raw_token: str) -> TokenHash: ...
