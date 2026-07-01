import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login, seed_user_with_org_permission


def test_check_permission_returns_allowed_true(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "audit.logs.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allowed"] is True
    assert body["permission_code"] == "audit.logs.read"


def test_check_permission_returns_allowed_false(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "fair_crm.customers.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allowed"] is False
    assert body["permission_code"] == "fair_crm.customers.read"


def test_check_permission_scope_mismatch_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{uuid.uuid4()}/authorization/check",
        json={"permission_code": "audit.logs.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400


def test_check_permission_requires_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "audit.logs.read"},
        headers={"X-Organization-Id": str(seed.org.id.value)},
    )

    assert response.status_code == 401
