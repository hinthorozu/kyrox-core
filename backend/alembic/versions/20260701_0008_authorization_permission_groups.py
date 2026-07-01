"""Create identity_permission_groups for authorization hierarchy.

Revision ID: 20260701_0008
Revises: 20260701_0007
Create Date: 2026-07-01
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0008"
down_revision: Union[str, Sequence[str], None] = "20260701_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"

DEFAULT_MODULES = ("audit", "core", "identity", "settings")


def _seed_permission_groups(connection: sa.Connection) -> None:
    existing_modules = {
        row[0]
        for row in connection.execute(
            sa.text(f"SELECT DISTINCT module FROM {PERMISSIONS_TABLE}")
        ).fetchall()
    }
    modules = sorted(existing_modules.union(DEFAULT_MODULES))

    for sort_order, module in enumerate(modules, start=1):
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {GROUPS_TABLE} (
                    id, code, name, module, description, sort_order, is_system, created_at, updated_at
                )
                SELECT :id, :code, :name, :module, :description, :sort_order, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (
                    SELECT 1 FROM {GROUPS_TABLE} WHERE module = :module
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "code": module,
                "name": module.title(),
                "module": module,
                "description": f"{module.title()} permissions",
                "sort_order": sort_order,
                "is_system": True,
            },
        )


def upgrade() -> None:
    op.create_table(
        GROUPS_TABLE,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_identity_permission_groups_code"),
    )
    op.create_index(
        "ix_identity_permission_groups_module",
        GROUPS_TABLE,
        ["module", "sort_order"],
        unique=False,
    )

    connection = op.get_bind()
    _seed_permission_groups(connection)


def downgrade() -> None:
    op.drop_index("ix_identity_permission_groups_module", table_name=GROUPS_TABLE)
    op.drop_table(GROUPS_TABLE)
