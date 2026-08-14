from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.organization.commands import CreateOrganizationCommand
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import CreateOrganizationResult
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.ports.organization_role_repository import (
    OrganizationRoleRepository,
)
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId as AuthorizationOrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.exceptions import DuplicateOrganizationSlugError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class CreateOrganizationUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        organization_role_repository: OrganizationRoleRepository,
        clock: Clock,
        id_generator: IdGenerator,
        naming_policy: OrganizationNamingPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._organization_role_repository = organization_role_repository
        self._clock = clock
        self._id_generator = id_generator
        self._naming_policy = naming_policy or OrganizationNamingPolicy()

    def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationResult:
        # The creator is a platform Super Admin (enforced by the API guard).
        # Validate the platform user, but never create an organization membership
        # or user-role assignment for Super Admin. Platform access comes only from
        # identity_users.is_super_admin.
        creator = self._user_repository.get_by_id(command.owner_user_id)
        if creator is None:
            raise InactiveUserError("Creator user not found")
        creator.assert_can_authenticate()

        name = self._naming_policy.normalize_name(command.name)
        organization_id = OrganizationId(self._id_generator.generate_uuid())
        raw_slug = command.slug or f"org-{organization_id.value.hex[:12]}"
        slug = self._naming_policy.normalize_slug(raw_slug)
        if self._organization_repository.exists_by_slug(slug):
            raise DuplicateOrganizationSlugError(f"Organization slug already exists: {slug.value}")

        now = self._clock.now()
        organization = Organization(
            id=organization_id,
            name=name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        organization = self._organization_repository.add(organization)

        # Organization-role bindings only make DB roles assignable inside this
        # organization. They grant nothing to the Super Admin creator and are not
        # authorization bypasses. Provision every active system organization role
        # generically so future system roles work without slug-specific code here.
        authorization_organization_id = AuthorizationOrganizationId(organization.id.value)
        for role in self._role_repository.list_system_roles():
            if role.scope is not RoleScope.ORGANIZATION or not role.is_active():
                continue
            existing = self._organization_role_repository.get_by_organization_and_role(
                authorization_organization_id,
                role.id,
            )
            if existing is not None:
                continue
            self._organization_role_repository.add(
                OrganizationRole(
                    id=OrganizationRoleId(self._id_generator.generate_uuid()),
                    organization_id=authorization_organization_id,
                    role_id=role.id,
                    status=AssignmentStatus.ACTIVE,
                    is_default=False,
                    created_at=now,
                    updated_at=now,
                    deleted_at=None,
                )
            )

        return CreateOrganizationResult(
            organization=to_organization_result(organization),
            membership_id=None,
        )
