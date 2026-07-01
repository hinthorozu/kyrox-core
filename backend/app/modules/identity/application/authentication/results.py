from dataclasses import dataclass

from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessToken
from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken as RefreshTokenValue,
)


@dataclass(frozen=True, slots=True)
class AuthTokenPairResult:
    access_token: AccessToken
    refresh_token: RefreshTokenValue
    token_type: str
    expires_in: int
