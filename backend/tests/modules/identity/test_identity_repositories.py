import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from app.modules.identity.infrastructure.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _sample_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="hashed",
        status=UserStatus.ACTIVE,
        is_super_admin=False,
        created_at=_now(),
        updated_at=_now(),
    )


def _sample_organization() -> Organization:
    return Organization(
        id=uuid.uuid4(),
        name="Acme Corp",
        slug="acme-corp",
        status=OrganizationStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )


def test_user_repository_crud_and_soft_delete(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = _sample_user()

    created = repo.create(user)
    db_session.commit()

    assert repo.get_by_id(created.id) == created
    assert repo.get_by_email("user@example.com") == created

    created.status = UserStatus.SUSPENDED
    created.updated_at = _now()
    updated = repo.update(created)
    db_session.commit()

    assert updated.status == UserStatus.SUSPENDED

    repo.soft_delete(updated.id)
    db_session.commit()

    assert repo.get_by_id(updated.id) is None
    assert repo.get_by_email("user@example.com") is None


def test_organization_repository_get_by_slug(db_session: Session) -> None:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = _sample_organization()

    created = repo.create(organization)
    db_session.commit()

    assert repo.get_by_slug("acme-corp") == created
    assert repo.get_by_id(created.id) == created


def test_membership_repository_list_and_lookup(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    membership_repo = SqlAlchemyMembershipRepository(db_session)

    user = user_repo.create(_sample_user())
    organization = org_repo.create(_sample_organization())
    db_session.commit()

    membership = Membership(
        id=uuid.uuid4(),
        user_id=user.id,
        organization_id=organization.id,
        status=MembershipStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )
    created = membership_repo.create(membership)
    db_session.commit()

    assert membership_repo.get_by_id(created.id) == created
    assert membership_repo.get_by_user_and_organization(user.id, organization.id) == created
    assert membership_repo.list_by_user_id(user.id) == [created]
    assert membership_repo.list_by_organization_id(organization.id) == [created]

    membership_repo.soft_delete(created.id)
    db_session.commit()

    assert membership_repo.get_by_id(created.id) is None
    assert membership_repo.list_by_user_id(user.id) == []
