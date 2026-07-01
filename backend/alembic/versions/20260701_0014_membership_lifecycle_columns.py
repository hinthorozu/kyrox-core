"""Add membership lifecycle timestamps.

Revision ID: 20260701_0014
Revises: 20260701_0013
Create Date: 2026-07-01

Adds invited_at and joined_at to identity_memberships for Sprint 0.3.5.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0014"
down_revision: Union[str, Sequence[str], None] = "20260701_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEMBERSHIPS_TABLE = "identity_memberships"


def upgrade() -> None:
    op.add_column(
        MEMBERSHIPS_TABLE,
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        MEMBERSHIPS_TABLE,
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"""
            UPDATE {MEMBERSHIPS_TABLE}
            SET joined_at = created_at
            WHERE joined_at IS NULL
              AND status = 'active'
              AND deleted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column(MEMBERSHIPS_TABLE, "joined_at")
    op.drop_column(MEMBERSHIPS_TABLE, "invited_at")
