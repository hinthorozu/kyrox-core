"""Promote the canonical default owner to DB-controlled super admin.

Revision ID: 20260814_0041
Revises: 20260814_0040
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_0041"
down_revision = "20260814_0040"
branch_labels = None
depends_on = None

DEFAULT_OWNER_EMAIL = "dev@example.com"


def upgrade() -> None:
    # One-time promotion for existing installations. Future authorization reads
    # identity_users.is_super_admin directly, so operators may toggle this value
    # in the database after this migration without seed jobs forcing it back.
    op.get_bind().execute(
        sa.text(
            """
            UPDATE identity_users
            SET is_super_admin = TRUE,
                updated_at = NOW()
            WHERE email = :email
              AND deleted_at IS NULL
            """
        ),
        {"email": DEFAULT_OWNER_EMAIL},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE identity_users
            SET is_super_admin = FALSE,
                updated_at = NOW()
            WHERE email = :email
              AND deleted_at IS NULL
            """
        ),
        {"email": DEFAULT_OWNER_EMAIL},
    )
