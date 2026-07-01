"""Create platform_settings table for org and system scoped settings.

Revision ID: 20260701_0019
Revises: 20260701_0018
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260701_0019"
down_revision: Union[str, Sequence[str], None] = "20260701_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.CheckConstraint(
            "scope IN ('system', 'organization')",
            name="ck_platform_settings_scope",
        ),
        sa.CheckConstraint(
            "(scope = 'organization' AND organization_id IS NOT NULL) "
            "OR (scope = 'system' AND organization_id IS NULL)",
            name="ck_platform_settings_scope_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_settings_scope_org",
        "platform_settings",
        ["scope", "organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_settings_key",
        "platform_settings",
        ["key"],
        unique=False,
    )
    op.create_index(
        "uq_platform_settings_system_key",
        "platform_settings",
        ["key"],
        unique=True,
        postgresql_where=sa.text("scope = 'system'"),
        sqlite_where=sa.text("scope = 'system'"),
    )
    op.create_index(
        "uq_platform_settings_org_key",
        "platform_settings",
        ["organization_id", "key"],
        unique=True,
        postgresql_where=sa.text("scope = 'organization'"),
        sqlite_where=sa.text("scope = 'organization'"),
    )


def downgrade() -> None:
    op.drop_index("uq_platform_settings_org_key", table_name="platform_settings")
    op.drop_index("uq_platform_settings_system_key", table_name="platform_settings")
    op.drop_index("ix_platform_settings_key", table_name="platform_settings")
    op.drop_index("ix_platform_settings_scope_org", table_name="platform_settings")
    op.drop_table("platform_settings")
