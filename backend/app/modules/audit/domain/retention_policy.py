from dataclasses import dataclass


AUDIT_RETENTION_POLICY_VERSION = "ol09-d.v1"
RETAINED_AUDIT_ACTION_PREFIXES = (
    "identity.organization.",
    "fair_crm.organization_closure.",
)


@dataclass(frozen=True, slots=True)
class AuditRetentionMinimizationCounts:
    deleted_non_retention_rows: int
    sanitized_retention_rows: int


def is_terminal_retention_action(action: str) -> bool:
    normalized = action.strip()
    return any(normalized.startswith(prefix) for prefix in RETAINED_AUDIT_ACTION_PREFIXES)
