from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.security.token_utils import (
    generate_opaque_token,
    hash_opaque_token,
)


class IdentityActionTokenService:
    def generate(self) -> str:
        return generate_opaque_token()

    def hash(self, raw_token: str) -> TokenHash:
        return TokenHash(hash_opaque_token(raw_token))
