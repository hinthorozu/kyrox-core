import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login

from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus
from app.modules.notifications.domain.value_objects.recipient import Recipient
from app.modules.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository
from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope
from app.modules.settings.infrastructure.repositories import SqlAlchemySettingRepository
from notifications_test_helpers import seed_user_with_notification_permissions


def test_send_notification_runs_dispatch_job(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_notification_permissions(db_session)
    token = login(client, user.email)

    response = client.post(
        f"/api/v1/organizations/{org.id.value}/notifications/send",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
        json={
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hello",
            "body": "World",
        },
    )

    assert response.status_code == 202, response.text
    notification_id = response.json()["notification"]["id"]

    get_response = client.get(
        f"/api/v1/notifications/{notification_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
    )

    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["status"] == "sent"


def test_send_notification_suppressed_via_settings(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_notification_permissions(db_session)
    settings_repo = SqlAlchemySettingRepository(db_session)
    now = datetime.now(UTC)
    settings_repo.upsert(
        Setting(
            id=uuid.uuid4(),
            scope=SettingScope.ORGANIZATION,
            organization_id=org.id.value,
            key=SettingKey.create("kyrox.notifications.email_enabled"),
            value={"enabled": False},
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    token = login(client, user.email)

    response = client.post(
        f"/api/v1/organizations/{org.id.value}/notifications/send",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
        json={
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hello",
            "body": "World",
        },
    )

    assert response.status_code == 202, response.text
    assert response.json()["notification"]["status"] == "suppressed"


def test_get_notification_masks_other_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_notification_permissions(db_session)
    other_org_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    now = datetime.now(UTC)
    SqlAlchemyNotificationRepository(db_session).save(
        Notification(
            id=notification_id,
            organization_id=other_org_id,
            channel=NotificationChannel.EMAIL,
            recipient=Recipient.create("user@example.com"),
            subject="Hello",
            body="World",
            template_key=None,
            variables=None,
            status=NotificationStatus.SENT,
            idempotency_key=None,
            job_id=None,
            failure_reason=None,
            created_at=now,
            queued_at=None,
            sent_at=now,
            failed_at=None,
            suppressed_at=None,
        )
    )
    db_session.commit()
    token = login(client, user.email)

    get_response = client.get(
        f"/api/v1/notifications/{notification_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
    )

    assert get_response.status_code == 404


def test_send_notification_idempotency(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_notification_permissions(db_session)
    token = login(client, user.email)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org.id.value),
    }
    body = {
        "channel": "email",
        "recipient": "user@example.com",
        "subject": "Hello",
        "body": "World",
        "idempotency_key": "notify-1",
    }

    first = client.post(
        f"/api/v1/organizations/{org.id.value}/notifications/send",
        headers=headers,
        json=body,
    )
    second = client.post(
        f"/api/v1/organizations/{org.id.value}/notifications/send",
        headers=headers,
        json=body,
    )

    assert first.status_code == 202, first.text
    assert second.status_code == 200, second.text
    assert first.json()["notification"]["id"] == second.json()["notification"]["id"]
    assert second.json()["created"] is False
