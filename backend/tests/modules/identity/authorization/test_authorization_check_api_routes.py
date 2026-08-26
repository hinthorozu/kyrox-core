import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.persistence.models import UserModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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


def test_check_permission_returns_allowed_true_for_scraper_read(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="fair_crm.scraper.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "fair_crm.scraper.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allowed"] is True
    assert body["permission_code"] == "fair_crm.scraper.read"


def test_check_permission_nested_admin_code_does_not_return_500(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(
        db_session,
        permission_code="fair_crm.admin.backups.read",
    )
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "fair_crm.admin.backups.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allowed"] is True
    assert body["permission_code"] == "fair_crm.admin.backups.read"


def test_check_permission_invalid_permission_code_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/authorization/check",
        json={"permission_code": "fair_crm..read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400, response.text


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


def test_normal_user_cannot_self_assert_super_admin_for_foreign_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)
    foreign_organization_id = uuid.uuid4()

    response = client.post(
        (
            f"/api/v1/organizations/{foreign_organization_id}/authorization/check"
            f"?is_super_admin=true&organization_id={foreign_organization_id}"
        ),
        json={
            "permission_code": "audit.logs.read",
            "is_super_admin": True,
            "organization_id": str(foreign_organization_id),
        },
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(foreign_organization_id),
            "X-Is-Super-Admin": "true",
            "X-Platform-Super-Admin": "true",
        },
    )

    assert response.status_code == 403, response.text


def test_db_backed_super_admin_bypasses_foreign_scope_without_new_token(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="audit.logs.read")
    token = login(client, seed.user.email)
    foreign_organization_id = uuid.uuid4()

    user_model = db_session.get(UserModel, seed.user.id.value)
    assert user_model is not None
    assert user_model.is_super_admin is False
    user_model.is_super_admin = True
    db_session.commit()

    response = client.post(
        f"/api/v1/organizations/{foreign_organization_id}/authorization/check",
        json={"permission_code": "product.anything.read"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(foreign_organization_id),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "allowed": True,
        "permission_code": "product.anything.read",
    }


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
