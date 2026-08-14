from dataclasses import dataclass

from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.membership.mappers import to_membership_result
from app.modules.identity.application.membership.results import MembershipResult
from app.modules.identity.application.membership.role_assignment import MembershipRoleAssigner
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class CreateOrganizationUserError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CreateOrganizationUserCommand:
    organization_id: OrganizationId
    created_by_user_id: UserId
    email: str
    temporary_password: str
    role_slug: str | None = None


@dataclass(frozen=True, slots=True)
class CreateOrganizationUserResult:
    user_id: UserId
    email: str
    must_change_password: bool
    membership: MembershipResult


class CreateOrganizationUserUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        membership_repository: MembershipRepository,
        role_assigner: MembershipRoleAssigner,
        password_hasher: PasswordHasher,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._organization_repository = organization_repository
        self._user_repository = user_repository
        self._membership_repository = membership_repository
        self._role_assigner = role_assigner
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, command: CreateOrganizationUserCommand) -> CreateOrganizationUserResult:
        if self._organization_repository.get_by_id(command.organization_id) is None:
            raise CreateOrganizationUserError("Organization not found")

        email = Email.create(command.email)
        if self._user_repository.get_by_email(email) is not None:
            raise CreateOrganizationUserError("User already exists")

        now = self._clock.now()
        user = self._user_repository.add(
            User(
                id=UserId(self._id_generator.generate_uuid()),
                email=email,
                password_hash=self._password_hasher.hash(command.temporary_password),
                status=UserStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                must_change_password=True,
            )
        )

        membership = self._membership_repository.add(
            Membership(
                id=MembershipId(self._id_generator.generate_uuid()),
                user_id=user.id,
                organization_id=command.organization_id,
                status=MembershipStatus.ACTIVE,
                invited_at=None,
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
        )

        if command.role_slug:
            self._role_assigner.assign_role(
                user_id=user.id,
                organization_id=command.organization_id,
                role_slug=RoleSlug.create(command.role_slug),
                assigned_by=command.created_by_user_id,
            )
        else:
            self._role_assigner.assign_default_member_role(
                user_id=user.id,
                organization_id=command.organization_id,
                assigned_by=command.created_by_user_id,
            )

        return CreateOrganizationUserResult(
            user_id=user.id,
            email=user.email.value,
            must_change_password=user.must_change_password,
            membership=to_membership_result(membership),
        )
