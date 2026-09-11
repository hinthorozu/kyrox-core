from dataclasses import dataclass


AUDIT_RETENTION_POLICY_VERSION = "ol09-d.v1"
CORE_LIFECYCLE_ACTION_PREFIX = "identity.organization."
FAIR_CLOSURE_ACTION_PREFIX = "fair_crm.organization_closure."
RETAINED_AUDIT_ACTION_PREFIXES = (
    CORE_LIFECYCLE_ACTION_PREFIX,
    FAIR_CLOSURE_ACTION_PREFIX,
)


@dataclass(frozen=True, slots=True)
class AuditRetentionMinimizationCounts:
    deleted_non_retention_rows: int
    sanitized_retention_rows: int


def is_terminal_retention_action(action: str) -> bool:
    normalized = action.strip()
    return any(normalized.startswith(prefix) for prefix in RETAINED_AUDIT_ACTION_PREFIXES)


def is_reserved_core_lifecycle_action(action: str) -> bool:
    return action.strip().startswith(CORE_LIFECYCLE_ACTION_PREFIX)
