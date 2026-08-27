import base64
import hashlib
import hmac

from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.security.token_utils import (
    generate_opaque_token,
    hash_opaque_token,
)

_DERIVATION_CONTEXT = b"kyrox.identity-action-token.v1:"


class IdentityActionTokenService:
    def __init__(self, secret_key: str) -> None:
        normalized = secret_key.strip()
        if len(normalized) < 32:
            raise ValueError("Identity action token secret must be at least 32 characters")
        self._secret_key = normalized.encode("utf-8")

    def generate(self) -> str:
        return generate_opaque_token()

    def derive(self, token_id: IdentityActionTokenId) -> str:
        digest = hmac.new(
            self._secret_key,
            _DERIVATION_CONTEXT + token_id.value.bytes,
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def hash(self, raw_token: str) -> TokenHash:
        return TokenHash(hash_opaque_token(raw_token))
