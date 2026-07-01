import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login, seed_user_with_org_permission

from app.modules.settings.application.commands import UpsertSettingCommand
from app.modules.settings.application.upsert_setting import UpsertSettingUseCase
from app.modules.settings.domain.value_objects.setting_scope import SettingScope
from app.modules.settings.infrastructure.repositories import SqlAlchemySettingRepository


def _seed_org_setting(db_session: Session, org_id: uuid.UUID, key: str, value: dict) -> None:
    repository = SqlAlchemySettingRepository(db_session)
    UpsertSettingUseCase(repository).execute(
        UpsertSettingCommand(
            scope=SettingScope.ORGANIZATION,
            organization_id=org_id,
            key=key,
            value=value,
        )
    )
    db_session.commit()


def test_list_organization_settings_requires_permission(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.read")
    _seed_org_setting(
        db_session,
        seed.org.id.value,
        "fair_crm.pipeline.default_stage",
        {"enabled": True},
    )
    token = login(client, seed.user.email)

    response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/settings",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["key"] == "fair_crm.pipeline.default_stage"


def test_get_organization_setting_scope_mismatch_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.read")
    token = login(client, seed.user.email)

    response = client.get(
        f"/api/v1/organizations/{uuid.uuid4()}/settings/fair_crm.pipeline.default_stage",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 400


def test_upsert_organization_setting_requires_update_permission(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.update")
    token = login(client, seed.user.email)

    response = client.put(
        f"/api/v1/organizations/{seed.org.id.value}/settings/fair_crm.pipeline.default_stage",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
        json={"value": {"enabled": True}},
    )

    assert response.status_code == 200, response.text
    assert response.json()["value"] == {"enabled": True}


def test_delete_organization_setting_returns_204(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.update")
    _seed_org_setting(
        db_session,
        seed.org.id.value,
        "fair_crm.pipeline.default_stage",
        {"enabled": True},
    )
    token = login(client, seed.user.email)

    response = client.delete(
        f"/api/v1/organizations/{seed.org.id.value}/settings/fair_crm.pipeline.default_stage",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 204


def test_organization_settings_do_not_leak_across_orgs(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.read")
    other_org_id = uuid.uuid4()
    _seed_org_setting(
        db_session,
        seed.org.id.value,
        "fair_crm.pipeline.default_stage",
        {"org": "a"},
    )
    _seed_org_setting(
        db_session,
        other_org_id,
        "fair_crm.pipeline.default_stage",
        {"org": "b"},
    )
    token = login(client, seed.user.email)

    response = client.get(
        f"/api/v1/organizations/{seed.org.id.value}/settings",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["value"] == {"org": "a"}


def test_invalid_setting_key_returns_400(
    client: TestClient,
    db_session: Session,
) -> None:
    seed = seed_user_with_org_permission(db_session, permission_code="settings.platform.update")
    token = login(client, seed.user.email)

    response = client.put(
        f"/api/v1/organizations/{seed.org.id.value}/settings/invalid",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(seed.org.id.value),
        },
        json={"value": {"enabled": True}},
    )

    assert response.status_code == 400
