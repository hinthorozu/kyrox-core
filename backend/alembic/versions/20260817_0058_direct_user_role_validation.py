"""Validate role assignments through direct user organization ownership.

Revision ID: 20260817_0058
Revises: 20260817_0057
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260817_0058"
down_revision = "20260817_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION identity_validate_user_role_assignment()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM identity_users
                    WHERE id=NEW.user_id
                      AND is_super_admin=TRUE
                ) THEN
                    RAISE EXCEPTION 'Super Admin access cannot be represented by a role assignment';
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM identity_users
                    WHERE id=NEW.user_id
                      AND is_super_admin=FALSE
                      AND organization_id=NEW.organization_id
                ) THEN
                    RAISE EXCEPTION 'User must belong to the role organization';
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM identity_roles
                    WHERE id=NEW.role_id
                      AND deleted_at IS NULL
                      AND is_assignable=TRUE
                      AND (
                          role_kind='protected_global'
                          OR (
                              role_kind='organization'
                              AND organization_id=NEW.organization_id
                          )
                      )
                ) THEN
                    RAISE EXCEPTION 'Role is not assignable in this organization';
                END IF;

                RETURN NEW;
            END; $$;

            DROP TRIGGER IF EXISTS trg_identity_validate_user_role_assignment
            ON identity_user_roles;

            CREATE TRIGGER trg_identity_validate_user_role_assignment
            BEFORE INSERT OR UPDATE OF user_id, organization_id, role_id, status
            ON identity_user_roles
            FOR EACH ROW
            WHEN (NEW.status='active' AND NEW.revoked_at IS NULL)
            EXECUTE FUNCTION identity_validate_user_role_assignment();
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS trg_identity_validate_user_role_assignment
            ON identity_user_roles;
            DROP FUNCTION IF EXISTS identity_validate_user_role_assignment();
            """
        )
    )
