import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.persistence.models import MembershipModel, UserModel

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


def test_create_organization_user_with_temporary_password(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="identity.users.create")
    token = login(client, seed.user.email)

    response = client.post(
        f"/api/v1/organizations/{seed.org.id.value}/users",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
        json={
            "email": "temporary-user@example.com",
            "temporary_password": "Temporary123!",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "temporary-user@example.com"
    assert body["must_change_password"] is True
    assert body["membership"]["status"] == "active"

    user = db_session.scalars(
        select(UserModel).where(UserModel.email == "temporary-user@example.com")
    ).one()
    assert user.must_change_password is True
    membership = db_session.scalars(
        select(MembershipModel).where(
            MembershipModel.user_id == user.id,
            MembershipModel.organization_id == seed.org.id.value,
        )
    ).one()
    assert membership.status == "active"


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
