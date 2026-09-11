from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.audit.domain.exceptions import (
    AuditRetentionOrganizationNotFoundError,
    AuditRetentionPreconditionError,
)
from app.modules.audit.domain.ports import AuditLogRepository
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId

AUDIT_RETENTION_MONTHS = 12


@dataclass(frozen=True, slots=True)
class PurgeRetainedOrganizationAuditResult:
    organization_id: UUID
    terminal_deleted_at: datetime
    retention_deadline: datetime
    purged_count: int


def add_calendar_months(value: datetime, months: int) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Retention timestamps must be timezone-aware")
    if months < 0:
        raise ValueError("Retention month offset must be non-negative")

    value = value.astimezone(UTC)
    target_index = value.year * 12 + (value.month - 1) + months
    target_year, target_month_index = divmod(target_index, 12)
    target_month = target_month_index + 1
    target_day = min(value.day, monthrange(target_year, target_month)[1])
    return value.replace(year=target_year, month=target_month, day=target_day)


class PurgeRetainedOrganizationAuditUseCase:
    def __init__(
        self,
        *,
        audit_log_repository: AuditLogRepository,
        organization_repository: OrganizationRepository,
        clock: Clock,
    ) -> None:
        self._audit_log_repository = audit_log_repository
        self._organization_repository = organization_repository
        self._clock = clock

    def execute(self, organization_id: UUID) -> PurgeRetainedOrganizationAuditResult:
        organization = self._organization_repository.get_by_id_including_deleted(
            OrganizationId(organization_id)
        )
        if organization is None:
            raise AuditRetentionOrganizationNotFoundError("Organization not found")
        if not organization.is_deleted() or organization.deleted_at is None:
            raise AuditRetentionPreconditionError(
                "Audit retention purge requires an authoritative terminal organization tombstone"
            )

        terminal_deleted_at = organization.deleted_at.astimezone(UTC)
        retention_deadline = add_calendar_months(
            terminal_deleted_at,
            AUDIT_RETENTION_MONTHS,
        )
        now = self._clock.now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Clock must return a timezone-aware timestamp")
        if now.astimezone(UTC) < retention_deadline:
            raise AuditRetentionPreconditionError(
                "Audit retention deadline has not been reached"
            )

        purged_count = self._audit_log_repository.purge_for_organization(organization_id)
        return PurgeRetainedOrganizationAuditResult(
            organization_id=organization_id,
            terminal_deleted_at=terminal_deleted_at,
            retention_deadline=retention_deadline,
            purged_count=purged_count,
        )
