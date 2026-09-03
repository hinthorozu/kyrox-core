import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.authentication.persistence.models.refresh_token import (
    RefreshTokenModel,
)
from app.modules.identity.infrastructure.authentication.persistence.models.session import SessionModel
from app.modules.identity.infrastructure.persistence.models import UserModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import seed_authenticated_user, seed_user_with_org_permission


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _login_super_admin(client: TestClient, db_session: Session) -> str:
    user = seed_authenticated_user(db_session)
    user_model = db_session.get(UserModel, user.id.value)
    assert user_model is not None
    user_model.is_super_admin = True
    db_session.commit()
    return _login(client, user.email.value)["access_token"]


def test_suspend_revokes_target_organization_sessions_and_refresh_tokens(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(
        db_session,
        permission_code="identity.organizations.read",
    )
    tokens = _login(client, seed.user.email.value)
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    super_admin_token = _login_super_admin(client, db_session)
    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/suspend",
        headers={
            "Authorization": f"Bearer {super_admin_token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )
    assert response.status_code == 200, response.text

    sessions = db_session.scalars(
        select(SessionModel).where(SessionModel.user_id == seed.user.id.value)
    ).all()
    assert sessions
    assert all(session.revoked_at is not None for session in sessions)

    refresh_tokens = db_session.scalars(
        select(RefreshTokenModel)
        .join(SessionModel, SessionModel.id == RefreshTokenModel.session_id)
        .where(SessionModel.user_id == seed.user.id.value)
    ).all()
    assert refresh_tokens
    assert all(token.revoked_at is not None for token in refresh_tokens)
    assert all(token.revoked_reason == "organization_suspended" for token in refresh_tokens)

    protected_response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )
    assert protected_response.status_code == 401

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
