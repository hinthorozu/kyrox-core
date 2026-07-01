"""Create platform_jobs table for background job queue.

Revision ID: 20260701_0021
Revises: 20260701_0020
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260701_0021"
down_revision: Union[str, Sequence[str], None] = "20260701_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_platform_jobs_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_platform_jobs_attempt_count"),
        sa.CheckConstraint("max_attempts >= 1", name="ck_platform_jobs_max_attempts"),
        sa.CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_platform_jobs_attempt_lte_max",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_jobs_organization_id",
        "platform_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_jobs_status_created",
        "platform_jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_platform_jobs_org_type_idempotency",
        "platform_jobs",
        ["organization_id", "job_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_platform_jobs_org_type_idempotency", table_name="platform_jobs")
    op.drop_index("ix_platform_jobs_status_created", table_name="platform_jobs")
    op.drop_index("ix_platform_jobs_organization_id", table_name="platform_jobs")
    op.drop_table("platform_jobs")
