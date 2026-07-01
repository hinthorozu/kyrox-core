import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login, seed_user_with_org_permission


def test_record_organization_audit_event_creates_log(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/audit-events",
        json={
            "action": "fair_crm.customer.created",
            "resource_type": "customer",
            "resource_id": str(uuid.uuid4()),
            "new_values": {"display_name": "Example Co"},
            "metadata": {"source": "test"},
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["action"] == "fair_crm.customer.created"
    assert body["resource_type"] == "customer"
    assert body["organization_id"] == str(seed.org.id.value)
    assert body["user_id"] == str(seed.user.id.value)

    list_response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/audit-logs",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert any(item["action"] == "fair_crm.customer.created" for item in items)


def test_record_organization_audit_event_rejects_invalid_action(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/audit-events",
        json={
            "action": "invalid-action",
            "resource_type": "customer",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400


def test_record_organization_audit_event_scope_mismatch_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{uuid.uuid4()}/audit-events",
        json={
            "action": "fair_crm.customer.created",
            "resource_type": "customer",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400


def test_record_organization_audit_event_requires_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/audit-events",
        json={
            "action": "fair_crm.customer.created",
            "resource_type": "customer",
        },
        headers={"X-Organization-Id": str(seed.org.id.value)},
    )

    assert response.status_code == 401
