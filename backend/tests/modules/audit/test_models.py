from app.modules.audit.infrastructure.persistence.models import AuditLogModel


def test_audit_log_table_metadata() -> None:
    table = AuditLogModel.__table__

    assert table.name == "audit_logs"
    assert {column.name for column in table.columns} == {
        "id",
        "organization_id",
        "user_id",
        "session_id",
        "action",
        "resource_type",
        "resource_id",
        "old_values",
        "new_values",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    }

    indexed_columns = {index.columns.keys()[0] for index in table.indexes}
    assert indexed_columns == {
        "organization_id",
        "user_id",
        "session_id",
        "action",
        "resource_type",
        "created_at",
    }

    assert table.c.action.nullable is False
    assert table.c.resource_type.nullable is False
    assert table.c.created_at.nullable is False
