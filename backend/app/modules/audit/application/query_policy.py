import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.audit.domain.query.audit_log_cursor import AuditLogCursor
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter
from app.modules.audit.domain.query_exceptions import InvalidAuditQueryError


class AuditLogQueryPolicy:
    DEFAULT_LIMIT = 50
    MIN_LIMIT = 1
    MAX_LIMIT = 100
    MAX_ACTION_LENGTH = 255
    MAX_RESOURCE_TYPE_LENGTH = 128
    MIN_ACTION_PREFIX_LENGTH = 3
    MAX_DATE_RANGE_DAYS = 90

    def normalize_limit(self, limit: int | None) -> int:
        if limit is None:
            return self.DEFAULT_LIMIT
        if limit < self.MIN_LIMIT or limit > self.MAX_LIMIT:
            raise InvalidAuditQueryError(
                f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}"
            )
        return limit

    def validate_filter(self, query_filter: AuditLogQueryFilter) -> AuditLogQueryFilter:
        if query_filter.action and query_filter.action_prefix:
            raise InvalidAuditQueryError("action and action_prefix are mutually exclusive")
        if query_filter.action and len(query_filter.action) > self.MAX_ACTION_LENGTH:
            raise InvalidAuditQueryError(f"action must be at most {self.MAX_ACTION_LENGTH} characters")
        if query_filter.action_prefix:
            if len(query_filter.action_prefix) < self.MIN_ACTION_PREFIX_LENGTH:
                raise InvalidAuditQueryError(
                    f"action_prefix must be at least {self.MIN_ACTION_PREFIX_LENGTH} characters"
                )
            if len(query_filter.action_prefix) > self.MAX_ACTION_LENGTH:
                raise InvalidAuditQueryError(
                    f"action_prefix must be at most {self.MAX_ACTION_LENGTH} characters"
                )
        if query_filter.resource_type and len(query_filter.resource_type) > self.MAX_RESOURCE_TYPE_LENGTH:
            raise InvalidAuditQueryError(
                f"resource_type must be at most {self.MAX_RESOURCE_TYPE_LENGTH} characters"
            )

        created_from = self._normalize_datetime(query_filter.created_from)
        created_to = self._normalize_datetime(query_filter.created_to)
        if created_from and created_to:
            if created_from >= created_to:
                raise InvalidAuditQueryError("from must be before to")
            if created_to - created_from > timedelta(days=self.MAX_DATE_RANGE_DAYS):
                raise InvalidAuditQueryError(
                    f"date range must not exceed {self.MAX_DATE_RANGE_DAYS} days"
                )

        return AuditLogQueryFilter(
            action=query_filter.action,
            action_prefix=query_filter.action_prefix,
            resource_type=query_filter.resource_type,
            resource_id=query_filter.resource_id,
            user_id=query_filter.user_id,
            session_id=query_filter.session_id,
            created_from=created_from,
            created_to=created_to,
        )

    def decode_cursor(self, raw: str | None) -> AuditLogCursor | None:
        if raw is None:
            return None
        if not raw.strip():
            raise InvalidAuditQueryError("cursor must not be empty")
        try:
            payload = json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
            created_at = datetime.fromisoformat(payload["created_at"])
            cursor_id = UUID(payload["id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidAuditQueryError("Invalid cursor") from exc

        normalized_created_at = self._normalize_datetime(created_at)
        if normalized_created_at is None:
            raise InvalidAuditQueryError("Invalid cursor")
        return AuditLogCursor(created_at=normalized_created_at, id=cursor_id)

    def encode_cursor(self, cursor: AuditLogCursor) -> str:
        payload = {
            "created_at": cursor.created_at.isoformat(),
            "id": str(cursor.id),
        }
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
