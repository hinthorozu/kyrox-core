from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.authorization.ports.organization_role_repository import (
    OrganizationRoleRepository,
)
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
from app.modules.identity.domain.authorization.ports.user_role_repository import UserRoleRepository
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import UserRoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug


class MembershipRoleAssigner:
    def __init__(
        self,
        role_repository: RoleRepository,
        organization_role_repository: OrganizationRoleRepository,
        user_role_repository: UserRoleRepository,
        clock: Clock,
        id_generator: IdGenerator,
        default_role_slug: RoleSlug | None = None,
    ) -> None:
        self._role_repository = role_repository
        self._organization_role_repository = organization_role_repository
        self._user_role_repository = user_role_repository
        self._clock = clock
        self._id_generator = id_generator
        self._default_role_slug = default_role_slug or RoleSlug.create("member")

    def assign_role(
        self,
        *,
        user_id: UserId,
        organization_id: OrganizationId,
        role_slug: RoleSlug | None = None,
        assigned_by: UserId | None = None,
    ) -> None:
        slug = role_slug or self._default_role_slug
        role = self._role_repository.get_by_slug(slug, RoleScope.ORGANIZATION)
        if role is None:
            raise InvalidRoleError(f"Role not found: {slug.value}")

        organization_role = self._organization_role_repository.get_by_organization_and_role(
            organization_id,
            role.id,
        )
        if organization_role is None:
            now = self._clock.now()
            organization_role = self._organization_role_repository.add(
                OrganizationRole(
                    id=OrganizationRoleId(self._id_generator.generate_uuid()),
                    organization_id=organization_id,
                    role_id=role.id,
                    status=AssignmentStatus.ACTIVE,
                    is_default=slug.value == self._default_role_slug.value,
                    created_at=now,
                    updated_at=now,
                )
            )

        now = self._clock.now()
        self._user_role_repository.add(
            UserRole(
                id=UserRoleId(self._id_generator.generate_uuid()),
                user_id=user_id,
                organization_id=organization_id,
                organization_role_id=organization_role.id,
                status=AssignmentStatus.ACTIVE,
                assigned_at=now,
                assigned_by=assigned_by,
            )
        )

    def assign_default_member_role(
        self,
        *,
        user_id: UserId,
        organization_id: OrganizationId,
        assigned_by: UserId | None = None,
    ) -> None:
        self.assign_role(
            user_id=user_id,
            organization_id=organization_id,
            role_slug=self._default_role_slug,
            assigned_by=assigned_by,
        )
