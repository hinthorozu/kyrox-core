from dataclasses import dataclass

from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.domain.authentication.ports.session_repository import SessionRepository
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class RevokeAllUserSessionsResult:
    sessions_revoked: int
    refresh_tokens_revoked: int


class RevokeAllUserSessionsUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        clock: Clock,
    ) -> None:
        self._session_repository = session_repository
        self._refresh_token_repository = refresh_token_repository
        self._clock = clock

    def execute(self, user_id: UserId) -> RevokeAllUserSessionsResult:
        now = self._clock.now()
        refresh_tokens = self._refresh_token_repository.get_active_by_user_id(user_id)
        sessions = self._session_repository.get_active_by_user_id(user_id)

        for refresh_token in refresh_tokens:
            refresh_token.revoke(now, RefreshTokenRevokeReason.SESSION_REVOKED)
            self._refresh_token_repository.update(refresh_token)

        for session in sessions:
            session.revoke(now)
            self._session_repository.update(session)

        return RevokeAllUserSessionsResult(
            sessions_revoked=len(sessions),
            refresh_tokens_revoked=len(refresh_tokens),
        )
