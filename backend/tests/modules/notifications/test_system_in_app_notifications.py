from uuid import uuid4

from app.modules.identity.infrastructure.persistence.models import UserModel
from app.modules.notifications.infrastructure.persistence.models import PlatformNotificationModel
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.domain.exceptions import InvalidNotificationRequestError
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from identity_api_test_helpers import login
from notifications_test_helpers import seed_user_with_notification_permissions
import pytest


def test_system_inbox_uses_real_super_admin_flag_and_no_org_context(client, db_session):
    user, _ = seed_user_with_notification_permissions(db_session)
    token = login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}
    proposal = {
        "subject": "Çalışma tamamlandı", "body": "Sonuçları inceleyin",
        "variables": {"path": "/fairs", "run_id": str(uuid4())},
        "idempotency_key": "completion-1",
    }
    assert client.post("/api/v1/system/notifications/in-app", headers=headers, json=proposal).status_code == 403
    assert client.get("/api/v1/system/notifications/in-app", headers=headers).status_code == 403
    db_session.get(UserModel, user.id.value).is_super_admin = True
    db_session.commit()
    sent = client.post("/api/v1/system/notifications/in-app", headers=headers, json=proposal)
    assert sent.status_code == 200, sent.text
    payload = sent.json()
    assert payload["created"] is True
    assert payload["notification"]["status"] == "sent"
    assert payload["notification"]["job_id"] is None
    assert payload["notification"]["organization_id"] is None
    replay = client.post("/api/v1/system/notifications/in-app", headers=headers, json=proposal)
    assert replay.json()["created"] is False
    changed = {**proposal, "body": "Different content"}
    assert client.post("/api/v1/system/notifications/in-app", headers=headers, json=changed).status_code == 409
    changed_navigation = {**proposal, "variables": {"path": "/other"}}
    assert client.post("/api/v1/system/notifications/in-app", headers=headers, json=changed_navigation).status_code == 409
    foreign = {**proposal, "recipient": str(uuid4()), "idempotency_key": "other-user"}
    assert client.post("/api/v1/system/notifications/in-app", headers=headers, json=foreign).status_code == 200
    inbox = client.get("/api/v1/system/notifications/in-app", headers=headers)
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    assert inbox.json()[0]["variables"] == proposal["variables"]
    assert db_session.query(PlatformNotificationModel).count() == 2


def test_in_app_recipient_must_be_a_user_or_super_admin():
    with pytest.raises(InvalidNotificationRequestError):
        NotificationPolicy().normalize_recipient("someone@example.com", NotificationChannel.IN_APP)


def test_worker_delivery_has_purpose_separated_fail_closed_credential(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "CORE_PRODUCT_NOTIFICATION_TOKEN", "x" * 32)
    proposal = {"subject": "Completed", "body": "Open results", "idempotency_key": "worker-1"}
    assert client.post("/api/v1/internal/notifications/in-app", json=proposal).status_code == 401
    assert client.post("/api/v1/internal/notifications/in-app", headers={"X-Kyrox-Notification-Token": "incorrect"}, json=proposal).status_code == 401
    response = client.post("/api/v1/internal/notifications/in-app", headers={"X-Kyrox-Notification-Token": "x" * 32}, json=proposal)
    assert response.status_code == 200
    assert response.json()["notification"]["organization_id"] is None
    assert response.json()["notification"]["channel"] == "in_app"
    monkeypatch.setattr(settings, "CORE_PRODUCT_NOTIFICATION_TOKEN", None)
    assert client.post("/api/v1/internal/notifications/in-app", json=proposal).status_code == 503


def test_organization_notification_endpoint_cannot_target_system_inbox(client, db_session):
    user, org = seed_user_with_notification_permissions(db_session)
    token = login(client, user.email)
    response = client.post(f"/api/v1/organizations/{org.id.value}/notifications/send",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": str(org.id.value)},
        json={"channel": "in_app", "recipient": "super_admin", "subject": "Forbidden", "body": "Forbidden"})
    assert response.status_code == 400
    assert db_session.query(PlatformNotificationModel).count() == 0
