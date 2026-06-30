"""Identity core tables: users, organizations, memberships.

Revision ID: 20260701_0002
Revises: 20260701_0001
Create Date: 2026-07-01

Creates identity_users, identity_organizations, and identity_memberships.
Role, permission, and refresh token tables are deferred to later sprints.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0002"
down_revision: Union[str, Sequence[str], None] = "20260701_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_identity_users_email"),
    )
    op.create_index("ix_identity_users_email", "identity_users", ["email"], unique=False)

    op.create_table(
        "identity_organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_identity_organizations_slug"),
    )
    op.create_index(
        "ix_identity_organizations_slug",
        "identity_organizations",
        ["slug"],
        unique=False,
    )

    op.create_table(
        "identity_memberships",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_identity_memberships_user_organization",
        ),
    )
    op.create_index(
        "ix_identity_memberships_user_id",
        "identity_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_memberships_organization_id",
        "identity_memberships",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_memberships_organization_id", table_name="identity_memberships")
    op.drop_index("ix_identity_memberships_user_id", table_name="identity_memberships")
    op.drop_table("identity_memberships")

    op.drop_index("ix_identity_organizations_slug", table_name="identity_organizations")
    op.drop_table("identity_organizations")

    op.drop_index("ix_identity_users_email", table_name="identity_users")
    op.drop_table("identity_users")
