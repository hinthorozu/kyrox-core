import uuid
from datetime import UTC, datetime

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.infrastructure.persistence.mappers import (
    audit_log_to_domain,
    audit_log_to_model,
)


def test_audit_log_mapper_roundtrip() -> None:
    entity = AuditLog(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        action="identity.user.logout",
        resource_type="user",
        resource_id=str(uuid.uuid4()),
        old_values={"active": True},
        new_values={"active": False},
        metadata={"reason": "user_initiated"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        created_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC),
    )

    restored = audit_log_to_domain(audit_log_to_model(entity))
    assert restored == entity
