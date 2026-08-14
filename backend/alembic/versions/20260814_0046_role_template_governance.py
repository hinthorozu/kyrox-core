"""Introduce governed role templates and direct organization role assignments.

Revision ID: 20260814_0046
Revises: 20260814_0045
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260814_0046"
down_revision = "20260814_0045"
branch_labels = None
depends_on = None

TEMPLATES = (
    ("ReadUser", "read_user", "read"),
    ("CreateUpdateUser", "create_update_user", "create_update"),
    ("FullUser", "full_user", "full"),
)

GOVERNANCE_PERMISSIONS = (
    ("identity.roles.create", "Create organization roles", True),
    ("identity.roles.delete", "Delete organization roles", True),
    ("identity.roles.assign", "Assign organization roles", True),
    ("identity.roles.assign_protected", "Assign protected system roles", False),
    ("identity.role_templates.read", "Read global role templates", False),
    ("identity.role_templates.manage", "Manage and synchronize global role templates", False),
    ("identity.permissions.read", "Read permission catalog", True),
    ("identity.permissions.lifecycle", "Lock and activate platform permissions", False),
)


def _drop_foreign_keys_for_column(table: str, column: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table):
        if column in foreign_key.get("constrained_columns", ()) and foreign_key.get("name"):
            op.drop_constraint(foreign_key["name"], table, type_="foreignkey")


def upgrade() -> None:
    op.add_column("identity_roles", sa.Column("role_kind", sa.String(32), nullable=False, server_default="organization"))
    op.add_column("identity_roles", sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("identity_roles", sa.Column("source_template_role_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("identity_roles", sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("identity_roles", sa.Column("source_template_version", sa.Integer(), nullable=True))
    op.add_column("identity_roles", sa.Column("permissions_customized", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("identity_roles", sa.Column("is_assignable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("identity_roles", sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("identity_roles", sa.Column("auto_include_new_permissions", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key("fk_identity_roles_organization", "identity_roles", "identity_organizations", ["organization_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE")
    op.create_foreign_key("fk_identity_roles_source_template", "identity_roles", "identity_roles", ["source_template_role_id"], ["id"], ondelete="SET NULL", onupdate="CASCADE")

    op.add_column("identity_permissions", sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="active"))
    op.add_column("identity_permissions", sa.Column("is_assignable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("identity_permissions", sa.Column("lifecycle_reason", sa.String(512), nullable=True))
    op.add_column("identity_permissions", sa.Column("lifecycle_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("identity_permissions", sa.Column("lifecycle_changed_by", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_identity_permissions_lifecycle_actor", "identity_permissions", "identity_users", ["lifecycle_changed_by"], ["id"], ondelete="SET NULL", onupdate="CASCADE")

    op.add_column("identity_user_roles", sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=True))
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE identity_user_roles ur
        SET role_id = organization_role.role_id
        FROM identity_organization_roles organization_role
        WHERE organization_role.id = ur.organization_role_id
    """))
    op.alter_column("identity_user_roles", "role_id", nullable=False)
    op.create_foreign_key("fk_identity_user_roles_role", "identity_user_roles", "identity_roles", ["role_id"], ["id"], ondelete="CASCADE", onupdate="CASCADE")
    op.create_index("ix_identity_user_roles_role_id", "identity_user_roles", ["role_id"])

    connection.execute(sa.text("""
        UPDATE identity_roles
        SET role_kind='protected_global', is_assignable=TRUE, is_protected=TRUE,
            auto_include_new_permissions=TRUE, is_system=TRUE
        WHERE slug='organization_admin' AND deleted_at IS NULL
    """))

    group_id = connection.execute(sa.text("SELECT id FROM identity_permission_groups WHERE code='identity'")).scalar_one()
    for code, description, assignable in GOVERNANCE_PERMISSIONS:
        connection.execute(sa.text("""
            INSERT INTO identity_permissions
                (id, group_id, code, description, is_system, lifecycle_state,
                 is_assignable, created_at, updated_at)
            SELECT :id, :group_id, :code, :description, TRUE, 'active',
                   :assignable, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code=:code)
        """), {"id": str(uuid.uuid4()), "group_id": str(group_id), "code": code, "description": description, "assignable": assignable})
        connection.execute(sa.text("UPDATE identity_permissions SET is_assignable=:assignable WHERE code=:code"), {"code": code, "assignable": assignable})

    for name, slug, _ in TEMPLATES:
        connection.execute(sa.text("""
            INSERT INTO identity_roles
                (id, name, slug, scope, is_system, role_kind, organization_id,
                 template_version, permissions_customized, is_assignable,
                 is_protected, auto_include_new_permissions, created_at, updated_at)
            SELECT :id, :name, :slug, 'organization', TRUE, 'template', NULL,
                   1, FALSE, FALSE, TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM identity_roles WHERE slug=:slug AND organization_id IS NULL
                  AND deleted_at IS NULL
            )
        """), {"id": str(uuid.uuid4()), "name": name, "slug": slug})

    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.slug='organization_admin' AND r.deleted_at IS NULL
          AND p.lifecycle_state='active'
        ON CONFLICT DO NOTHING
    """))
    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.slug='read_user' AND r.role_kind='template'
          AND p.lifecycle_state='active' AND p.is_assignable=TRUE
          AND (p.code LIKE '%.read' OR p.code LIKE '%.list')
        ON CONFLICT DO NOTHING
    """))
    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.slug='create_update_user' AND r.role_kind='template'
          AND p.lifecycle_state='active' AND p.is_assignable=TRUE
          AND (p.code LIKE '%.read' OR p.code LIKE '%.list' OR p.code LIKE '%.create' OR p.code LIKE '%.update')
        ON CONFLICT DO NOTHING
    """))
    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.slug='full_user' AND r.role_kind='template'
          AND p.lifecycle_state='active' AND p.is_assignable=TRUE
        ON CONFLICT DO NOTHING
    """))

    op.create_table(
        "identity_role_template_exclusions",
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("permission_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["identity_permissions.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.drop_constraint("uq_identity_roles_scope_slug", "identity_roles", type_="unique")
    op.create_index("uq_identity_roles_global_slug", "identity_roles", ["slug"], unique=True, postgresql_where=sa.text("organization_id IS NULL AND deleted_at IS NULL"))
    op.create_index("uq_identity_roles_organization_slug", "identity_roles", ["organization_id", "slug"], unique=True, postgresql_where=sa.text("organization_id IS NOT NULL AND deleted_at IS NULL"))

    op.drop_index("ix_identity_user_roles_organization_role_id", table_name="identity_user_roles")
    _drop_foreign_keys_for_column("identity_user_roles", "organization_role_id")
    op.drop_column("identity_user_roles", "organization_role_id")
    op.drop_table("identity_organization_roles")

    connection.execute(sa.text("""
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
        CREATE TRIGGER trg_identity_role_permission_lifecycle
        BEFORE INSERT OR UPDATE ON identity_role_permissions
        FOR EACH ROW EXECUTE FUNCTION identity_enforce_permission_lifecycle();

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
        CREATE TRIGGER trg_identity_new_permission_auto_grant
        AFTER INSERT ON identity_permissions
        FOR EACH ROW EXECUTE FUNCTION identity_grant_new_permission_to_auto_roles();
    """))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_identity_new_permission_auto_grant ON identity_permissions; DROP FUNCTION IF EXISTS identity_grant_new_permission_to_auto_roles(); DROP TRIGGER IF EXISTS trg_identity_permission_lifecycle ON identity_permissions; DROP FUNCTION IF EXISTS identity_apply_permission_lifecycle(); DROP TRIGGER IF EXISTS trg_identity_role_permission_lifecycle ON identity_role_permissions; DROP FUNCTION IF EXISTS identity_enforce_permission_lifecycle();"))
    op.create_table(
        "identity_organization_roles",
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["identity_roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "role_id", name="uq_identity_organization_roles_organization_role"),
    )
    op.add_column("identity_user_roles", sa.Column("organization_role_id", sa.Uuid(as_uuid=True), nullable=True))
    connection.execute(sa.text("""
        INSERT INTO identity_organization_roles (id, organization_id, role_id, status, is_default, created_at, updated_at)
        SELECT gen_random_uuid(), ur.organization_id, ur.role_id, 'active', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM identity_user_roles ur GROUP BY ur.organization_id, ur.role_id;
        UPDATE identity_user_roles ur SET organization_role_id=orr.id
        FROM identity_organization_roles orr
        WHERE orr.organization_id=ur.organization_id AND orr.role_id=ur.role_id;
    """))
    op.alter_column("identity_user_roles", "organization_role_id", nullable=False)
    op.create_foreign_key("fk_identity_user_roles_organization_role", "identity_user_roles", "identity_organization_roles", ["organization_role_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_identity_user_roles_organization_role_id", "identity_user_roles", ["organization_role_id"])
    op.drop_index("ix_identity_user_roles_role_id", table_name="identity_user_roles")
    _drop_foreign_keys_for_column("identity_user_roles", "role_id")
    op.drop_column("identity_user_roles", "role_id")
    op.drop_table("identity_role_template_exclusions")
    op.drop_index("uq_identity_roles_organization_slug", table_name="identity_roles")
    op.drop_index("uq_identity_roles_global_slug", table_name="identity_roles")
    op.create_unique_constraint("uq_identity_roles_scope_slug", "identity_roles", ["scope", "slug"])
    for column in ("auto_include_new_permissions", "is_protected", "is_assignable", "permissions_customized", "source_template_version", "template_version", "source_template_role_id", "organization_id", "role_kind"):
        if column in ("organization_id", "source_template_role_id"):
            _drop_foreign_keys_for_column("identity_roles", column)
        op.drop_column("identity_roles", column)
    _drop_foreign_keys_for_column("identity_permissions", "lifecycle_changed_by")
    for column in ("lifecycle_changed_by", "lifecycle_changed_at", "lifecycle_reason", "is_assignable", "lifecycle_state"):
        op.drop_column("identity_permissions", column)
