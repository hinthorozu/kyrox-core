import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.persistence import models as identity_models
from identity_api_test_helpers import login, seed_authenticated_user


def _seed_super_admin(client: TestClient, db_session: Session) -> str:
    user = seed_authenticated_user(db_session)
    model = db_session.get(identity_models.UserModel, user.id.value)
    assert model is not None
    model.is_super_admin = True
    db_session.commit()
    return login(client, user.email)


def test_admin_organization_crud(client: TestClient, db_session: Session) -> None:
    token = _seed_super_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"admin-org-{uuid.uuid4().hex[:8]}"

    create_response = client.post(
        "/api/v1/admin/organizations",
        headers=headers,
        json={"name": "Admin Org", "slug": slug},
    )
    assert create_response.status_code == 201, create_response.text
    organization_id = create_response.json()["organization"]["id"]

    list_response = client.get("/api/v1/admin/organizations", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert organization_id in {item["id"] for item in list_response.json()["items"]}

    get_response = client.get(
        f"/api/v1/admin/organizations/{organization_id}",
        headers=headers,
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["slug"] == slug

    update_response = client.patch(
        f"/api/v1/admin/organizations/{organization_id}",
        headers=headers,
        json={"name": "Updated Admin Org"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["name"] == "Updated Admin Org"

    delete_response = client.delete(
        f"/api/v1/admin/organizations/{organization_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204, delete_response.text

    list_after_delete = client.get("/api/v1/admin/organizations", headers=headers)
    assert list_after_delete.status_code == 200, list_after_delete.text
    assert organization_id not in {item["id"] for item in list_after_delete.json()["items"]}


def test_admin_organization_routes_reject_regular_user(
    client: TestClient,
    db_session: Session,
) -> None:
    user = seed_authenticated_user(db_session)
    token = login(client, user.email)

    response = client.get(
        "/api/v1/admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
