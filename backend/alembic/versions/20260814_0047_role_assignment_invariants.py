"""Enforce direct role assignment and active-permission invariants.

Revision ID: 20260814_0047
Revises: 20260814_0046
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260814_0047"
down_revision = "20260814_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM identity_user_roles ur
        USING identity_users u
        WHERE u.id=ur.user_id AND u.is_super_admin=TRUE;

        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.auto_include_new_permissions=TRUE AND r.deleted_at IS NULL
          AND p.lifecycle_state='active'
        ON CONFLICT DO NOTHING;

        CREATE OR REPLACE FUNCTION identity_apply_permission_lifecycle()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.lifecycle_state = 'active' THEN
                INSERT INTO identity_role_permissions (role_id, permission_id)
                SELECT id, NEW.id FROM identity_roles
                WHERE auto_include_new_permissions=TRUE AND deleted_at IS NULL
                ON CONFLICT DO NOTHING;
            ELSE
                DELETE FROM identity_role_permissions WHERE permission_id=NEW.id;
            END IF;
            RETURN NEW;
        END; $$;

        CREATE OR REPLACE FUNCTION identity_validate_user_role_assignment()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM identity_users
                WHERE id=NEW.user_id AND is_super_admin=TRUE
            ) THEN
                RAISE EXCEPTION 'Super Admin access cannot be represented by a role assignment';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM identity_memberships
                WHERE user_id=NEW.user_id AND organization_id=NEW.organization_id
                  AND status='active' AND deleted_at IS NULL
            ) THEN
                RAISE EXCEPTION 'Active organization membership is required for role assignment';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM identity_roles
                WHERE id=NEW.role_id AND deleted_at IS NULL AND is_assignable=TRUE
                  AND (
                    role_kind='protected_global'
                    OR (role_kind='organization' AND organization_id=NEW.organization_id)
                  )
            ) THEN
                RAISE EXCEPTION 'Role is not assignable in this organization';
            END IF;
            RETURN NEW;
        END; $$;
        DROP TRIGGER IF EXISTS trg_identity_validate_user_role_assignment ON identity_user_roles;
        CREATE TRIGGER trg_identity_validate_user_role_assignment
        BEFORE INSERT OR UPDATE OF user_id, organization_id, role_id, status
        ON identity_user_roles
        FOR EACH ROW
        WHEN (NEW.status='active' AND NEW.revoked_at IS NULL)
        EXECUTE FUNCTION identity_validate_user_role_assignment();
    """))

    op.create_check_constraint(
        "ck_identity_roles_kind_scope",
        "identity_roles",
        "(role_kind IN ('protected_global', 'template') AND organization_id IS NULL) OR "
        "(role_kind = 'organization' AND organization_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_identity_roles_kind_scope", "identity_roles", type_="check")
    connection = op.get_bind()
    connection.execute(sa.text("""
        DROP TRIGGER IF EXISTS trg_identity_validate_user_role_assignment ON identity_user_roles;
        DROP FUNCTION IF EXISTS identity_validate_user_role_assignment();
        CREATE OR REPLACE FUNCTION identity_apply_permission_lifecycle()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.lifecycle_state <> 'active' THEN
                DELETE FROM identity_role_permissions WHERE permission_id=NEW.id;
            END IF;
            RETURN NEW;
        END; $$;
    """))
