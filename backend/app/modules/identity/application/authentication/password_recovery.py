from dataclasses import dataclass, field
from datetime import UTC, timedelta
from typing import Protocol
from uuid import UUID

from app.modules.identity.application.authentication.identity_action_tokens import (
    ConsumeIdentityActionToken,
    IssueIdentityActionToken,
)
from app.modules.identity.application.authentication.password_policy import (
    DEFAULT_PASSWORD_POLICY,
    PasswordPolicy,
    PasswordPolicyViolation,
)
from app.modules.identity.application.authentication.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions.authentication import (
    InvalidPasswordResetTokenError,
    PasswordResetPolicyError,
)
from app.modules.identity.domain.authentication.exceptions.identity_action_token import (
    IdentityActionTokenError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.identity_action_token_repository import (
    IdentityActionTokenRepository,
)
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.ports.organization_repository import (
    OrganizationRepository,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)


class PasswordResetNotificationPort(Protocol):
    def enqueue_password_reset(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> bool: ...


class PasswordResetAuditPort(Protocol):
    def record_password_reset(
        self,
        *,
        organization_id: UUID | None,
        user_id: UUID,
        sessions_revoked: int,
        refresh_tokens_revoked: int,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ForgotPasswordCommand:
    email: str


@dataclass(frozen=True, slots=True)
class ForgotPasswordResult:
    notification_queued: bool


@dataclass(frozen=True, slots=True)
class ResetPasswordCommand:
    token: str = field(repr=False)
    password: str = field(repr=False)


class ForgotPasswordUseCase:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        identity_action_token_repository: IdentityActionTokenRepository,
        issue_identity_action_token: IssueIdentityActionToken,
        notification_port: PasswordResetNotificationPort,
        clock: Clock,
        token_ttl: timedelta,
        resend_cooldown: timedelta,
    ) -> None:
        self._user_repository = user_repository
        self._organization_repository = organization_repository
        self._identity_action_token_repository = identity_action_token_repository
        self._issue_identity_action_token = issue_identity_action_token
        self._notification_port = notification_port
        self._clock = clock
        self._token_ttl = token_ttl
        self._resend_cooldown = resend_cooldown

    def execute(self, command: ForgotPasswordCommand) -> ForgotPasswordResult:
        try:
            email = Email.create(command.email)
        except ValueError:
            return ForgotPasswordResult(notification_queued=False)

        user = self._user_repository.get_by_email(email)
        if not self._eligible_user(user):
            return ForgotPasswordResult(notification_queued=False)

        now = self._clock.now()
        latest = self._identity_action_token_repository.get_latest_for_user_purpose(
            user.id,
            IdentityActionTokenPurpose.PASSWORD_RESET,
        )
        if latest is not None:
            created_at = latest.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
            if now - created_at < self._resend_cooldown:
                return ForgotPasswordResult(notification_queued=False)

        issued = self._issue_identity_action_token.execute(
            user.id,
            IdentityActionTokenPurpose.PASSWORD_RESET,
            self._token_ttl,
            reconstructable=True,
        )
        queued = self._notification_port.enqueue_password_reset(
            recipient=user.email.value,
            user_id=user.id,
            token_id=issued.token_id,
        )
        if not queued:
            self._identity_action_token_repository.invalidate_outstanding_for_user_purpose(
                user.id,
                IdentityActionTokenPurpose.PASSWORD_RESET,
                now,
            )
        return ForgotPasswordResult(notification_queued=queued)

    def _eligible_user(self, user: object | None) -> bool:
        if user is None:
            return False
        if user.is_deleted or user.status is not UserStatus.ACTIVE or user.password_hash is None:
            return False
        if user.organization_id is None:
            return bool(user.is_super_admin)
        organization = self._organization_repository.get_by_id(
            OrganizationId(user.organization_id)
        )
        return bool(
            organization is not None
            and not organization.is_deleted()
            and organization.status is OrganizationStatus.ACTIVE
        )


class ResetPasswordUseCase:
    def __init__(
        self,
        *,
        consume_identity_action_token: ConsumeIdentityActionToken,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        password_hasher: PasswordHasher,
        revoke_all_user_sessions: RevokeAllUserSessionsUseCase,
        clock: Clock,
        audit_port: PasswordResetAuditPort,
        password_policy: PasswordPolicy | None = None,
    ) -> None:
        self._consume_identity_action_token = consume_identity_action_token
        self._user_repository = user_repository
        self._organization_repository = organization_repository
        self._password_hasher = password_hasher
        self._revoke_all_user_sessions = revoke_all_user_sessions
        self._clock = clock
        self._audit_port = audit_port
        self._password_policy = password_policy or DEFAULT_PASSWORD_POLICY

    def execute(self, command: ResetPasswordCommand) -> None:
        try:
            self._password_policy.validate(command.password)
        except PasswordPolicyViolation as exc:
            raise PasswordResetPolicyError(
                "Password does not satisfy the Core password policy"
            ) from exc

        try:
            user_id = self._consume_identity_action_token.execute(
                command.token,
                IdentityActionTokenPurpose.PASSWORD_RESET,
            )
        except IdentityActionTokenError as exc:
            raise InvalidPasswordResetTokenError(
                "Invalid or expired password reset token"
            ) from exc

        user = self._user_repository.get_by_id(user_id)
        if not self._eligible_user(user):
            raise InvalidPasswordResetTokenError(
                "Invalid or expired password reset token"
            )

        now = self._clock.now()
        user.password_hash = self._password_hasher.hash(command.password)
        user.updated_at = now
        self._user_repository.update(user)

        revoked = self._revoke_all_user_sessions.execute(user.id)
        self._audit_port.record_password_reset(
            organization_id=user.organization_id,
            user_id=user.id.value,
            sessions_revoked=revoked.sessions_revoked,
            refresh_tokens_revoked=revoked.refresh_tokens_revoked,
        )

    def _eligible_user(self, user: object | None) -> bool:
        if user is None:
            return False
        if user.is_deleted or user.status is not UserStatus.ACTIVE or user.password_hash is None:
            return False
        if user.organization_id is None:
            return bool(user.is_super_admin)
        organization = self._organization_repository.get_by_id(
            OrganizationId(user.organization_id)
        )
        return bool(
            organization is not None
            and not organization.is_deleted()
            and organization.status is OrganizationStatus.ACTIVE
        )
