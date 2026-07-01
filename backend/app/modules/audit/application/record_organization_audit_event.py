from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.audit.application.dto import RecordAuditEventCommand
from app.modules.audit.application.service import AuditService
from app.modules.audit.domain.entities import AuditLog


@dataclass(frozen=True)
class RecordOrganizationAuditEventCommand:
    organization_id: UUID
    user_id: UUID
    session_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class RecordOrganizationAuditEventUseCase:
    def __init__(self, audit_service: AuditService) -> None:
        self._audit_service = audit_service

    def execute(self, command: RecordOrganizationAuditEventCommand) -> AuditLog:
        return self._audit_service.record(
            RecordAuditEventCommand(
                organization_id=command.organization_id,
                user_id=command.user_id,
                session_id=command.session_id,
                action=command.action,
                resource_type=command.resource_type,
                resource_id=command.resource_id,
                old_values=command.old_values,
                new_values=command.new_values,
                metadata=command.metadata,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
            )
        )
