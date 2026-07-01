from app.modules.identity.domain.membership.ports.invite_token_service import InviteTokenService
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash


class InviteTokenIssuer:
    def __init__(self, invite_token_service: InviteTokenService) -> None:
        self._invite_token_service = invite_token_service

    def issue(self) -> tuple[InviteTokenHash, str]:
        plain_token = self._invite_token_service.generate()
        token_hash = self._invite_token_service.hash(plain_token)
        return token_hash, plain_token

    def hash_plain_token(self, plain_token: str) -> InviteTokenHash:
        return self._invite_token_service.hash(plain_token)
