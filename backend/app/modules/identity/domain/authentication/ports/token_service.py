from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessToken,
    AccessTokenClaims,
)


class TokenService(Protocol):
    def create_access_token(self, claims: AccessTokenClaims) -> AccessToken: ...

    def decode_access_token(self, token: AccessToken) -> AccessTokenClaims: ...
