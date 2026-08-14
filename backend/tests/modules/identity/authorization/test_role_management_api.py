import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.api.authorization.guards import require_super_admin
from app.modules.identity.infrastructure.authorization.persistence.models import (
    PermissionGroupModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)
from app.modules.identity.infrastructure.organization.persistence.models import OrganizationModel
from app.modules.identity.infrastructure.persistence.models import UserModel


def test_super_admin_template_derive_sync_and_permission_lock(
    client: TestClient,
    db_session: Session,
) -> None:
    actor_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    group_id = uuid.uuid4()
    permission_id = uuid.uuid4()
    template_id = uuid.uuid4()
    db_session.add(UserModel(
        id=actor_id, email="role-admin@example.com", password_hash="hash",
        status="active", is_super_admin=True,
    ))
    db_session.add(OrganizationModel(
        id=organization_id, name="Role Test Org", slug="role-test-org", status="active",
    ))
    db_session.add(PermissionGroupModel(
        id=group_id, code="role.test", name="Role Test", module="identity",
        description="Role management tests", sort_order=1, is_system=False,
    ))
    db_session.add(PermissionModel(
        id=permission_id, group_id=group_id, code="role.test.read",
        description="Read role test", is_system=False, lifecycle_state="active",
        is_assignable=True,
    ))
    db_session.add(RoleModel(
        id=template_id, name="ReadUser", slug="read_user_test", scope="organization",
        is_system=True, role_kind="template", organization_id=None,
        template_version=1, permissions_customized=False, is_assignable=False,
        is_protected=True, auto_include_new_permissions=False,
    ))
    db_session.add(RolePermissionModel(role_id=template_id, permission_id=permission_id))
    db_session.commit()

    client.app.dependency_overrides[require_super_admin] = lambda: SimpleNamespace(
        sub=SimpleNamespace(value=actor_id)
    )

    templates = client.get("/api/v1/role-templates")
    assert templates.status_code == 200
    assert templates.json()[0]["is_assignable"] is False

    derived = client.post(
        f"/api/v1/role-templates/{template_id}/derive",
        json={
            "organization_id": str(organization_id),
            "name": "ABN Read User",
            "slug": "abn_read_user",
        },
    )
    assert derived.status_code == 201
    derived_body = derived.json()
    assert derived_body["organization_id"] == str(organization_id)
    assert derived_body["permission_ids"] == [str(permission_id)]

    preview = client.post(
        f"/api/v1/role-templates/{template_id}/sync/preview",
        json={"role_ids": [derived_body["id"]]},
    )
    assert preview.status_code == 200
    assert preview.json()[0]["add_count"] == 0
    assert preview.json()[0]["remove_count"] == 0

    locked = client.post(
        f"/api/v1/permissions/{permission_id}/lifecycle",
        json={"state": "locked", "reason": "Test lock"},
    )
    assert locked.status_code == 200
    assert locked.json()["affected_roles"] == 2
    assert db_session.scalar(select(func.count(RolePermissionModel.role_id)).where(
        RolePermissionModel.permission_id == permission_id
    )) == 0
    assert db_session.scalar(select(func.count(AuditLogModel.id)).where(
        AuditLogModel.action == "permission.lifecycle.update"
    )) == 1
