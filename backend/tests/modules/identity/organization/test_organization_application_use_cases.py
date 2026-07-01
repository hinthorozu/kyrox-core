import uuid
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.membership.accept_membership_invite import AcceptMembershipInviteUseCase
from app.modules.identity.application.membership.commands import (
    AcceptMembershipInviteCommand,
    InviteMemberCommand,
    ListOrganizationMembershipsCommand,
    RemoveMembershipCommand,
    SuspendMembershipCommand,
)
from app.modules.identity.application.membership.invite_member import InviteMemberUseCase
from app.modules.identity.application.membership.invite_token_issuer import InviteTokenIssuer
from app.modules.identity.application.membership.list_organization_memberships import (
    ListOrganizationMembershipsUseCase,
)
from app.modules.identity.application.membership.role_assignment import MembershipRoleAssigner
from app.modules.identity.application.membership.suspend_membership import (
    RemoveMembershipUseCase,
    SuspendMembershipUseCase,
)
from app.modules.identity.application.organization.commands import CreateOrganizationCommand
from app.modules.identity.application.organization.create_organization import CreateOrganizationUseCase
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import PasswordHash
from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.exceptions import DuplicateMembershipError
from app.modules.identity.domain.membership.ports.invite_token_service import InviteTokenService
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.exceptions import DuplicateOrganizationSlugError
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from organization_application_test_helpers import (
    FixedClock,
    InMemoryMembershipInviteRepository,
    InMemoryMembershipRepository,
    InMemoryOrganizationRepository,
    InMemoryOrganizationRoleRepository,
    InMemoryRoleRepository,
    InMemoryUserRepository,
    InMemoryUserRoleRepository,
    SequenceIdGenerator,
)


class FakeInviteTokenService:
    def __init__(self) -> None:
        self._counter = 0

    def generate(self) -> str:
        self._counter += 1
        return f"invite-token-{self._counter}"

    def hash(self, plain_token: str) -> InviteTokenHash:
        return InviteTokenHash(f"hash:{plain_token}")


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _seed_owner(now: datetime) -> tuple[User, UserId]:
    owner_id = UserId(uuid.uuid4())
    owner = User(
        id=owner_id,
        email=Email.create("owner@example.com"),
        password_hash=PasswordHash("hash"),
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    return owner, owner_id


def _seed_roles(role_repo: InMemoryRoleRepository, now: datetime) -> None:
    for slug in ("owner", "member"):
        role_repo.add(
            Role(
                id=RoleId(uuid.uuid4()),
                name=slug.title(),
                slug=RoleSlug.create(slug),
                scope=RoleScope.ORGANIZATION,
                is_system=True,
                created_at=now,
                updated_at=now,
            )
        )


def _build_role_assigner(
    *,
    role_repo: InMemoryRoleRepository,
    org_role_repo: InMemoryOrganizationRoleRepository,
    user_role_repo: InMemoryUserRoleRepository,
    clock: FixedClock,
    id_generator: SequenceIdGenerator,
) -> MembershipRoleAssigner:
    return MembershipRoleAssigner(
        role_repository=role_repo,
        organization_role_repository=org_role_repo,
        user_role_repository=user_role_repo,
        clock=clock,
        id_generator=id_generator,
    )


def test_create_organization_use_case_creates_org_membership_and_owner_role() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    user_repo = InMemoryUserRepository([owner])
    org_repo = InMemoryOrganizationRepository()
    membership_repo = InMemoryMembershipRepository()
    role_repo = InMemoryRoleRepository()
    org_role_repo = InMemoryOrganizationRoleRepository()
    user_role_repo = InMemoryUserRoleRepository()
    _seed_roles(role_repo, now)

    use_case = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=_build_role_assigner(
            role_repo=role_repo,
            org_role_repo=org_role_repo,
            user_role_repo=user_role_repo,
            clock=clock,
            id_generator=ids,
        ),
        clock=clock,
        id_generator=ids,
    )

    result = use_case.execute(
        CreateOrganizationCommand(
            owner_user_id=owner_id,
            name="Acme Corp",
            slug="acme-corp",
        )
    )

    assert result.organization.name == "Acme Corp"
    assert result.organization.slug == "acme-corp"
    assert result.organization.status is OrganizationStatus.ACTIVE
    assert len(membership_repo.items) == 1
    assert membership_repo.items[0].status is MembershipStatus.ACTIVE
    assert len(user_role_repo.items) == 1


def test_create_organization_rejects_duplicate_slug() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    org_repo = InMemoryOrganizationRepository()
    org_repo.add_slug(OrganizationSlug.create("acme-corp"))

    use_case = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=InMemoryMembershipRepository(),
        user_repository=InMemoryUserRepository([owner]),
        role_assigner=_build_role_assigner(
            role_repo=InMemoryRoleRepository(),
            org_role_repo=InMemoryOrganizationRoleRepository(),
            user_role_repo=InMemoryUserRoleRepository(),
            clock=clock,
            id_generator=ids,
        ),
        clock=clock,
        id_generator=ids,
    )

    with pytest.raises(DuplicateOrganizationSlugError):
        use_case.execute(
            CreateOrganizationCommand(
                owner_user_id=owner_id,
                name="Acme",
                slug="acme-corp",
            )
        )


def test_invite_and_accept_membership_flow() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4() for _ in range(10)])
    owner, owner_id = _seed_owner(now)
    invitee_id = UserId(uuid.uuid4())
    invitee = User(
        id=invitee_id,
        email=Email.create("member@example.com"),
        password_hash=PasswordHash("hash"),
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    user_repo = InMemoryUserRepository([owner, invitee])
    org_repo = InMemoryOrganizationRepository()
    membership_repo = InMemoryMembershipRepository()
    invite_repo = InMemoryMembershipInviteRepository()
    role_repo = InMemoryRoleRepository()
    org_role_repo = InMemoryOrganizationRoleRepository()
    user_role_repo = InMemoryUserRoleRepository()
    _seed_roles(role_repo, now)
    role_assigner = _build_role_assigner(
        role_repo=role_repo,
        org_role_repo=org_role_repo,
        user_role_repo=user_role_repo,
        clock=clock,
        id_generator=ids,
    )
    invite_token_service = FakeInviteTokenService()
    invite_token_issuer = InviteTokenIssuer(invite_token_service)

    create_org = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=role_assigner,
        clock=clock,
        id_generator=ids,
    )
    org_result = create_org.execute(
        CreateOrganizationCommand(
            owner_user_id=owner_id,
            name="Acme",
            slug="acme",
        )
    )

    invite_use_case = InviteMemberUseCase(
        organization_repository=org_repo,
        membership_invite_repository=invite_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        invite_token_issuer=invite_token_issuer,
        clock=clock,
        id_generator=ids,
    )
    invite_result = invite_use_case.execute(
        InviteMemberCommand(
            organization_id=org_result.organization.organization_id,
            invited_by_user_id=owner_id,
            email="member@example.com",
        )
    )

    accept_use_case = AcceptMembershipInviteUseCase(
        membership_invite_repository=invite_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=role_assigner,
        invite_token_issuer=invite_token_issuer,
        clock=clock,
        id_generator=ids,
    )
    accept_result = accept_use_case.execute(
        AcceptMembershipInviteCommand(
            plain_token=invite_result.plain_token,
            accepting_user_id=invitee_id,
        )
    )

    assert accept_result.membership.status is MembershipStatus.ACTIVE
    assert accept_result.organization_id == org_result.organization.organization_id
    assert len(user_role_repo.items) == 2


def test_list_organization_memberships_returns_created_members() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    user_repo = InMemoryUserRepository([owner])
    org_repo = InMemoryOrganizationRepository()
    membership_repo = InMemoryMembershipRepository()
    role_repo = InMemoryRoleRepository()
    _seed_roles(role_repo, now)

    create_org = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=_build_role_assigner(
            role_repo=role_repo,
            org_role_repo=InMemoryOrganizationRoleRepository(),
            user_role_repo=InMemoryUserRoleRepository(),
            clock=clock,
            id_generator=ids,
        ),
        clock=clock,
        id_generator=ids,
    )
    org_result = create_org.execute(
        CreateOrganizationCommand(owner_user_id=owner_id, name="Acme", slug="acme")
    )

    list_use_case = ListOrganizationMembershipsUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
    )
    listed = list_use_case.execute(
        ListOrganizationMembershipsCommand(
            organization_id=org_result.organization.organization_id
        )
    )

    assert len(listed.memberships) == 1
    assert listed.memberships[0].user_id == owner_id


def test_invite_member_rejects_duplicate_pending_invite() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    user_repo = InMemoryUserRepository([owner])
    org_repo = InMemoryOrganizationRepository()
    membership_repo = InMemoryMembershipRepository()
    invite_repo = InMemoryMembershipInviteRepository()
    invite_token_issuer = InviteTokenIssuer(FakeInviteTokenService())
    role_repo = InMemoryRoleRepository()
    _seed_roles(role_repo, now)

    create_org = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=_build_role_assigner(
            role_repo=role_repo,
            org_role_repo=InMemoryOrganizationRoleRepository(),
            user_role_repo=InMemoryUserRoleRepository(),
            clock=clock,
            id_generator=ids,
        ),
        clock=clock,
        id_generator=ids,
    )
    org_result = create_org.execute(
        CreateOrganizationCommand(owner_user_id=owner_id, name="Acme", slug="acme")
    )

    invite_use_case = InviteMemberUseCase(
        organization_repository=org_repo,
        membership_invite_repository=invite_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        invite_token_issuer=invite_token_issuer,
        clock=clock,
        id_generator=ids,
    )
    invite_use_case.execute(
        InviteMemberCommand(
            organization_id=org_result.organization.organization_id,
            invited_by_user_id=owner_id,
            email="member@example.com",
        )
    )

    with pytest.raises(DuplicateMembershipError):
        invite_use_case.execute(
            InviteMemberCommand(
                organization_id=org_result.organization.organization_id,
                invited_by_user_id=owner_id,
                email="member@example.com",
            )
        )


def test_suspend_and_remove_membership() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    user_repo = InMemoryUserRepository([owner])
    org_repo = InMemoryOrganizationRepository()
    membership_repo = InMemoryMembershipRepository()
    role_repo = InMemoryRoleRepository()
    _seed_roles(role_repo, now)

    create_org = CreateOrganizationUseCase(
        organization_repository=org_repo,
        membership_repository=membership_repo,
        user_repository=user_repo,
        role_assigner=_build_role_assigner(
            role_repo=role_repo,
            org_role_repo=InMemoryOrganizationRoleRepository(),
            user_role_repo=InMemoryUserRoleRepository(),
            clock=clock,
            id_generator=ids,
        ),
        clock=clock,
        id_generator=ids,
    )
    org_result = create_org.execute(
        CreateOrganizationCommand(owner_user_id=owner_id, name="Acme", slug="acme")
    )
    membership_id = org_result.membership_id

    suspend_use_case = SuspendMembershipUseCase(membership_repository=membership_repo, clock=clock)
    suspended = suspend_use_case.execute(SuspendMembershipCommand(membership_id=membership_id))
    assert suspended.status is MembershipStatus.SUSPENDED

    remove_use_case = RemoveMembershipUseCase(membership_repository=membership_repo, clock=clock)
    removed = remove_use_case.execute(RemoveMembershipCommand(membership_id=membership_id))
    assert removed.status is MembershipStatus.REMOVED
