"""Remove legacy owner role; platform super admin is identity_users.is_super_admin.

Revision ID: 20260814_0043
Revises: 20260814_0042
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_0043"
down_revision = "20260814_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM identity_roles
            WHERE slug = 'owner'
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "20260814_0043 is irreversible: platform ownership is represented by identity_users.is_super_admin"
    )
