from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.identity.application.authentication.identity_action_tokens import (
    ConsumeIdentityActionToken,
)
from app.modules.identity.application.authentication.password_policy import (
    DEFAULT_PASSWORD_POLICY,
    PasswordPolicy,
    PasswordPolicyViolation,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions.authentication import (
    ActivationPasswordPolicyError,
    InvalidActivationTokenError,
)
from app.modules.identity.domain.authentication.exceptions.identity_action_token import (
    IdentityActionTokenError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.ports.organization_repository import (
    OrganizationRepository,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)


class ActivationAuditPort(Protocol):
    def record_activation(self, *, organization_id: UUID, user_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class CompleteActivationCommand:
    token: str
    password: str


@dataclass(frozen=True, slots=True)
class CompleteActivationResult:
    organization_id: UUID
    user_id: UUID


class CompleteActivationUseCase:
    def __init__(
        self,
        *,
        consume_identity_action_token: ConsumeIdentityActionToken,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
        audit_port: ActivationAuditPort,
        password_policy: PasswordPolicy | None = None,
    ) -> None:
        self._consume_identity_action_token = consume_identity_action_token
        self._user_repository = user_repository
        self._organization_repository = organization_repository
        self._password_hasher = password_hasher
        self._clock = clock
        self._audit_port = audit_port
        self._password_policy = password_policy or DEFAULT_PASSWORD_POLICY

    def execute(self, command: CompleteActivationCommand) -> CompleteActivationResult:
        try:
            self._password_policy.validate(command.password)
        except PasswordPolicyViolation as exc:
            raise ActivationPasswordPolicyError(
                "Password does not satisfy the Core password policy"
            ) from exc

        try:
            user_id = self._consume_identity_action_token.execute(
                command.token,
                IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
            )
        except IdentityActionTokenError as exc:
            raise InvalidActivationTokenError(
                "Invalid or expired activation token"
            ) from exc

        user = self._user_repository.get_by_id(user_id)
        if (
            user is None
            or user.is_deleted
            or user.status is not UserStatus.INACTIVE
            or user.password_hash is not None
            or user.organization_id is None
            or user.is_super_admin
        ):
            raise InvalidActivationTokenError("Invalid or expired activation token")

        organization = self._organization_repository.get_by_id(
            OrganizationId(user.organization_id)
        )
        if (
            organization is None
            or organization.is_deleted()
            or organization.status is not OrganizationStatus.PENDING_ACTIVATION
        ):
            raise InvalidActivationTokenError("Invalid or expired activation token")

        now = self._clock.now()
        user.password_hash = self._password_hasher.hash(command.password)
        user.status = UserStatus.ACTIVE
        user.updated_at = now
        organization.status = OrganizationStatus.ACTIVE
        organization.updated_at = now

        self._user_repository.update(user)
        self._organization_repository.update(organization)
        self._audit_port.record_activation(
            organization_id=organization.id.value,
            user_id=user.id.value,
        )

        return CompleteActivationResult(
            organization_id=organization.id.value,
            user_id=user.id.value,
        )
