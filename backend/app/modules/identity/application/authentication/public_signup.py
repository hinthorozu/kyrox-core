from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from uuid import UUID

from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.authentication.identity_action_tokens import (
    IssueIdentityActionToken,
)
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions.authentication import (
    PublicSignupConflictError,
    PublicSignupProvisioningError,
    PublicSignupValidationError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
from app.modules.identity.domain.authorization.ports.user_role_repository import (
    UserRoleRepository,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId as AuthorizationOrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import (
    UserRoleId,
)
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.exceptions import OrganizationError
from app.modules.identity.domain.organization.ports.organization_repository import (
    OrganizationRepository,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)

# This protected system role predates the stricter RoleSlug.create() policy and
# is intentionally stored with an underscore by migration 20260815_0052.
_ORGANIZATION_ADMIN_ROLE_SLUG = "organization_admin"


class ActivationNotificationPort(Protocol):
    def enqueue_activation(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> UUID: ...


@dataclass(frozen=True, slots=True)
class PublicSignupCommand:
    organization_name: str
    email: str
    organization_slug: str | None = None


@dataclass(frozen=True, slots=True)
class PublicSignupResult:
    organization_id: UUID
    user_id: UUID
    activation_notification_id: UUID


class PublicSignupUseCase:
    def __init__(
        self,
        *,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
        issue_identity_action_token: IssueIdentityActionToken,
        activation_notification_port: ActivationNotificationPort,
        clock: Clock,
        id_generator: IdGenerator,
        activation_token_ttl: timedelta,
        naming_policy: OrganizationNamingPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository
        self._issue_identity_action_token = issue_identity_action_token
        self._activation_notification_port = activation_notification_port
        self._clock = clock
        self._id_generator = id_generator
        self._activation_token_ttl = activation_token_ttl
        self._naming_policy = naming_policy or OrganizationNamingPolicy()

    def execute(self, command: PublicSignupCommand) -> PublicSignupResult:
        try:
            email = Email.create(command.email)
        except ValueError as exc:
            raise PublicSignupValidationError("Invalid signup details") from exc

        if self._user_repository.get_by_email(email) is not None:
            raise PublicSignupConflictError(
                "An account with the supplied details already exists"
            )

        organization_id = OrganizationId(self._id_generator.generate_uuid())
        try:
            name = self._naming_policy.normalize_name(command.organization_name)
            raw_slug = command.organization_slug or f"org-{organization_id.value.hex[:12]}"
            slug = self._naming_policy.normalize_slug(raw_slug)
        except (OrganizationError, ValueError) as exc:
            raise PublicSignupValidationError("Invalid signup details") from exc

        if self._organization_repository.exists_by_slug(slug):
            raise PublicSignupConflictError(
                "An account with the supplied details already exists"
            )

        now = self._clock.now()
        organization = self._organization_repository.add(
            Organization(
                id=organization_id,
                name=name,
                slug=slug,
                status=OrganizationStatus.PENDING_ACTIVATION,
                created_at=now,
                updated_at=now,
            )
        )

        user_id = UserId(self._id_generator.generate_uuid())
        user = self._user_repository.add(
            User(
                id=user_id,
                email=email,
                password_hash=None,
                status=UserStatus.INACTIVE,
                created_at=now,
                updated_at=now,
                organization_id=organization.id.value,
                is_super_admin=False,
            )
        )

        organization_admin = self._role_repository.get_by_slug(
            RoleSlug(value=_ORGANIZATION_ADMIN_ROLE_SLUG),
            RoleScope.ORGANIZATION,
        )
        if (
            organization_admin is None
            or not organization_admin.is_active()
            or not organization_admin.is_assignable
            or not organization_admin.is_protected
        ):
            raise PublicSignupProvisioningError("Signup is temporarily unavailable")

        self._user_role_repository.add(
            UserRole(
                id=UserRoleId(self._id_generator.generate_uuid()),
                user_id=user.id,
                organization_id=AuthorizationOrganizationId(organization.id.value),
                role_id=organization_admin.id,
                status=AssignmentStatus.ACTIVE,
                assigned_at=now,
                assigned_by=None,
            )
        )

        issued = self._issue_identity_action_token.execute(
            user.id,
            IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
            self._activation_token_ttl,
            reconstructable=True,
        )
        activation_notification_id = (
            self._activation_notification_port.enqueue_activation(
                recipient=user.email.value,
                user_id=user.id,
                token_id=issued.token_id,
            )
        )
        return PublicSignupResult(
            organization_id=organization.id.value,
            user_id=user.id.value,
            activation_notification_id=activation_notification_id,
        )
