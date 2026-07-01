"""Create platform_notifications table for notification dispatch.

Revision ID: 20260701_0023
Revises: 20260701_0022
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260701_0023"
down_revision: Union[str, Sequence[str], None] = "20260701_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(length=255), nullable=True),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppressed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("channel IN ('email')", name="ck_platform_notifications_channel"),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'sending', 'sent', 'failed', 'suppressed')",
            name="ck_platform_notifications_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_notifications_organization_id",
        "platform_notifications",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_notifications_status_created",
        "platform_notifications",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_notifications_job_id",
        "platform_notifications",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "uq_platform_notifications_org_idempotency",
        "platform_notifications",
        ["organization_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_platform_notifications_org_idempotency", table_name="platform_notifications")
    op.drop_index("ix_platform_notifications_job_id", table_name="platform_notifications")
    op.drop_index("ix_platform_notifications_status_created", table_name="platform_notifications")
    op.drop_index("ix_platform_notifications_organization_id", table_name="platform_notifications")
    op.drop_table("platform_notifications")
