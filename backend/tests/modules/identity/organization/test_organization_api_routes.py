import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import (
    login,
    seed_authenticated_user,
    seed_user_with_org_permission,
)


def test_create_organization_returns_membership(client: TestClient, db_session: Session) -> None:
    user = seed_authenticated_user(db_session)
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
    assert body["membership_id"]


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
