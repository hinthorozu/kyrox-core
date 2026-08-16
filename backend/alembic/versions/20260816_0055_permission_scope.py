"""Separate organization permissions from Super Admin system permissions.

Revision ID: 20260816_0055
Revises: 20260816_0054
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260816_0055"
down_revision = "20260816_0054"
branch_labels = None
depends_on = None

ORGANIZATION_SCOPE = "organization"
SYSTEM_SCOPE = "system"

SYSTEM_PERMISSION_CODES = (
    "fair_crm.admin.backups.read",
    "fair_crm.admin.backups.create",
    "fair_crm.admin.backups.execute",
    "identity.permissions.lifecycle",
    "identity.role_templates.read",
    "identity.role_templates.manage",
    "identity.organizations.delete",
)

SUSPEND_PERMISSION_CODE = "identity.organizations.suspend"
SUSPEND_PERMISSION_DESCRIPTION = "Suspend organizations"


def _permission_id(connection: sa.Connection, code: str):
    return connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code LIMIT 1"),
        {"code": code},
    ).scalar_one_or_none()


def _install_scope_aware_triggers(connection: sa.Connection) -> None:
    connection.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION identity_enforce_permission_lifecycle()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM identity_permissions
                    WHERE id=NEW.permission_id
                      AND lifecycle_state='active'
                      AND permission_scope='organization'
                ) THEN
                    RAISE EXCEPTION 'Permission is not an active organization permission and cannot be assigned';
                END IF;
                RETURN NEW;
            END; $$;

            DROP TRIGGER IF EXISTS trg_identity_permission_lifecycle ON identity_permissions;
            CREATE OR REPLACE FUNCTION identity_apply_permission_lifecycle()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.lifecycle_state='active' AND NEW.permission_scope='organization' THEN
                    INSERT INTO identity_role_permissions (role_id, permission_id)
                    SELECT id, NEW.id FROM identity_roles
                    WHERE auto_include_new_permissions=TRUE AND deleted_at IS NULL
                    ON CONFLICT DO NOTHING;
                ELSE
                    DELETE FROM identity_role_permissions WHERE permission_id=NEW.id;
                END IF;
                RETURN NEW;
            END; $$;
            CREATE TRIGGER trg_identity_permission_lifecycle
            AFTER UPDATE OF lifecycle_state, permission_scope ON identity_permissions
            FOR EACH ROW EXECUTE FUNCTION identity_apply_permission_lifecycle();

            CREATE OR REPLACE FUNCTION identity_grant_new_permission_to_auto_roles()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.lifecycle_state='active' AND NEW.permission_scope='organization' THEN
                    INSERT INTO identity_role_permissions (role_id, permission_id)
                    SELECT id, NEW.id FROM identity_roles
                    WHERE auto_include_new_permissions=TRUE AND deleted_at IS NULL
                    ON CONFLICT DO NOTHING;
                END IF;
                RETURN NEW;
            END; $$;
            """
        )
    )


def _install_legacy_triggers(connection: sa.Connection) -> None:
    connection.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION identity_enforce_permission_lifecycle()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM identity_permissions
                    WHERE id=NEW.permission_id AND lifecycle_state='active'
                ) THEN
                    RAISE EXCEPTION 'Permission is not active and cannot be assigned';
                END IF;
                RETURN NEW;
            END; $$;

            DROP TRIGGER IF EXISTS trg_identity_permission_lifecycle ON identity_permissions;
            CREATE OR REPLACE FUNCTION identity_apply_permission_lifecycle()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.lifecycle_state='active' THEN
                    INSERT INTO identity_role_permissions (role_id, permission_id)
                    SELECT id, NEW.id FROM identity_roles
                    WHERE auto_include_new_permissions=TRUE AND deleted_at IS NULL
                    ON CONFLICT DO NOTHING;
                ELSE
                    DELETE FROM identity_role_permissions WHERE permission_id=NEW.id;
                END IF;
                RETURN NEW;
            END; $$;
            CREATE TRIGGER trg_identity_permission_lifecycle
            AFTER UPDATE OF lifecycle_state ON identity_permissions
            FOR EACH ROW EXECUTE FUNCTION identity_apply_permission_lifecycle();

            CREATE OR REPLACE FUNCTION identity_grant_new_permission_to_auto_roles()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.lifecycle_state='active' THEN
                    INSERT INTO identity_role_permissions (role_id, permission_id)
                    SELECT id, NEW.id FROM identity_roles
                    WHERE auto_include_new_permissions=TRUE AND deleted_at IS NULL
                    ON CONFLICT DO NOTHING;
                END IF;
                RETURN NEW;
            END; $$;
            """
        )
    )


def upgrade() -> None:
    connection = op.get_bind()

    op.add_column(
        "identity_permissions",
        sa.Column(
            "permission_scope",
            sa.String(32),
            nullable=False,
            server_default=ORGANIZATION_SCOPE,
        ),
    )
    op.create_check_constraint(
        "ck_identity_permissions_permission_scope",
        "identity_permissions",
        "permission_scope IN ('organization', 'system')",
    )

    for code in SYSTEM_PERMISSION_CODES:
        if _permission_id(connection, code) is None:
            raise RuntimeError(f"Required permission is missing: {code}")

    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET permission_scope=:system_scope,
                is_assignable=FALSE,
                updated_at=CURRENT_TIMESTAMP
            WHERE code IN (
                'fair_crm.admin.backups.read',
                'fair_crm.admin.backups.create',
                'fair_crm.admin.backups.execute',
                'identity.permissions.lifecycle',
                'identity.role_templates.read',
                'identity.role_templates.manage',
                'identity.organizations.delete'
            )
            """
        ),
        {"system_scope": SYSTEM_SCOPE},
    )

    organization_group_id = connection.execute(
        sa.text(
            """
            SELECT group_id
            FROM identity_permissions
            WHERE code='identity.organizations.update'
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if organization_group_id is None:
        raise RuntimeError("identity.organizations.update permission group is missing")

    if _permission_id(connection, SUSPEND_PERMISSION_CODE) is None:
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions (
                    id, group_id, code, description, is_system,
                    lifecycle_state, is_assignable, permission_scope,
                    created_at, updated_at
                ) VALUES (
                    :id, :group_id, :code, :description, TRUE,
                    'active', FALSE, :permission_scope,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "group_id": str(organization_group_id),
                "code": SUSPEND_PERMISSION_CODE,
                "description": SUSPEND_PERMISSION_DESCRIPTION,
                "permission_scope": SYSTEM_SCOPE,
            },
        )

    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_role_template_exclusions
                WHERE permission_id IN (
                    SELECT id FROM identity_permissions WHERE permission_scope=:system_scope
                )
                """
            ),
            {"system_scope": SYSTEM_SCOPE},
        )

    connection.execute(
        sa.text(
            """
            DELETE FROM identity_role_permissions
            WHERE permission_id IN (
                SELECT id FROM identity_permissions WHERE permission_scope=:system_scope
            )
            """
        ),
        {"system_scope": SYSTEM_SCOPE},
    )

    _install_scope_aware_triggers(connection)


def downgrade() -> None:
    connection = op.get_bind()

    _install_legacy_triggers(connection)

    suspend_id = _permission_id(connection, SUSPEND_PERMISSION_CODE)
    if suspend_id is not None:
        if sa.inspect(connection).has_table("identity_role_template_exclusions"):
            connection.execute(
                sa.text(
                    "DELETE FROM identity_role_template_exclusions WHERE permission_id=:permission_id"
                ),
                {"permission_id": suspend_id},
            )
        connection.execute(
            sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:permission_id"),
            {"permission_id": suspend_id},
        )
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE id=:permission_id"),
            {"permission_id": suspend_id},
        )

    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET is_assignable=TRUE,
                permission_scope='organization',
                updated_at=CURRENT_TIMESTAMP
            WHERE code IN (
                'fair_crm.admin.backups.read',
                'fair_crm.admin.backups.create',
                'fair_crm.admin.backups.execute',
                'identity.organizations.delete'
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET permission_scope='organization',
                updated_at=CURRENT_TIMESTAMP
            WHERE code IN (
                'identity.permissions.lifecycle',
                'identity.role_templates.read',
                'identity.role_templates.manage'
            )
            """
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM identity_roles r
            CROSS JOIN identity_permissions p
            WHERE r.slug='organization_admin'
              AND r.organization_id IS NULL
              AND r.deleted_at IS NULL
              AND p.code IN (
                  'fair_crm.admin.backups.read',
                  'fair_crm.admin.backups.create',
                  'fair_crm.admin.backups.execute',
                  'identity.permissions.lifecycle',
                  'identity.role_templates.read',
                  'identity.role_templates.manage',
                  'identity.organizations.delete'
              )
              AND p.lifecycle_state='active'
            ON CONFLICT DO NOTHING
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM identity_roles r
            CROSS JOIN identity_permissions p
            WHERE r.role_kind='template'
              AND r.organization_id IS NULL
              AND r.deleted_at IS NULL
              AND p.lifecycle_state='active'
              AND p.is_assignable=TRUE
              AND (
                  (r.slug='read_user' AND (p.code LIKE '%.read' OR p.code LIKE '%.list'))
                  OR (
                      r.slug='create_update_user'
                      AND (
                          p.code LIKE '%.read' OR p.code LIKE '%.list'
                          OR p.code LIKE '%.create' OR p.code LIKE '%.update'
                      )
                  )
                  OR r.slug='full_user'
              )
            ON CONFLICT DO NOTHING
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT derived.id, template_permission.permission_id
            FROM identity_roles derived
            JOIN identity_role_permissions template_permission
              ON template_permission.role_id=derived.source_template_role_id
            WHERE derived.role_kind='organization'
              AND derived.permissions_customized=FALSE
              AND derived.source_template_role_id IS NOT NULL
              AND derived.deleted_at IS NULL
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.drop_constraint(
        "ck_identity_permissions_permission_scope",
        "identity_permissions",
        type_="check",
    )
    op.drop_column("identity_permissions", "permission_scope")
