from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class IdentityActionTokenService(Protocol):
    def generate(self) -> str: ...

    def hash(self, raw_token: str) -> TokenHash: ...
