"""Allow platform-scoped jobs and notifications for identity email.

Revision ID: 20260827_0064
Revises: 20260827_0063
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260827_0064"
down_revision = "20260827_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("platform_jobs") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
    op.create_index(
        "uq_platform_jobs_platform_type_idempotency",
        "platform_jobs",
        ["job_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "organization_id IS NULL AND idempotency_key IS NOT NULL"
        ),
        sqlite_where=sa.text(
            "organization_id IS NULL AND idempotency_key IS NOT NULL"
        ),
    )

    with op.batch_alter_table("platform_notifications") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
    op.create_index(
        "uq_platform_notifications_platform_idempotency",
        "platform_notifications",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "organization_id IS NULL AND idempotency_key IS NOT NULL"
        ),
        sqlite_where=sa.text(
            "organization_id IS NULL AND idempotency_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_platform_notifications_platform_idempotency",
        table_name="platform_notifications",
    )
    op.execute(sa.text("DELETE FROM platform_notifications WHERE organization_id IS NULL"))
    with op.batch_alter_table("platform_notifications") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

    op.drop_index(
        "uq_platform_jobs_platform_type_idempotency",
        table_name="platform_jobs",
    )
    op.execute(sa.text("DELETE FROM platform_jobs WHERE organization_id IS NULL"))
    with op.batch_alter_table("platform_jobs") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
