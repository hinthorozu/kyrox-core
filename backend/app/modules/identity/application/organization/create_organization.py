from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.organization.commands import CreateOrganizationCommand
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import CreateOrganizationResult
from app.modules.identity.application.membership.role_assignment import MembershipRoleAssigner
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.exceptions import DuplicateOrganizationSlugError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class CreateOrganizationUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        membership_repository: MembershipRepository,
        user_repository: UserRepository,
        role_assigner: MembershipRoleAssigner,
        clock: Clock,
        id_generator: IdGenerator,
        naming_policy: OrganizationNamingPolicy | None = None,
        owner_role_slug: RoleSlug | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._membership_repository = membership_repository
        self._user_repository = user_repository
        self._role_assigner = role_assigner
        self._clock = clock
        self._id_generator = id_generator
        self._naming_policy = naming_policy or OrganizationNamingPolicy()
        self._owner_role_slug = owner_role_slug or RoleSlug.create("owner")

    def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationResult:
        owner = self._user_repository.get_by_id(command.owner_user_id)
        if owner is None:
            raise InactiveUserError("Owner user not found")
        owner.assert_can_authenticate()

        name = self._naming_policy.normalize_name(command.name)
        slug = self._naming_policy.normalize_slug(command.slug)
        if self._organization_repository.exists_by_slug(slug):
            raise DuplicateOrganizationSlugError(f"Organization slug already exists: {slug.value}")

        now = self._clock.now()
        organization = Organization(
            id=OrganizationId(self._id_generator.generate_uuid()),
            name=name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        organization = self._organization_repository.add(organization)

        membership = Membership(
            id=MembershipId(self._id_generator.generate_uuid()),
            user_id=command.owner_user_id,
            organization_id=organization.id,
            status=MembershipStatus.ACTIVE,
            invited_at=None,
            joined_at=now,
            created_at=now,
            updated_at=now,
        )
        membership = self._membership_repository.add(membership)

        self._role_assigner.assign_role(
            user_id=command.owner_user_id,
            organization_id=organization.id,
            role_slug=self._owner_role_slug,
            assigned_by=command.owner_user_id,
        )

        return CreateOrganizationResult(
            organization=to_organization_result(organization),
            membership_id=membership.id,
        )
