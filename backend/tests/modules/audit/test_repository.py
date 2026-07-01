import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.infrastructure.persistence import models as audit_models  # noqa: F401
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.audit.infrastructure.repositories import SqlAlchemyAuditLogRepository


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


def _sample_audit_log() -> AuditLog:
    return AuditLog(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        action="identity.permission.granted",
        resource_type="permission",
        resource_id=str(uuid.uuid4()),
        old_values=None,
        new_values={"code": "core.user.read"},
        metadata={"source": "test"},
        ip_address="10.0.0.1",
        user_agent="pytest",
        created_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC),
    )


def test_repository_appends_audit_log(db_session: Session) -> None:
    repository = SqlAlchemyAuditLogRepository(db_session)
    entity = _sample_audit_log()

    stored = repository.append(entity)
    db_session.commit()

    assert stored.id == entity.id
    assert stored.action == "identity.permission.granted"
    assert stored.metadata == {"source": "test"}

    row = db_session.scalars(select(AuditLogModel).where(AuditLogModel.id == entity.id)).one()
    assert row.action == "identity.permission.granted"
    assert row.event_metadata == {"source": "test"}


def test_repository_is_append_only(db_session: Session) -> None:
    repository = SqlAlchemyAuditLogRepository(db_session)

    assert hasattr(repository, "append")
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")
    assert not hasattr(repository, "soft_delete")
