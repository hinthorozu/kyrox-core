import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel
from app.modules.identity.infrastructure.organization.repositories.sqlalchemy_organization_repository import (
    SqlAlchemyOrganizationRepository,
)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[OrganizationModel.__table__])
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_sqlalchemy_organization_repository_add_update_remove(db_session: Session) -> None:
    clock = FixedClock(_now())
    repo = SqlAlchemyOrganizationRepository(db_session, clock)
    organization = Organization(
        id=OrganizationId(uuid.uuid4()),
        name=OrganizationName.create("Acme Corp"),
        slug=OrganizationSlug.create("acme-corp"),
        status=OrganizationStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )

    created = repo.add(organization)
    db_session.commit()
    assert repo.get_by_slug(OrganizationSlug.create("acme-corp")) is not None
    assert repo.exists_by_slug(OrganizationSlug.create("acme-corp")) is True

    created.suspend(_now())
    updated = repo.update(created)
    db_session.commit()
    assert updated.status is OrganizationStatus.SUSPENDED

    repo.remove(created.id)
    db_session.commit()
    assert repo.get_by_id(created.id) is None
    assert repo.exists_by_slug(OrganizationSlug.create("acme-corp")) is False
