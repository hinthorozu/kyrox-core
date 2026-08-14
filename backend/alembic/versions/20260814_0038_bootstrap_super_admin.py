"""Bootstrap the first super admin when the installation has one active user.

Revision ID: 20260814_0038
Revises: 20260814_0037
"""

from alembic import op
import sqlalchemy as sa

revision = "20260814_0038"
down_revision = "20260814_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    super_admin_count = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM identity_users
            WHERE is_super_admin = true
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()
    if super_admin_count:
        return

    active_users = connection.execute(
        sa.text(
            """
            SELECT id
            FROM identity_users
            WHERE status = 'active'
              AND deleted_at IS NULL
            ORDER BY created_at ASC, id ASC
            LIMIT 2
            """
        )
    ).scalars().all()

    # Bootstrap only when the choice is unambiguous. Never guess which user
    # should become a platform super admin on an existing multi-user system.
    if len(active_users) != 1:
        return

    connection.execute(
        sa.text(
            """
            UPDATE identity_users
            SET is_super_admin = true,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id
            """
        ),
        {"user_id": active_users[0]},
    )


def downgrade() -> None:
    # Intentionally irreversible: a migration must not silently revoke a
    # platform administrator privilege after the installation has started.
    pass
