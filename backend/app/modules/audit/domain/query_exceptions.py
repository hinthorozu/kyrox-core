from app.modules.audit.domain.exceptions import AuditError


class InvalidAuditQueryError(AuditError):
    """Audit log query parameters failed validation."""
