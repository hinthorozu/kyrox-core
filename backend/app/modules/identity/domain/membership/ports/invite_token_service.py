from typing import Protocol

from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash


class InviteTokenService(Protocol):
    def generate(self) -> str: ...

    def hash(self, plain_token: str) -> InviteTokenHash: ...
