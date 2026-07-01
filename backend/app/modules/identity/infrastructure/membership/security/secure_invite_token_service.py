from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.infrastructure.authentication.security.token_utils import (
    generate_opaque_token,
    hash_opaque_token,
)


class SecureInviteTokenService:
    def generate(self) -> str:
        return generate_opaque_token()

    def hash(self, plain_token: str) -> InviteTokenHash:
        return InviteTokenHash(value=hash_opaque_token(plain_token))
