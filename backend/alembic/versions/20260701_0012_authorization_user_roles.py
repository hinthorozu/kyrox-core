"""Create identity_user_roles and migrate membership role assignments.

Revision ID: 20260701_0012
Revises: 20260701_0011
Create Date: 2026-07-01
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0012"
down_revision: Union[str, Sequence[str], None] = "20260701_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USER_ROLES_TABLE = "identity_user_roles"
ORG_ROLES_TABLE = "identity_organization_roles"
MEMBERSHIPS_TABLE = "identity_memberships"


def _migrate_user_roles(connection: sa.Connection) -> None:
    rows = connection.execute(
        sa.text(
            f"""
            SELECT
                m.user_id,
                m.organization_id,
                orr.id AS organization_role_id,
                m.created_at AS assigned_at
            FROM {MEMBERSHIPS_TABLE} AS m
            JOIN {ORG_ROLES_TABLE} AS orr
              ON orr.organization_id = m.organization_id
             AND orr.role_id = m.role_id
            WHERE m.role_id IS NOT NULL
              AND m.status = 'active'
              AND m.deleted_at IS NULL
              AND orr.deleted_at IS NULL
              AND orr.status = 'active'
            """
        )
    ).fetchall()

    for row in rows:
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {USER_ROLES_TABLE} (
                    id, user_id, organization_id, organization_role_id,
                    status, assigned_at, revoked_at, assigned_by, created_at
                )
                VALUES (
                    :id, :user_id, :organization_id, :organization_role_id,
                    'active', :assigned_at, NULL, NULL, :assigned_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": str(row.user_id),
                "organization_id": str(row.organization_id),
                "organization_role_id": str(row.organization_role_id),
                "assigned_at": row.assigned_at,
            },
        )


def upgrade() -> None:
    op.create_table(
        USER_ROLES_TABLE,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_role_id"], [ORG_ROLES_TABLE + ".id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["identity_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_identity_user_roles_user_org",
        USER_ROLES_TABLE,
        ["user_id", "organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_user_roles_organization_role_id",
        USER_ROLES_TABLE,
        ["organization_role_id"],
        unique=False,
    )

    connection = op.get_bind()
    _migrate_user_roles(connection)


def downgrade() -> None:
    op.drop_index("ix_identity_user_roles_organization_role_id", table_name=USER_ROLES_TABLE)
    op.drop_index("ix_identity_user_roles_user_org", table_name=USER_ROLES_TABLE)
    op.drop_table(USER_ROLES_TABLE)
