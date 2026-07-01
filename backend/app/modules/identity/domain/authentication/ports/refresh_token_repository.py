from typing import Protocol

from app.modules.identity.domain.authentication.entities.refresh_token import RefreshToken
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import (
    RefreshTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class RefreshTokenRepository(Protocol):
    def add(self, refresh_token: RefreshToken) -> RefreshToken: ...

    def update(self, refresh_token: RefreshToken) -> RefreshToken: ...

    def remove(self, refresh_token_id: RefreshTokenId) -> None: ...

    def get_by_id(self, refresh_token_id: RefreshTokenId) -> RefreshToken | None: ...

    def get_by_token_hash(self, token_hash: TokenHash) -> RefreshToken | None: ...

    def get_active_by_session_id(self, session_id: SessionId) -> RefreshToken | None: ...
