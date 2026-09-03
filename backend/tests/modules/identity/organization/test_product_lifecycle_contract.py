import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.identity.infrastructure.persistence.models import UserModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import seed_authenticated_user, seed_user_with_org_permission


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _login_super_admin(client: TestClient, db_session: Session) -> str:
    user = seed_authenticated_user(db_session)
    user_model = db_session.get(UserModel, user.id.value)
    assert user_model is not None
    user_model.is_super_admin = True
    db_session.commit()
    return _login(client, user.email.value)


def _lifecycle_headers() -> dict[str, str]:
    return {"X-Kyrox-Product-Lifecycle-Token": settings.CORE_PRODUCT_LIFECYCLE_TOKEN}


def test_product_lifecycle_snapshot_requires_dedicated_credential(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(
        db_session,
        permission_code="identity.organizations.read",
    )

    response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/lifecycle-snapshot",
    )

    assert response.status_code == 401


def test_product_lifecycle_snapshot_reports_active_and_suspended_state(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(
        db_session,
        permission_code="identity.organizations.read",
    )

    active_response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/lifecycle-snapshot",
        headers=_lifecycle_headers(),
    )
    assert active_response.status_code == 200, active_response.text
    assert active_response.json() == {
        "organization_id": str(seed.org.id.value),
        "status": "active",
        "work_allowed": True,
    }

    super_admin_token = _login_super_admin(client, db_session)
    suspend_response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/suspend",
        headers={
            "Authorization": f"Bearer {super_admin_token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )
    assert suspend_response.status_code == 200, suspend_response.text

    suspended_response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/lifecycle-snapshot",
        headers=_lifecycle_headers(),
    )
    assert suspended_response.status_code == 200, suspended_response.text
    assert suspended_response.json() == {
        "organization_id": str(seed.org.id.value),
        "status": "suspended",
        "work_allowed": False,
    }
