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
TRIGGER_NAME = "trg_identity_users_default_owner_super_admin"
FUNCTION_NAME = "identity_default_owner_super_admin_on_insert"


def upgrade() -> None:
    bind = op.get_bind()

    # Existing installations: promote the canonical owner once.
    bind.execute(
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

    # Fresh installations run Core migrations before the Fair CRM bootstrap seed.
    # The trigger guarantees the canonical bootstrap owner is born as super admin
    # even if an older seed explicitly inserts FALSE. It fires on INSERT only:
    # afterwards identity_users.is_super_admin is fully DB-controlled and can be
    # changed TRUE/FALSE manually without a deploy or seed forcing it back.
    bind.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.email = '{DEFAULT_OWNER_EMAIL}' THEN
                    NEW.is_super_admin := TRUE;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON identity_users;
            CREATE TRIGGER {TRIGGER_NAME}
            BEFORE INSERT ON identity_users
            FOR EACH ROW
            EXECUTE FUNCTION {FUNCTION_NAME}()
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON identity_users"))
    bind.execute(sa.text(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()"))
    bind.execute(
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
