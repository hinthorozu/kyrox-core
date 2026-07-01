"""Create identity_organization_roles and migrate legacy role assignments.

Revision ID: 20260701_0011
Revises: 20260701_0010
Create Date: 2026-07-01
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0011"
down_revision: Union[str, Sequence[str], None] = "20260701_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORG_ROLES_TABLE = "identity_organization_roles"
ROLES_TABLE = "identity_roles"
MEMBERSHIPS_TABLE = "identity_memberships"


def _migrate_organization_roles(connection: sa.Connection) -> None:
    rows = connection.execute(
        sa.text(
            f"""
            SELECT m.organization_id, m.role_id, MIN(m.created_at) AS created_at
            FROM {MEMBERSHIPS_TABLE} AS m
            JOIN {ROLES_TABLE} AS r ON r.id = m.role_id
            WHERE m.role_id IS NOT NULL
              AND m.deleted_at IS NULL
              AND r.deleted_at IS NULL
            GROUP BY m.organization_id, m.role_id
            """
        )
    ).fetchall()

    for row in rows:
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {ORG_ROLES_TABLE} (
                    id, organization_id, role_id, status, is_default,
                    created_at, updated_at, deleted_at
                )
                VALUES (
                    :id, :organization_id, :role_id, 'active', :is_default,
                    :created_at, :created_at, NULL
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "organization_id": str(row.organization_id),
                "role_id": str(row.role_id),
                "is_default": False,
                "created_at": row.created_at,
            },
        )


def upgrade() -> None:
    op.create_table(
        ORG_ROLES_TABLE,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "role_id",
            name="uq_identity_organization_roles_organization_role",
        ),
    )
    op.create_index(
        "ix_identity_organization_roles_organization_id",
        ORG_ROLES_TABLE,
        ["organization_id"],
        unique=False,
    )

    connection = op.get_bind()
    _migrate_organization_roles(connection)


def downgrade() -> None:
    op.drop_index("ix_identity_organization_roles_organization_id", table_name=ORG_ROLES_TABLE)
    op.drop_table(ORG_ROLES_TABLE)
