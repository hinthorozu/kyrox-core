"""Add organization-scoped Fair Stand project CRUD + execute permissions.

Revision ID: 20260922_0067
Revises: 20260919_0066
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260922_0067"
down_revision = "20260919_0066"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.fair_stand.projects"
PERMISSIONS = (
    ("fair_crm.fair_stand.projects.read", "Read Fair Stand projects"),
    ("fair_crm.fair_stand.projects.create", "Create Fair Stand projects"),
    ("fair_crm.fair_stand.projects.update", "Update Fair Stand projects and upload assets"),
    ("fair_crm.fair_stand.projects.delete", "Delete Fair Stand projects"),
    ("fair_crm.fair_stand.projects.execute", "Export Fair Stand projects (ZIP/PNG download)"),
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
                    (:id, :code, 'FAIR CRM Fair Stand Projects', 'fair_crm',
                     'Organization-scoped Fair Stand project persistence permissions', 97, TRUE,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": str(group_id), "code": GROUP_CODE},
        )
    else:
        connection.execute(
            sa.text(
                """
                UPDATE identity_permission_groups
                SET name='FAIR CRM Fair Stand Projects',
                    module='fair_crm',
                    description='Organization-scoped Fair Stand project persistence permissions',
                    sort_order=97,
                    is_system=TRUE,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=:group_id
                """
            ),
            {"group_id": str(group_id)},
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
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET group_id=:group_id,
                    description=:description,
                    is_system=TRUE,
                    lifecycle_state='active',
                    is_assignable=TRUE,
                    permission_scope='organization',
                    updated_at=CURRENT_TIMESTAMP
                WHERE code=:code
                """
            ),
            {"group_id": str(group_id), "code": code, "description": description},
        )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM identity_roles r CROSS JOIN identity_permissions p
            WHERE r.organization_id IS NULL
              AND r.deleted_at IS NULL
              AND p.code LIKE 'fair_crm.fair_stand.projects.%'
              AND p.lifecycle_state='active'
              AND p.permission_scope='organization'
              AND (
                  r.slug='organization_admin'
                  OR r.slug='full_user'
                  OR (r.slug='read_user' AND p.code LIKE '%.read')
                  OR (
                      r.slug='create_update_user'
                      AND (
                          p.code LIKE '%.read'
                          OR p.code LIKE '%.create'
                          OR p.code LIKE '%.update'
                      )
                  )
              )
            ON CONFLICT DO NOTHING
            """
        )
    )

    # execute: FullUser + OrganizationAdmin only (export)
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM identity_roles r CROSS JOIN identity_permissions p
            WHERE r.organization_id IS NULL
              AND r.deleted_at IS NULL
              AND r.slug IN ('organization_admin', 'full_user')
              AND p.code='fair_crm.fair_stand.projects.execute'
              AND p.lifecycle_state='active'
              AND p.permission_scope='organization'
            ON CONFLICT DO NOTHING
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE identity_roles
            SET template_version=template_version + 1, updated_at=CURRENT_TIMESTAMP
            WHERE role_kind='template'
              AND organization_id IS NULL
              AND deleted_at IS NULL
              AND slug IN ('read_user', 'create_update_user', 'full_user')
            """
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT derived.id, template_permission.permission_id
            FROM identity_roles derived
            JOIN identity_roles template ON template.id=derived.source_template_role_id
            JOIN identity_role_permissions template_permission ON template_permission.role_id=template.id
            JOIN identity_permissions permission ON permission.id=template_permission.permission_id
            WHERE derived.role_kind='organization'
              AND derived.permissions_customized=FALSE
              AND derived.deleted_at IS NULL
              AND permission.code LIKE 'fair_crm.fair_stand.projects.%'
            ON CONFLICT DO NOTHING
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE identity_roles derived
            SET source_template_version=template.template_version, updated_at=CURRENT_TIMESTAMP
            FROM identity_roles template
            WHERE template.id=derived.source_template_role_id
              AND derived.role_kind='organization'
              AND derived.permissions_customized=FALSE
              AND derived.deleted_at IS NULL
              AND template.slug IN ('read_user', 'create_update_user', 'full_user')
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_role_template_exclusions
                WHERE permission_id IN (
                    SELECT id FROM identity_permissions
                    WHERE code LIKE 'fair_crm.fair_stand.projects.%'
                )
                """
            )
        )
    connection.execute(
        sa.text(
            """
            DELETE FROM identity_role_permissions
            WHERE permission_id IN (
                SELECT id FROM identity_permissions
                WHERE code LIKE 'fair_crm.fair_stand.projects.%'
            )
            """
        )
    )
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE code LIKE 'fair_crm.fair_stand.projects.%'")
    )
    connection.execute(
        sa.text("DELETE FROM identity_permission_groups WHERE code=:code"),
        {"code": GROUP_CODE},
    )
