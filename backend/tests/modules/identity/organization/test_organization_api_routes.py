import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel
from app.modules.identity.infrastructure.persistence.models import UserModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import (
    login,
    seed_authenticated_user,
    seed_user_with_org_permission,
)


def _login_super_admin(client: TestClient, db_session: Session) -> tuple[uuid.UUID, str]:
    user = seed_authenticated_user(db_session)
    user_model = db_session.get(UserModel, user.id.value)
    assert user_model is not None
    user_model.is_super_admin = True
    db_session.commit()
    return user.id.value, login(client, user.email)


def _create_organization_as_super_admin(client: TestClient, token: str) -> uuid.UUID:
    slug = f"ol05-org-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "OL05 Test Org", "slug": slug},
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["organization"]["id"])


def _lifecycle_path(organization_id: uuid.UUID, suffix: str) -> str:
    return f"/api/v1/organizations/{organization_id}{suffix}"


def test_super_admin_creates_organization_without_membership(client: TestClient, db_session: Session) -> None:
    user = seed_authenticated_user(db_session)
    user_model = db_session.get(UserModel, user.id.value)
    assert user_model is not None
    user_model.is_super_admin = True
    db_session.commit()
    token = login(client, user.email)
    slug = f"new-org-{uuid.uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Org", "slug": slug},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["organization"]["slug"] == slug
    assert body["organization"]["status"] == "active"
    assert "membership_id" not in body


def test_get_organization_requires_permission(client: TestClient, db_session: Session) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.organizations.read")
    token = login(client, seed.user.email)

    response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(seed.org.id.value)


def test_get_organization_scope_mismatch_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.organizations.read")
    token = login(client, seed.user.email)
    other_org_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/organizations/{other_org_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400
    assert "scope mismatch" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("POST", "/suspend"),
        ("POST", "/reactivate"),
        ("DELETE", ""),
    ],
)
def test_lifecycle_endpoints_require_authentication(
    client: TestClient,
    method: str,
    suffix: str,
) -> None:
    organization_id = uuid.uuid4()

    response = client.request(
        method,
        _lifecycle_path(organization_id, suffix),
        headers={"X-Organization-Id": str(organization_id)},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("POST", "/suspend"),
        ("POST", "/reactivate"),
        ("DELETE", ""),
    ],
)
def test_organization_user_cannot_execute_system_lifecycle_actions(
    client: TestClient,
    db_session: Session,
    method: str,
    suffix: str,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.organizations.read")
    token = login(client, seed.user.email)
    organization_id = seed.org.id.value

    response = client.request(
        method,
        _lifecycle_path(organization_id, suffix),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(organization_id),
        },
    )

    assert response.status_code == 403
    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    assert organization_model.status == "active"
    assert organization_model.deleted_at is None


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("POST", "/suspend"),
        ("POST", "/reactivate"),
        ("DELETE", ""),
    ],
)
def test_organization_user_cannot_spoof_another_organization_for_lifecycle_actions(
    client: TestClient,
    db_session: Session,
    method: str,
    suffix: str,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.organizations.read")
    token = login(client, seed.user.email)
    target_organization_id = uuid.uuid4()

    response = client.request(
        method,
        _lifecycle_path(target_organization_id, suffix),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(target_organization_id),
        },
    )

    assert response.status_code == 403
    own_organization_model = db_session.get(OrganizationModel, seed.org.id.value)
    assert own_organization_model is not None
    assert own_organization_model.status == "active"
    assert own_organization_model.deleted_at is None


def test_super_admin_can_suspend_organization_and_transition_is_audited(
    client: TestClient,
    db_session: Session,
) -> None:
    actor_user_id, token = _login_super_admin(client, db_session)
    organization_id = _create_organization_as_super_admin(client, token)

    response = client.post(
        _lifecycle_path(organization_id, "/suspend"),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(organization_id),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "suspended"

    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    assert organization_model.status == "suspended"

    audit_log = db_session.scalars(
        select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.action == "identity.organization.suspended",
        )
    ).one()
    assert audit_log.user_id == actor_user_id
    assert audit_log.session_id is not None
    assert audit_log.resource_type == "organization"
    assert audit_log.resource_id == str(organization_id)
    assert audit_log.new_values == {"status": "suspended"}
    assert audit_log.event_metadata == {"authority": "system"}


def test_super_admin_can_reactivate_suspended_organization_and_transition_is_audited(
    client: TestClient,
    db_session: Session,
) -> None:
    actor_user_id, token = _login_super_admin(client, db_session)
    organization_id = _create_organization_as_super_admin(client, token)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }

    suspend_response = client.post(
        _lifecycle_path(organization_id, "/suspend"),
        headers=headers,
    )
    assert suspend_response.status_code == 200, suspend_response.text

    response = client.post(
        _lifecycle_path(organization_id, "/reactivate"),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"

    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    assert organization_model.status == "active"

    audit_log = db_session.scalars(
        select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.action == "identity.organization.reactivated",
        )
    ).one()
    assert audit_log.user_id == actor_user_id
    assert audit_log.session_id is not None
    assert audit_log.resource_type == "organization"
    assert audit_log.resource_id == str(organization_id)
    assert audit_log.new_values == {"status": "active"}
    assert audit_log.event_metadata == {"authority": "system"}


@pytest.mark.parametrize("source_status", ["active", "pending_activation", "archived"])
def test_super_admin_cannot_reactivate_non_suspended_organization_and_no_audit_is_written(
    client: TestClient,
    db_session: Session,
    source_status: str,
) -> None:
    _, token = _login_super_admin(client, db_session)
    organization_id = _create_organization_as_super_admin(client, token)
    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    organization_model.status = source_status
    db_session.commit()

    response = client.post(
        _lifecycle_path(organization_id, "/reactivate"),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(organization_id),
        },
    )

    assert response.status_code == 409, response.text
    db_session.refresh(organization_model)
    assert organization_model.status == source_status

    audit_logs = db_session.scalars(
        select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.action == "identity.organization.reactivated",
        )
    ).all()
    assert audit_logs == []


def test_super_admin_cannot_reactivate_soft_deleted_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    _, token = _login_super_admin(client, db_session)
    organization_id = _create_organization_as_super_admin(client, token)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(organization_id),
    }

    delete_response = client.delete(
        _lifecycle_path(organization_id, ""),
        headers=headers,
    )
    assert delete_response.status_code == 204, delete_response.text

    response = client.post(
        _lifecycle_path(organization_id, "/reactivate"),
        headers=headers,
    )

    assert response.status_code == 404, response.text
    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    assert organization_model.deleted_at is not None

    audit_logs = db_session.scalars(
        select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.action == "identity.organization.reactivated",
        )
    ).all()
    assert audit_logs == []


def test_super_admin_can_delete_organization_and_transition_is_audited(
    client: TestClient,
    db_session: Session,
) -> None:
    actor_user_id, token = _login_super_admin(client, db_session)
    organization_id = _create_organization_as_super_admin(client, token)

    response = client.delete(
        _lifecycle_path(organization_id, ""),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(organization_id),
        },
    )

    assert response.status_code == 204, response.text

    organization_model = db_session.get(OrganizationModel, organization_id)
    assert organization_model is not None
    assert organization_model.deleted_at is not None

    audit_log = db_session.scalars(
        select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.action == "identity.organization.deleted",
        )
    ).one()
    assert audit_log.user_id == actor_user_id
    assert audit_log.session_id is not None
    assert audit_log.resource_type == "organization"
    assert audit_log.resource_id == str(organization_id)
    assert audit_log.new_values == {"deleted": True}
    assert audit_log.event_metadata == {"authority": "system"}
