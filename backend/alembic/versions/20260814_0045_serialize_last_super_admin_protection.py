"""Serialize protection of the last active super admin.

Revision ID: 20260814_0045
Revises: 20260814_0044
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_0045"
down_revision = "20260814_0044"
branch_labels = None
depends_on = None

TRIGGER_NAME = "trg_identity_users_protect_last_super_admin"
FUNCTION_NAME = "identity_protect_last_super_admin"
LOCK_KEY = "kyrox.identity.last_active_super_admin"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                other_super_admins integer;
                removes_super_admin boolean;
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    removes_super_admin := OLD.is_super_admin
                        AND OLD.status = 'active'
                        AND OLD.deleted_at IS NULL;
                ELSE
                    removes_super_admin := OLD.is_super_admin
                        AND OLD.status = 'active'
                        AND OLD.deleted_at IS NULL
                        AND (
                            NOT NEW.is_super_admin
                            OR NEW.status <> 'active'
                            OR NEW.deleted_at IS NOT NULL
                        );
                END IF;

                IF removes_super_admin THEN
                    -- Prevent two concurrent demotions/deletions from both
                    -- observing the other Super Admin before either commits.
                    PERFORM pg_advisory_xact_lock(hashtext('{LOCK_KEY}'));

                    SELECT COUNT(*) INTO other_super_admins
                    FROM identity_users
                    WHERE id <> OLD.id
                      AND is_super_admin = TRUE
                      AND status = 'active'
                      AND deleted_at IS NULL;

                    IF other_super_admins = 0 THEN
                        RAISE EXCEPTION 'Cannot remove, demote, suspend, or delete the last active super admin';
                    END IF;
                END IF;

                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END;
            $$;

            DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON identity_users;
            CREATE TRIGGER {TRIGGER_NAME}
            BEFORE UPDATE OR DELETE ON identity_users
            FOR EACH ROW
            EXECUTE FUNCTION {FUNCTION_NAME}();
            """
        )
    )


def downgrade() -> None:
    # Restore the function body introduced by 0042, without the serialization
    # lock. The trigger remains attached to the same function.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                other_super_admins integer;
                removes_super_admin boolean;
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    removes_super_admin := OLD.is_super_admin
                        AND OLD.status = 'active'
                        AND OLD.deleted_at IS NULL;
                ELSE
                    removes_super_admin := OLD.is_super_admin
                        AND OLD.status = 'active'
                        AND OLD.deleted_at IS NULL
                        AND (
                            NOT NEW.is_super_admin
                            OR NEW.status <> 'active'
                            OR NEW.deleted_at IS NOT NULL
                        );
                END IF;

                IF removes_super_admin THEN
                    SELECT COUNT(*) INTO other_super_admins
                    FROM identity_users
                    WHERE id <> OLD.id
                      AND is_super_admin = TRUE
                      AND status = 'active'
                      AND deleted_at IS NULL;

                    IF other_super_admins = 0 THEN
                        RAISE EXCEPTION 'Cannot remove, demote, suspend, or delete the last active super admin';
                    END IF;
                END IF;

                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        )
    )
