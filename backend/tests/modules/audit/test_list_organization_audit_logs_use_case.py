import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.audit.application.list_organization_audit_logs import ListOrganizationAuditLogsUseCase
from app.modules.audit.application.query_commands import ListOrganizationAuditLogsCommand
from app.modules.audit.application.query_policy import AuditLogQueryPolicy
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.query.audit_log_cursor import AuditLogCursor
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter
from app.modules.audit.domain.query.audit_log_query_page import AuditLogQueryPage
from app.modules.audit.domain.query_exceptions import InvalidAuditQueryError


class InMemoryAuditLogQueryRepository:
    def __init__(self, logs: list[AuditLog]) -> None:
        self._logs = logs

    def list_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        query_filter: AuditLogQueryFilter,
        cursor: AuditLogCursor | None,
        limit: int,
    ) -> AuditLogQueryPage:
        filtered = [
            log
            for log in self._logs
            if log.organization_id == organization_id
        ]
        filtered.sort(key=lambda log: (log.created_at, log.id), reverse=True)

        if cursor is not None:
            filtered = [
                log
                for log in filtered
                if (log.created_at, log.id) < (cursor.created_at, cursor.id)
            ]

        if query_filter.action is not None:
            filtered = [log for log in filtered if log.action == query_filter.action]

        has_next = len(filtered) > limit
        page_items = filtered[:limit]
        next_cursor = None
        if has_next and page_items:
            last = page_items[-1]
            next_cursor = AuditLogCursor(created_at=last.created_at, id=last.id)

        return AuditLogQueryPage(items=page_items, next_cursor=next_cursor)


def _log(
    *,
    organization_id: uuid.UUID,
    action: str,
    created_at: datetime,
) -> AuditLog:
    return AuditLog(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        action=action,
        resource_type="organization",
        resource_id=str(uuid.uuid4()),
        old_values=None,
        new_values=None,
        metadata=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
        created_at=created_at,
    )


def test_list_organization_audit_logs_returns_items_and_cursor() -> None:
    org_id = uuid.uuid4()
    now = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
    logs = [
        _log(organization_id=org_id, action="identity.organization.create", created_at=now),
        _log(
            organization_id=org_id,
            action="identity.organization.update",
            created_at=now - timedelta(minutes=1),
        ),
    ]
    use_case = ListOrganizationAuditLogsUseCase(InMemoryAuditLogQueryRepository(logs))

    result = use_case.execute(
        ListOrganizationAuditLogsCommand(
            organization_id=org_id,
            query_filter=AuditLogQueryFilter(),
            limit=1,
        )
    )

    assert len(result.items) == 1
    assert result.items[0].action == "identity.organization.create"
    assert result.next_cursor is not None


def test_list_organization_audit_logs_rejects_invalid_filter() -> None:
    org_id = uuid.uuid4()
    use_case = ListOrganizationAuditLogsUseCase(InMemoryAuditLogQueryRepository([]))

    with pytest.raises(InvalidAuditQueryError, match="mutually exclusive"):
        use_case.execute(
            ListOrganizationAuditLogsCommand(
                organization_id=org_id,
                query_filter=AuditLogQueryFilter(action="a.b.c", action_prefix="a.b"),
                limit=50,
            )
        )


def test_query_policy_rejects_invalid_limit() -> None:
    policy = AuditLogQueryPolicy()

    with pytest.raises(InvalidAuditQueryError):
        policy.normalize_limit(101)
