from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.domain.authentication.ports.session_repository import SessionRepository


@dataclass(frozen=True, slots=True)
class RevokeOrganizationSessionsResult:
    sessions_revoked: int
    refresh_tokens_revoked: int


class RevokeOrganizationSessionsUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        clock: Clock,
    ) -> None:
        self._session_repository = session_repository
        self._refresh_token_repository = refresh_token_repository
        self._clock = clock

    def execute(self, organization_id: UUID) -> RevokeOrganizationSessionsResult:
        now = self._clock.now()
        refresh_tokens = self._refresh_token_repository.get_active_by_organization_id(
            organization_id
        )
        sessions = self._session_repository.get_active_by_organization_id(organization_id)

        for refresh_token in refresh_tokens:
            refresh_token.revoke(now, RefreshTokenRevokeReason.ORGANIZATION_SUSPENDED)
            self._refresh_token_repository.update(refresh_token)

        for session in sessions:
            session.revoke(now)
            self._session_repository.update(session)

        return RevokeOrganizationSessionsResult(
            sessions_revoked=len(sessions),
            refresh_tokens_revoked=len(refresh_tokens),
        )
