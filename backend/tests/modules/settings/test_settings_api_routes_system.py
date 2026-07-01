import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login, seed_authenticated_user, seed_user_with_org_permission

from settings_test_helpers import seed_super_admin_user


def test_list_system_settings_requires_super_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = seed_super_admin_user(db_session)
    token = login(client, admin.email)

    put_response = client.put(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={"Authorization": f"Bearer {token}"},
        json={"value": {"enabled": False}},
    )
    assert put_response.status_code == 200, put_response.text

    response = client.get(
        "/api/v1/system/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["key"] == "kyrox.platform.maintenance_mode"


def test_system_settings_rejects_non_super_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    user = seed_authenticated_user(db_session)
    token = login(client, user.email)

    response = client.get(
        "/api/v1/system/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_system_setting_get_and_delete(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = seed_super_admin_user(db_session)
    token = login(client, admin.email)

    client.put(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={"Authorization": f"Bearer {token}"},
        json={"value": {"enabled": True}},
    )

    get_response = client.get(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["organization_id"] is None

    delete_response = client.delete(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    missing_response = client.get(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_response.status_code == 404


def test_org_user_with_settings_permission_cannot_access_system_settings(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.read")
    token = login(client, seed.user.email)

    response = client.get(
        "/api/v1/system/settings/kyrox.platform.maintenance_mode",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 403
