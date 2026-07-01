class AuditError(Exception):
    """Base class for audit module failures."""


class InvalidAuditEventError(AuditError):
    """Audit event payload failed validation."""
