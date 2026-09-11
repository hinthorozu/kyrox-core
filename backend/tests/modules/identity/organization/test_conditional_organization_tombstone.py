from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.domain.retention_policy import AUDIT_RETENTION_POLICY_VERSION
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel
from app.modules.identity.infrastructure.persistence.models import UserModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import login, seed_authenticated_user


EXPECTED_EPISODE_HEADER = "X-Kyrox-Expected-Suspension-Updated-At"


def _login_super_admin(client: TestClient, db_session: Session) -> str:
    user = seed_authenticated_user(db_session)
    user_model = db_session.get(UserModel, user.id.value)
    assert user_model is not None
    user_model.is_super_admin = True
    db_session.commit()
    return login(client, user.email)


def _create_organization(client: TestClient, token: str) -> uuid.UUID:
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Conditional Tombstone Org",
            "slug": f"conditional-tombstone-{uuid.uuid4().hex[:8]}",
        },
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["organization"]["id"])


def _headers(token: str, organization_id: uuid.UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def test_conditional_tombstone_accepts_exact_current_suspension_episode(
    client: TestClient,
    db_session: Session,
) -> None:
    token = _login_super_admin(client, db_session)
    organization_id = _create_organization(client, token)
    headers = _headers(token, organization_id)

    response = client.post(
        f"/api/v1/organizations/{organization_id}/suspend",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    organization = db_session.get(OrganizationModel, organization_id)
    assert organization is not None
    db_session.refresh(organization)
    episode = _as_utc(organization.updated_at)

    db_session.add(
        AuditLogModel(
            organization_id=organization_id,
            user_id=None,
            session_id=None,
            action="fair_crm.customer.created",
            resource_type="customer",
            resource_id=str(uuid.uuid4()),
            old_values={"name": "old payload"},
            new_values={"display_name": "customer payload"},
            event_metadata={"raw": "provider payload"},
            ip_address="127.0.0.1",
            user_agent="sensitive-agent",
        )
    )
    db_session.commit()

    response = client.delete(
        f"/api/v1/organizations/{organization_id}",
        headers={**headers, EXPECTED_EPISODE_HEADER: episode.isoformat()},
    )

    assert response.status_code == 204, response.text
    db_session.refresh(organization)
    assert organization.status == "suspended"
    assert organization.deleted_at is not None
    assert _as_utc(organization.updated_at) == episode

    retained = list(
        db_session.scalars(
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.asc(), AuditLogModel.id.asc())
        ).all()
    )
    assert retained
    assert all(row.action != "fair_crm.customer.created" for row in retained)
    assert all(
        row.action.startswith("identity.organization.")
        or row.action.startswith("fair_crm.organization_closure.")
        for row in retained
    )

    deleted_rows = [row for row in retained if row.action == "identity.organization.deleted"]
    assert len(deleted_rows) == 1
    assert deleted_rows[0].new_values == {"deleted": True}
    assert deleted_rows[0].event_metadata == {"authority": "system"}

    minimization_rows = [
        row for row in retained if row.action == "identity.organization.audit_retention_minimized"
    ]
    assert len(minimization_rows) == 1
    minimization = minimization_rows[0]
    assert minimization.new_values is not None
    assert minimization.new_values["policy_version"] == AUDIT_RETENTION_POLICY_VERSION
    assert minimization.new_values["deleted_non_retention_rows"] >= 1
    assert minimization.event_metadata == {"authority": "system"}

    for row in retained:
        assert row.ip_address is None
        assert row.user_agent is None
        if row.action.startswith("fair_crm.organization_closure."):
            assert row.old_values is None
            assert row.new_values is None
            assert row.event_metadata is None


def test_conditional_tombstone_rejects_active_organization_without_mutation(
    client: TestClient,
    db_session: Session,
) -> None:
    token = _login_super_admin(client, db_session)
    organization_id = _create_organization(client, token)
    headers = _headers(token, organization_id)

    organization = db_session.get(OrganizationModel, organization_id)
    assert organization is not None
    episode = _as_utc(organization.updated_at)

    response = client.delete(
        f"/api/v1/organizations/{organization_id}",
        headers={**headers, EXPECTED_EPISODE_HEADER: episode.isoformat()},
    )

    assert response.status_code == 409, response.text
    db_session.refresh(organization)
    assert organization.status == "active"
    assert organization.deleted_at is None


def test_conditional_tombstone_rejects_stale_suspension_episode_without_mutation(
    client: TestClient,
    db_session: Session,
) -> None:
    token = _login_super_admin(client, db_session)
    organization_id = _create_organization(client, token)
    headers = _headers(token, organization_id)

    response = client.post(
        f"/api/v1/organizations/{organization_id}/suspend",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    organization = db_session.get(OrganizationModel, organization_id)
    assert organization is not None
    db_session.refresh(organization)
    current_episode = _as_utc(organization.updated_at)
    stale_episode = current_episode - timedelta(microseconds=1)

    response = client.delete(
        f"/api/v1/organizations/{organization_id}",
        headers={**headers, EXPECTED_EPISODE_HEADER: stale_episode.isoformat()},
    )

    assert response.status_code == 409, response.text
    db_session.refresh(organization)
    assert organization.status == "suspended"
    assert organization.deleted_at is None
    assert _as_utc(organization.updated_at) == current_episode
