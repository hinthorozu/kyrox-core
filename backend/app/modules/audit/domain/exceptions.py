class AuditError(Exception):
    """Base class for audit module failures."""


class InvalidAuditEventError(AuditError):
    """Audit event payload failed validation."""


class AuditRetentionOrganizationNotFoundError(AuditError):
    """The organization required for retention authority does not exist."""


class AuditRetentionPreconditionError(AuditError):
    """Audit retention purge is not currently policy-authorized."""
