import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_api_test_helpers import (
    login,
    seed_authenticated_user,
    seed_user_with_org_permission,
)


def test_list_organization_memberships(client: TestClient, db_session: Session) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.memberships.read")
    token = login(client, seed.user.email)

    response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/memberships",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["memberships"], list)


def test_invite_member_returns_token(client: TestClient, db_session: Session) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.memberships.invite")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/memberships/invite",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
        json={"email": "invitee@example.com"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token"]
    assert body["invite_id"]


@pytest.mark.skip(reason="SQLite stores naive datetimes; accept invite needs infra mapper tz fix")
def test_accept_membership_invite(client: TestClient, db_session: Session) -> None:
    inviter_seed = seed_user_with_org_permission(
        db_session,
        permission_code="identity.memberships.invite",
    )
    invitee = seed_authenticated_user(db_session)
    inviter_token = login(client, inviter_seed.user.email)

    invite_response = client.post(
        f"/api/v1/organizations/{inviter_seed.org.id.value}/memberships/invite",
        headers={
            "Authorization": f"Bearer {inviter_token}",
            "X-Organization-Id": str(inviter_seed.org.id.value),
        },
        json={"email": invitee.email.value},
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_token = invite_response.json()["token"]

    accept_token = login(client, invitee.email)
    accept_response = client.post(
        "/api/v1/memberships/invites/accept",
        headers={"Authorization": f"Bearer {accept_token}"},
        json={"token": invite_token},
    )

    assert accept_response.status_code == 200, accept_response.text
    body = accept_response.json()
    assert body["organization_id"] == str(inviter_seed.org.id.value)
    assert body["membership"]["status"] == "active"


def test_suspend_membership_out_of_scope_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.memberships.update")
    token = login(client, seed.user.email)
    foreign_membership_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/memberships/{foreign_membership_id}/suspend",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 404
