from app.modules.identity.infrastructure.authorization.persistence.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
)


def test_identity_role_table_metadata() -> None:
    table = RoleModel.__table__

    assert table.name == "identity_roles"
    column_names = {column.name for column in table.columns}
    assert "scope" in column_names
    assert "slug" in column_names
    assert "is_system" in column_names
    assert {
        "role_kind",
        "organization_id",
        "source_template_role_id",
        "template_version",
        "source_template_version",
        "permissions_customized",
        "is_assignable",
        "is_protected",
        "auto_include_new_permissions",
    }.issubset(column_names)


def test_identity_permission_table_metadata() -> None:
    table = PermissionModel.__table__

    assert table.name == "identity_permissions"
    assert table.c.code.unique is True
    assert {column.name for column in table.columns} == {
        "id",
        "group_id",
        "code",
        "description",
        "is_system",
        "lifecycle_state",
        "is_assignable",
        "permission_scope",
        "lifecycle_reason",
        "lifecycle_changed_at",
        "lifecycle_changed_by",
        "created_at",
        "updated_at",
    }


def test_identity_role_permission_table_metadata() -> None:
    table = RolePermissionModel.__table__

    assert table.name == "identity_role_permissions"
    pk_columns = {column.name for column in table.primary_key.columns}
    assert pk_columns == {"role_id", "permission_id"}

    fk_targets = {fk.parent.name: fk.target_fullname for fk in table.foreign_keys}
    assert fk_targets["role_id"] == "identity_roles.id"
    assert fk_targets["permission_id"] == "identity_permissions.id"
