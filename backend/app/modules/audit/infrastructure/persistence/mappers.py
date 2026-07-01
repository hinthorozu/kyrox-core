from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.infrastructure.persistence.models import AuditLogModel


def audit_log_to_domain(model: AuditLogModel) -> AuditLog:
    return AuditLog(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        session_id=model.session_id,
        action=model.action,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        old_values=model.old_values,
        new_values=model.new_values,
        metadata=model.event_metadata,
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        created_at=model.created_at,
    )


def audit_log_to_model(entity: AuditLog) -> AuditLogModel:
    return AuditLogModel(
        id=entity.id,
        organization_id=entity.organization_id,
        user_id=entity.user_id,
        session_id=entity.session_id,
        action=entity.action,
        resource_type=entity.resource_type,
        resource_id=entity.resource_id,
        old_values=entity.old_values,
        new_values=entity.new_values,
        event_metadata=entity.metadata,
        ip_address=entity.ip_address,
        user_agent=entity.user_agent,
        created_at=entity.created_at,
    )
