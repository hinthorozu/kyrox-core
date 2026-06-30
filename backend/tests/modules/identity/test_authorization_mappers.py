import uuid
from datetime import UTC, datetime

from app.modules.identity.domain.entities import Permission, Role, RolePermission
from app.modules.identity.infrastructure.persistence.mappers import (
    permission_to_domain,
    permission_to_model,
    role_permission_to_domain,
    role_permission_to_model,
    role_to_domain,
    role_to_model,
)


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_role_mapper_roundtrip() -> None:
    entity = Role(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Admin",
        slug="admin",
        is_system=True,
        created_at=_now(),
        updated_at=_now(),
    )

    restored = role_to_domain(role_to_model(entity))
    assert restored == entity


def test_permission_mapper_roundtrip() -> None:
    entity = Permission(
        id=uuid.uuid4(),
        code="core.user.read",
        description="Read users",
        module="core",
        is_system=True,
        created_at=_now(),
        updated_at=_now(),
    )

    restored = permission_to_domain(permission_to_model(entity))
    assert restored == entity


def test_role_permission_mapper_roundtrip() -> None:
    entity = RolePermission(role_id=uuid.uuid4(), permission_id=uuid.uuid4())

    restored = role_permission_to_domain(role_permission_to_model(entity))
    assert restored == entity
