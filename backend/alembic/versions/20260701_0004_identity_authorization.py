"""Identity authorization tables and membership role assignment.

Revision ID: 20260701_0004
Revises: 20260701_0003
Create Date: 2026-07-01

Creates identity_roles, identity_permissions, identity_role_permissions,
and adds role_id to identity_memberships.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0004"
down_revision: Union[str, Sequence[str], None] = "20260701_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_identity_permissions_code"),
    )
    op.create_index("ix_identity_permissions_code", "identity_permissions", ["code"], unique=False)

    op.create_table(
        "identity_roles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_identity_roles_organization_slug",
        ),
    )
    op.create_index(
        "ix_identity_roles_organization_id",
        "identity_roles",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "identity_role_permissions",
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("permission_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["identity_permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index(
        "ix_identity_role_permissions_permission_id",
        "identity_role_permissions",
        ["permission_id"],
        unique=False,
    )

    op.add_column(
        "identity_memberships",
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_identity_memberships_role_id",
        "identity_memberships",
        "identity_roles",
        ["role_id"],
        ["id"],
    )
    op.create_index(
        "ix_identity_memberships_role_id",
        "identity_memberships",
        ["role_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_memberships_role_id", table_name="identity_memberships")
    op.drop_constraint("fk_identity_memberships_role_id", "identity_memberships", type_="foreignkey")
    op.drop_column("identity_memberships", "role_id")

    op.drop_index("ix_identity_role_permissions_permission_id", table_name="identity_role_permissions")
    op.drop_table("identity_role_permissions")

    op.drop_index("ix_identity_roles_organization_id", table_name="identity_roles")
    op.drop_table("identity_roles")

    op.drop_index("ix_identity_permissions_code", table_name="identity_permissions")
    op.drop_table("identity_permissions")
