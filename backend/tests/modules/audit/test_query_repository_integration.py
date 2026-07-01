import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter
from app.modules.audit.infrastructure.persistence import models as audit_models  # noqa: F401
from app.modules.audit.infrastructure.query_repository import SqlAlchemyAuditLogQueryRepository
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


def _append_log(
    db_session: Session,
    *,
    organization_id: uuid.UUID,
    action: str,
    created_at: datetime,
) -> AuditLog:
    repository = SqlAlchemyAuditLogRepository(db_session)
    audit_log = AuditLog(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        action=action,
        resource_type="organization",
        resource_id=str(uuid.uuid4()),
        old_values=None,
        new_values={"status": "active"},
        metadata={"source": "test"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        created_at=created_at,
    )
    repository.append(audit_log)
    db_session.commit()
    return audit_log


def test_query_repository_lists_org_logs_in_desc_order(db_session: Session) -> None:
    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    now = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)

    _append_log(
        db_session,
        organization_id=org_id,
        action="identity.organization.create",
        created_at=now,
    )
    _append_log(
        db_session,
        organization_id=org_id,
        action="identity.organization.update",
        created_at=now - timedelta(minutes=1),
    )
    _append_log(
        db_session,
        organization_id=other_org_id,
        action="identity.organization.create",
        created_at=now,
    )

    repository = SqlAlchemyAuditLogQueryRepository(db_session)
    page = repository.list_by_organization(
        org_id,
        query_filter=AuditLogQueryFilter(),
        cursor=None,
        limit=10,
    )

    assert len(page.items) == 2
    assert page.items[0].action == "identity.organization.create"
    assert page.items[1].action == "identity.organization.update"
    assert all(item.organization_id == org_id for item in page.items)


def test_query_repository_filters_by_action(db_session: Session) -> None:
    org_id = uuid.uuid4()
    now = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
    _append_log(db_session, organization_id=org_id, action="identity.organization.create", created_at=now)
    _append_log(db_session, organization_id=org_id, action="identity.organization.update", created_at=now)

    repository = SqlAlchemyAuditLogQueryRepository(db_session)
    page = repository.list_by_organization(
        org_id,
        query_filter=AuditLogQueryFilter(action="identity.organization.update"),
        cursor=None,
        limit=10,
    )

    assert len(page.items) == 1
    assert page.items[0].action == "identity.organization.update"


def test_query_repository_supports_cursor_pagination(db_session: Session) -> None:
    org_id = uuid.uuid4()
    now = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
    _append_log(db_session, organization_id=org_id, action="identity.organization.create", created_at=now)
    _append_log(
        db_session,
        organization_id=org_id,
        action="identity.organization.update",
        created_at=now - timedelta(minutes=1),
    )

    repository = SqlAlchemyAuditLogQueryRepository(db_session)
    first_page = repository.list_by_organization(
        org_id,
        query_filter=AuditLogQueryFilter(),
        cursor=None,
        limit=1,
    )
    assert len(first_page.items) == 1
    assert first_page.next_cursor is not None

    second_page = repository.list_by_organization(
        org_id,
        query_filter=AuditLogQueryFilter(),
        cursor=first_page.next_cursor,
        limit=1,
    )
    assert len(second_page.items) == 1
    assert second_page.items[0].id != first_page.items[0].id
