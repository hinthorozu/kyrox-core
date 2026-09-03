import uuid
from datetime import UTC, datetime

import pytest

from app.modules.identity.application.organization.commands import (
    CreateOrganizationCommand,
    ReactivateOrganizationCommand,
)
from app.modules.identity.application.organization.create_organization import CreateOrganizationUseCase
from app.modules.identity.application.organization.reactivate_organization import ReactivateOrganizationUseCase
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import PasswordHash
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.exceptions import (
    DuplicateOrganizationSlugError,
    OrganizationNotFoundError,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug

from organization_application_test_helpers import (
    FixedClock,
    InMemoryOrganizationRepository,
    InMemoryRoleRepository,
    InMemoryUserRepository,
    SequenceIdGenerator,
)


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


def test_create_organization_use_case_creates_org_without_super_admin_membership() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    user_repo = InMemoryUserRepository([owner])
    org_repo = InMemoryOrganizationRepository()
    role_repo = InMemoryRoleRepository()

    use_case = CreateOrganizationUseCase(
        organization_repository=org_repo,
        user_repository=user_repo,
        role_repository=role_repo,
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


def test_create_organization_rejects_duplicate_slug() -> None:
    now = _now()
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid.uuid4()])
    owner, owner_id = _seed_owner(now)
    org_repo = InMemoryOrganizationRepository()
    org_repo.add_slug(OrganizationSlug.create("acme-corp"))

    use_case = CreateOrganizationUseCase(
        organization_repository=org_repo,
        user_repository=InMemoryUserRepository([owner]),
        role_repository=InMemoryRoleRepository(),
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


def test_reactivate_organization_use_case_transitions_suspended_to_active() -> None:
    now = _now()
    organization_id = OrganizationId(uuid.uuid4())
    organization = Organization(
        id=organization_id,
        name=OrganizationName.create("Acme"),
        slug=OrganizationSlug.create("acme"),
        status=OrganizationStatus.SUSPENDED,
        created_at=now,
        updated_at=now,
    )
    org_repo = InMemoryOrganizationRepository()
    org_repo.add(organization)
    use_case = ReactivateOrganizationUseCase(
        organization_repository=org_repo,
        clock=FixedClock(now),
    )

    result = use_case.execute(ReactivateOrganizationCommand(organization_id=organization_id))

    assert result.status is OrganizationStatus.ACTIVE
    persisted = org_repo.get_by_id(organization_id)
    assert persisted is not None
    assert persisted.status is OrganizationStatus.ACTIVE


def test_reactivate_organization_use_case_rejects_missing_organization() -> None:
    organization_id = OrganizationId(uuid.uuid4())
    use_case = ReactivateOrganizationUseCase(
        organization_repository=InMemoryOrganizationRepository(),
        clock=FixedClock(_now()),
    )

    with pytest.raises(OrganizationNotFoundError):
        use_case.execute(ReactivateOrganizationCommand(organization_id=organization_id))
