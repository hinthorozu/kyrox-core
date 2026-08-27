"""Allow platform-scoped identity notifications.

Revision ID: 20260827_0064
Revises: 20260827_0063
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0064"
down_revision: str | None = "20260827_0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
    with op.batch_alter_table("platform_notifications") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
