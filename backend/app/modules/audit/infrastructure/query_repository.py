from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session as DbSession

from app.modules.audit.domain.query.audit_log_cursor import AuditLogCursor
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter
from app.modules.audit.domain.query.audit_log_query_page import AuditLogQueryPage
from app.modules.audit.infrastructure.persistence.mappers import audit_log_to_domain
from app.modules.audit.infrastructure.persistence.models import AuditLogModel


class SqlAlchemyAuditLogQueryRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        query_filter: AuditLogQueryFilter,
        cursor: AuditLogCursor | None,
        limit: int,
    ) -> AuditLogQueryPage:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.desc(), AuditLogModel.id.desc())
            .limit(limit + 1)
        )

        if query_filter.action is not None:
            stmt = stmt.where(AuditLogModel.action == query_filter.action)
        if query_filter.action_prefix is not None:
            escaped = _escape_like_prefix(query_filter.action_prefix)
            stmt = stmt.where(AuditLogModel.action.like(f"{escaped}%", escape="\\"))
        if query_filter.resource_type is not None:
            stmt = stmt.where(AuditLogModel.resource_type == query_filter.resource_type)
        if query_filter.resource_id is not None:
            stmt = stmt.where(AuditLogModel.resource_id == query_filter.resource_id)
        if query_filter.user_id is not None:
            stmt = stmt.where(AuditLogModel.user_id == query_filter.user_id)
        if query_filter.session_id is not None:
            stmt = stmt.where(AuditLogModel.session_id == query_filter.session_id)
        if query_filter.created_from is not None:
            stmt = stmt.where(AuditLogModel.created_at >= query_filter.created_from)
        if query_filter.created_to is not None:
            stmt = stmt.where(AuditLogModel.created_at < query_filter.created_to)

        if cursor is not None:
            stmt = stmt.where(
                tuple_(AuditLogModel.created_at, AuditLogModel.id)
                < tuple_(cursor.created_at, cursor.id)
            )

        models = self._session.scalars(stmt).all()
        has_next = len(models) > limit
        page_models = models[:limit]

        items = [audit_log_to_domain(model) for model in page_models]
        next_cursor = None
        if has_next and page_models:
            last = page_models[-1]
            next_cursor = AuditLogCursor(created_at=last.created_at, id=last.id)

        return AuditLogQueryPage(items=items, next_cursor=next_cursor)


def _escape_like_prefix(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
