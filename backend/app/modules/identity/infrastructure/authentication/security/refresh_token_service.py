import secrets

from app.modules.identity.domain.authentication.ports.refresh_token_service import RefreshTokenService
from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.security.token_utils import (
    generate_opaque_token,
    hash_opaque_token,
)


class RefreshTokenService:
    def create(self) -> RefreshToken:
        return RefreshToken.create(generate_opaque_token())

    def hash(self, token: RefreshToken) -> TokenHash:
        return TokenHash(hash_opaque_token(token.value))

    def verify(self, token: RefreshToken, token_hash: TokenHash) -> bool:
        computed = hash_opaque_token(token.value)
        return secrets.compare_digest(computed, token_hash.value)
