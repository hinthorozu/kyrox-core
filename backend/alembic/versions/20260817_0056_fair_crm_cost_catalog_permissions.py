"""Seed organization-scoped FAIR CRM cost catalog permissions.

Revision ID: 20260817_0056
Revises: 20260816_0055
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260817_0056"
down_revision = "20260816_0055"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.cost_catalog"
PERMISSIONS = (
    ("fair_crm.cost_catalog.categories.read", "Read cost catalog categories"),
    ("fair_crm.cost_catalog.categories.create", "Create cost catalog categories"),
    ("fair_crm.cost_catalog.categories.update", "Update cost catalog categories"),
    ("fair_crm.cost_catalog.categories.delete", "Delete cost catalog categories"),
    ("fair_crm.cost_catalog.products.read", "Read cost catalog products"),
    ("fair_crm.cost_catalog.products.create", "Create cost catalog products"),
    ("fair_crm.cost_catalog.products.update", "Update cost catalog products"),
    ("fair_crm.cost_catalog.products.delete", "Delete cost catalog products"),
)


def upgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code=:code LIMIT 1"),
        {"code": GROUP_CODE},
    ).scalar_one_or_none()
    if group_id is None:
        group_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permission_groups
                    (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
                VALUES
                    (:id, :code, 'FAIR CRM Cost Catalog', 'fair_crm',
                     'FAIR CRM cost catalog category and product permissions', 92, TRUE,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": str(group_id), "code": GROUP_CODE},
        )

    for code, description in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions
                    (id, group_id, code, description, is_system, lifecycle_state,
                     is_assignable, permission_scope, created_at, updated_at)
                SELECT
                    :id, :group_id, :code, :description, TRUE, 'active', TRUE,
                    'organization', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code=:code)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "group_id": str(group_id),
                "code": code,
                "description": description,
            },
        )

    # OrganizationAdmin receives every organization permission through the Core
    # auto-include trigger. Governed templates need explicit action-level grants.
    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM identity_roles r CROSS JOIN identity_permissions p
        WHERE r.organization_id IS NULL
          AND r.deleted_at IS NULL
          AND p.code LIKE 'fair_crm.cost_catalog.%'
          AND p.lifecycle_state='active'
          AND p.permission_scope='organization'
          AND (
              r.slug='organization_admin'
              OR r.slug='full_user'
              OR (r.slug='read_user' AND p.code LIKE '%.read')
              OR (
                  r.slug='create_update_user'
                  AND (p.code LIKE '%.read' OR p.code LIKE '%.create' OR p.code LIKE '%.update')
              )
          )
        ON CONFLICT DO NOTHING
    """))

    connection.execute(sa.text("""
        UPDATE identity_roles
        SET template_version=template_version + 1, updated_at=CURRENT_TIMESTAMP
        WHERE role_kind='template'
          AND organization_id IS NULL
          AND deleted_at IS NULL
          AND slug IN ('read_user', 'create_update_user', 'full_user')
    """))

    connection.execute(sa.text("""
        INSERT INTO identity_role_permissions (role_id, permission_id)
        SELECT derived.id, template_permission.permission_id
        FROM identity_roles derived
        JOIN identity_roles template ON template.id=derived.source_template_role_id
        JOIN identity_role_permissions template_permission ON template_permission.role_id=template.id
        JOIN identity_permissions permission ON permission.id=template_permission.permission_id
        WHERE derived.role_kind='organization'
          AND derived.permissions_customized=FALSE
          AND derived.deleted_at IS NULL
          AND permission.code LIKE 'fair_crm.cost_catalog.%'
        ON CONFLICT DO NOTHING
    """))

    connection.execute(sa.text("""
        UPDATE identity_roles derived
        SET source_template_version=template.template_version, updated_at=CURRENT_TIMESTAMP
        FROM identity_roles template
        WHERE template.id=derived.source_template_role_id
          AND derived.role_kind='organization'
          AND derived.permissions_customized=FALSE
          AND derived.deleted_at IS NULL
          AND template.slug IN ('read_user', 'create_update_user', 'full_user')
    """))


def downgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(sa.text("""
            DELETE FROM identity_role_template_exclusions
            WHERE permission_id IN (
                SELECT id FROM identity_permissions WHERE code LIKE 'fair_crm.cost_catalog.%'
            )
        """))
    connection.execute(sa.text("""
        DELETE FROM identity_role_permissions
        WHERE permission_id IN (
            SELECT id FROM identity_permissions WHERE code LIKE 'fair_crm.cost_catalog.%'
        )
    """))
    connection.execute(sa.text("DELETE FROM identity_permissions WHERE code LIKE 'fair_crm.cost_catalog.%'"))
    connection.execute(sa.text("DELETE FROM identity_permission_groups WHERE code=:code"), {"code": GROUP_CODE})
