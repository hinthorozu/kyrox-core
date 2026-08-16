from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.organization.commands import CreateOrganizationCommand
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import CreateOrganizationResult
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
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
        clock: Clock,
        id_generator: IdGenerator,
        naming_policy: OrganizationNamingPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._clock = clock
        self._id_generator = id_generator
        self._naming_policy = naming_policy or OrganizationNamingPolicy()

    def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationResult:
        # The creator is a platform Super Admin (enforced by the API guard).
        # Validate the platform user, but never create an organization-scoped
        # user-role assignment for Super Admin. Platform access comes only from
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

        return CreateOrganizationResult(
            organization=to_organization_result(organization),
        )
