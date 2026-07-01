from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class RefreshTokenService(Protocol):
    def create(self) -> RefreshToken: ...

    def hash(self, token: RefreshToken) -> TokenHash: ...

    def verify(self, token: RefreshToken, token_hash: TokenHash) -> bool: ...
