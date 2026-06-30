import uuid
from datetime import UTC, datetime

from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from app.modules.identity.infrastructure.persistence.mappers import (
    membership_to_domain,
    membership_to_model,
    organization_to_domain,
    organization_to_model,
    user_to_domain,
    user_to_model,
)


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_user_mapper_roundtrip() -> None:
    entity = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="hashed",
        status=UserStatus.ACTIVE,
        is_super_admin=False,
        created_at=_now(),
        updated_at=_now(),
        deleted_at=None,
    )

    model = user_to_model(entity)
    restored = user_to_domain(model)

    assert restored == entity


def test_organization_mapper_roundtrip() -> None:
    entity = Organization(
        id=uuid.uuid4(),
        name="Acme Corp",
        slug="acme-corp",
        status=OrganizationStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
        deleted_at=None,
    )

    model = organization_to_model(entity)
    restored = organization_to_domain(model)

    assert restored == entity


def test_membership_mapper_roundtrip() -> None:
    entity = Membership(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        status=MembershipStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
        deleted_at=None,
    )

    model = membership_to_model(entity)
    restored = membership_to_domain(model)

    assert restored == entity
