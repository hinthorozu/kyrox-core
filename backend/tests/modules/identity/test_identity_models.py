from app.modules.identity.infrastructure.persistence.models import OrganizationModel, UserModel


def test_identity_user_table_metadata() -> None:
    table = UserModel.__table__

    assert table.name == "identity_users"
    assert {column.name for column in table.columns} == {
        "id",
        "email",
        "password_hash",
        "status",
        "is_super_admin",
        "organization_id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert table.c.email.unique is True
    fk_columns = {fk.parent.name: fk.target_fullname for fk in table.foreign_keys}
    assert fk_columns["organization_id"] == "identity_organizations.id"


def test_identity_organization_table_metadata() -> None:
    table = OrganizationModel.__table__

    assert table.name == "identity_organizations"
    assert {column.name for column in table.columns} == {
        "id",
        "name",
        "slug",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert table.c.slug.unique is True
