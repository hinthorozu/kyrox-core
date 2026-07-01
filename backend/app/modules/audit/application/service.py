"""Audit application service.

Events are recorded through explicit calls from use cases and services.
HTTP middleware auto-audit is intentionally not used in this module.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.audit.application.dto import RecordAuditEventCommand
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.exceptions import InvalidAuditEventError
from app.modules.audit.domain.ports import AuditLogRepository

_ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}$")


class AuditService:
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_log_repository = audit_log_repository

    def record(self, command: RecordAuditEventCommand) -> AuditLog:
        self._validate_command(command)

        audit_log = AuditLog(
            id=uuid.uuid4(),
            organization_id=command.organization_id,
            user_id=command.user_id,
            session_id=command.session_id,
            action=command.action.strip(),
            resource_type=command.resource_type.strip(),
            resource_id=command.resource_id,
            old_values=command.old_values,
            new_values=command.new_values,
            metadata=command.metadata,
            ip_address=command.ip_address,
            user_agent=command.user_agent,
            created_at=datetime.now(UTC),
        )
        return self._audit_log_repository.append(audit_log)

    def _validate_command(self, command: RecordAuditEventCommand) -> None:
        action = command.action.strip()
        resource_type = command.resource_type.strip()

        if not action:
            raise InvalidAuditEventError("action is required")
        if not resource_type:
            raise InvalidAuditEventError("resource_type is required")
        if not _ACTION_PATTERN.match(action):
            raise InvalidAuditEventError(
                "action must follow module.resource.action naming convention"
            )

        self._ensure_json_serializable(command.old_values, "old_values")
        self._ensure_json_serializable(command.new_values, "new_values")
        self._ensure_json_serializable(command.metadata, "metadata")

    @staticmethod
    def _ensure_json_serializable(value: dict[str, Any] | None, field_name: str) -> None:
        if value is None:
            return
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise InvalidAuditEventError(f"{field_name} must be JSON-serializable") from exc
