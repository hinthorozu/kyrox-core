from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.modules.identity.application.authentication.password_policy import (
    DEFAULT_PASSWORD_POLICY,
    PasswordPolicy,
    PasswordPolicyViolation,
)
from app.modules.identity.application.authentication.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions.authentication import (
    InvalidCurrentPasswordError,
    PasswordChangePolicyError,
    PasswordChangeUnavailableError,
    SamePasswordError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


class PasswordChangeAuditPort(Protocol):
    def record_password_change(
        self,
        *,
        organization_id: UUID | None,
        user_id: UUID,
        sessions_revoked: int,
        refresh_tokens_revoked: int,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    user_id: UUID
    current_password: str = field(repr=False)
    new_password: str = field(repr=False)


class ChangePasswordUseCase:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        revoke_all_user_sessions: RevokeAllUserSessionsUseCase,
        clock: Clock,
        audit_port: PasswordChangeAuditPort,
        password_policy: PasswordPolicy | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._revoke_all_user_sessions = revoke_all_user_sessions
        self._clock = clock
        self._audit_port = audit_port
        self._password_policy = password_policy or DEFAULT_PASSWORD_POLICY

    def execute(self, command: ChangePasswordCommand) -> None:
        user = self._user_repository.get_by_id(UserId(command.user_id))
        if (
            user is None
            or user.is_deleted
            or user.status is not UserStatus.ACTIVE
            or user.password_hash is None
        ):
            raise PasswordChangeUnavailableError("Password change is unavailable")

        if not self._password_hasher.verify(command.current_password, user.password_hash):
            raise InvalidCurrentPasswordError("Current password is incorrect")

        try:
            self._password_policy.validate(command.new_password)
        except PasswordPolicyViolation as exc:
            raise PasswordChangePolicyError(
                "Password does not satisfy the Core password policy"
            ) from exc

        if self._password_hasher.verify(command.new_password, user.password_hash):
            raise SamePasswordError("New password must differ from the current password")

        now = self._clock.now()
        user.password_hash = self._password_hasher.hash(command.new_password)
        user.updated_at = now
        self._user_repository.update(user)

        revoked = self._revoke_all_user_sessions.execute(user.id)
        self._audit_port.record_password_change(
            organization_id=user.organization_id,
            user_id=user.id.value,
            sessions_revoked=revoked.sessions_revoked,
            refresh_tokens_revoked=revoked.refresh_tokens_revoked,
        )
