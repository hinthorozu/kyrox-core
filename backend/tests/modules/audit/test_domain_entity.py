import uuid
from datetime import UTC, datetime

from app.modules.audit.domain.entities import AuditLog


def test_audit_log_entity_fields() -> None:
    event_id = uuid.uuid4()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    created_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)

    entity = AuditLog(
        id=event_id,
        organization_id=org_id,
        user_id=user_id,
        session_id=session_id,
        action="identity.user.login",
        resource_type="user",
        resource_id=str(user_id),
        old_values=None,
        new_values={"status": "authenticated"},
        metadata={"outcome": "success"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        created_at=created_at,
    )

    assert entity.id == event_id
    assert entity.action == "identity.user.login"
    assert entity.metadata == {"outcome": "success"}


def test_audit_log_entity_allows_null_actor_fields() -> None:
    entity = AuditLog(
        id=uuid.uuid4(),
        action="core.system.started",
        resource_type="system",
        created_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC),
    )

    assert entity.organization_id is None
    assert entity.user_id is None
    assert entity.session_id is None
