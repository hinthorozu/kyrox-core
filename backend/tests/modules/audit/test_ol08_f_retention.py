from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.application.purge_retained_organization_audit import add_calendar_months
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.api.authentication.dependencies import get_clock
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self.value = now

    def now(self) -> datetime:
        return self.value


def _headers() -> dict[str, str]:
    return {"X-Kyrox-Product-Lifecycle-Token": settings.CORE_PRODUCT_LIFECYCLE_TOKEN}


def _seed_deleted_organization(
    db_session: Session,
    *,
    deleted_at: datetime,
):
    organization_id = uuid4()
    db_session.add(
        OrganizationModel(
            id=organization_id,
            name=f"Deleted {organization_id}",
            slug=f"deleted-{organization_id}",
            status="suspended",
            deleted_at=deleted_at,
        )
    )
    db_session.flush()
    return organization_id


def _seed_audit(db_session: Session, organization_id, *, action: str) -> None:
    db_session.add(
        AuditLogModel(
            organization_id=organization_id,
            user_id=None,
            session_id=None,
            action=action,
            resource_type="organization_closure",
            resource_id=str(organization_id),
            old_values=None,
            new_values=None,
            event_metadata={"result": "bounded"},
            ip_address=None,
            user_agent=None,
        )
    )
    db_session.flush()


def _count(db_session: Session, organization_id) -> int:
    return int(
        db_session.scalar(
            select(func.count())
            .select_from(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
        )
        or 0
    )


def _set_clock(client: TestClient, at: datetime) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.dependency_overrides[get_clock] = lambda: FixedClock(at)


def test_calendar_retention_maps_leap_day_to_last_valid_day() -> None:
    assert add_calendar_months(datetime(2024, 2, 29, 10, 30, tzinfo=UTC), 12) == datetime(
        2025,
        2,
        28,
        10,
        30,
        tzinfo=UTC,
    )


def test_retention_purge_requires_product_lifecycle_credential(
    client: TestClient,
    db_session: Session,
) -> None:
    deleted_at = datetime(2025, 1, 1, tzinfo=UTC)
    organization_id = _seed_deleted_organization(db_session, deleted_at=deleted_at)
    _seed_audit(db_session, organization_id, action="organization_closure.completed")
    _set_clock(client, datetime(2026, 1, 1, tzinfo=UTC))

    path = f"/api/v1/organizations/{organization_id}/retained-audit-evidence/purge"
    assert client.post(path).status_code == 401
    assert client.post(path, headers={"X-Kyrox-Product-Lifecycle-Token": "wrong"}).status_code == 401
    assert _count(db_session, organization_id) == 1


def test_retention_purge_fails_closed_before_terminal_tombstone(
    client: TestClient,
    db_session: Session,
) -> None:
    organization_id = uuid4()
    db_session.add(
        OrganizationModel(
            id=organization_id,
            name="Not deleted",
            slug=f"not-deleted-{organization_id}",
            status="suspended",
            deleted_at=None,
        )
    )
    _seed_audit(db_session, organization_id, action="organization_closure.started")
    _set_clock(client, datetime(2030, 1, 1, tzinfo=UTC))

    response = client.post(
        f"/api/v1/organizations/{organization_id}/retained-audit-evidence/purge",
        headers=_headers(),
    )

    assert response.status_code == 409
    assert _count(db_session, organization_id) == 1


def test_retention_purge_fails_closed_before_exact_12_month_deadline(
    client: TestClient,
    db_session: Session,
) -> None:
    deleted_at = datetime(2025, 6, 15, 12, 30, 45, tzinfo=UTC)
    organization_id = _seed_deleted_organization(db_session, deleted_at=deleted_at)
    _seed_audit(db_session, organization_id, action="organization_closure.completed")
    _set_clock(client, datetime(2026, 6, 15, 12, 30, 44, 999999, tzinfo=UTC))

    response = client.post(
        f"/api/v1/organizations/{organization_id}/retained-audit-evidence/purge",
        headers=_headers(),
    )

    assert response.status_code == 409
    assert _count(db_session, organization_id) == 1


def test_retention_purge_uses_terminal_clock_purges_all_org_audit_and_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    deleted_at = datetime(2025, 6, 15, 12, 30, 45, tzinfo=UTC)
    deadline = datetime(2026, 6, 15, 12, 30, 45, tzinfo=UTC)
    organization_id = _seed_deleted_organization(db_session, deleted_at=deleted_at)
    other_organization_id = uuid4()
    _seed_audit(db_session, organization_id, action="organization_closure.completed")
    _seed_audit(db_session, organization_id, action="organization_closure.retained_after_terminal")
    _seed_audit(db_session, other_organization_id, action="other.organization.audit")
    _set_clock(client, deadline)

    path = f"/api/v1/organizations/{organization_id}/retained-audit-evidence/purge"
    first = client.post(path, headers=_headers())
    second = client.post(path, headers=_headers())

    assert first.status_code == 200, first.text
    assert first.json()["organization_id"] == str(organization_id)
    assert first.json()["purged_count"] == 2
    assert datetime.fromisoformat(first.json()["terminal_deleted_at"].replace("Z", "+00:00")) == deleted_at
    assert datetime.fromisoformat(first.json()["retention_deadline"].replace("Z", "+00:00")) == deadline
    assert second.status_code == 200, second.text
    assert second.json()["purged_count"] == 0
    assert _count(db_session, organization_id) == 0
    assert _count(db_session, other_organization_id) == 1


def test_later_audit_activity_does_not_restart_terminal_retention_clock(
    client: TestClient,
    db_session: Session,
) -> None:
    deleted_at = datetime(2025, 3, 1, tzinfo=UTC)
    organization_id = _seed_deleted_organization(db_session, deleted_at=deleted_at)
    _seed_audit(db_session, organization_id, action="organization.deleted")
    late = AuditLogModel(
        organization_id=organization_id,
        user_id=None,
        session_id=None,
        action="restore.reconciliation.observed",
        resource_type="organization_closure",
        resource_id=str(organization_id),
        old_values=None,
        new_values=None,
        event_metadata=None,
        ip_address=None,
        user_agent=None,
        created_at=deleted_at + timedelta(days=300),
    )
    db_session.add(late)
    db_session.flush()
    _set_clock(client, datetime(2026, 3, 1, tzinfo=UTC))

    response = client.post(
        f"/api/v1/organizations/{organization_id}/retained-audit-evidence/purge",
        headers=_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["purged_count"] == 2
    assert _count(db_session, organization_id) == 0
