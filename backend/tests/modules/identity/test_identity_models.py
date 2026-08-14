from app.modules.identity.infrastructure.persistence.models import (
    MembershipModel,
    OrganizationModel,
    UserModel,
)

def test_identity_user_table_metadata() -> None:
    table = UserModel.__table__

    assert table.name == "identity_users"
    assert {column.name for column in table.columns} == {
        "id",
        "email",
        "password_hash",
        "status",
        "is_super_admin",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert table.c.email.unique is True


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


def test_identity_membership_table_metadata() -> None:
    table = MembershipModel.__table__

    assert table.name == "identity_memberships"
    assert {column.name for column in table.columns} == {
        "id",
        "user_id",
        "organization_id",
        "status",
        "invited_at",
        "joined_at",
        "created_at",
        "updated_at",
        "deleted_at",
    }

    fk_columns = {fk.parent.name: fk.target_fullname for fk in table.foreign_keys}
    assert fk_columns["user_id"] == "identity_users.id"
    assert fk_columns["organization_id"] == "identity_organizations.id"

    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("user_id", "organization_id") in unique_constraints
