"""Remove the dashboard read permission; dashboard access is membership-scoped.

Revision ID: 20260816_0054
Revises: 20260816_0053
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260816_0054"
down_revision = "20260816_0053"
branch_labels = None
depends_on = None

PERMISSION_CODE = "fair_crm.dashboard.read"
GROUP_CODE = "fair_crm.dashboard"
GROUP_NAME = "FAIR CRM Dashboard"
GROUP_DESCRIPTION = "FAIR CRM dashboard permissions"
GROUP_MODULE = "fair_crm"
GROUP_SORT_ORDER = 87
PERMISSION_DESCRIPTION = "Read CRM dashboard"


def upgrade() -> None:
    connection = op.get_bind()
    row = connection.execute(
        sa.text(
            """
            SELECT id, group_id
            FROM identity_permissions
            WHERE code=:code
            LIMIT 1
            """
        ),
        {"code": PERMISSION_CODE},
    ).mappings().first()

    if row is None:
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_permission_groups
                WHERE code=:group_code
                  AND NOT EXISTS (
                      SELECT 1 FROM identity_permissions
                      WHERE group_id=identity_permission_groups.id
                  )
                """
            ),
            {"group_code": GROUP_CODE},
        )
        return

    permission_id = row["id"]
    group_id = row["group_id"]

    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                "DELETE FROM identity_role_template_exclusions WHERE permission_id=:permission_id"
            ),
            {"permission_id": permission_id},
        )

    connection.execute(
        sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:permission_id"),
        {"permission_id": permission_id},
    )
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE id=:permission_id"),
        {"permission_id": permission_id},
    )
    connection.execute(
        sa.text(
            """
            DELETE FROM identity_permission_groups
            WHERE id=:group_id
              AND code=:group_code
              AND NOT EXISTS (
                  SELECT 1 FROM identity_permissions WHERE group_id=:group_id
              )
            """
        ),
        {"group_id": group_id, "group_code": GROUP_CODE},
    )


def downgrade() -> None:
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
                INSERT INTO identity_permission_groups (
                    id, code, name, module, description, sort_order,
                    is_system, created_at, updated_at
                ) VALUES (
                    :id, :code, :name, :module, :description, :sort_order,
                    TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(group_id),
                "code": GROUP_CODE,
                "name": GROUP_NAME,
                "module": GROUP_MODULE,
                "description": GROUP_DESCRIPTION,
                "sort_order": GROUP_SORT_ORDER,
            },
        )

    permission_id = connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code LIMIT 1"),
        {"code": PERMISSION_CODE},
    ).scalar_one_or_none()

    if permission_id is None:
        permission_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions (
                    id, group_id, code, description, is_system,
                    lifecycle_state, is_assignable, created_at, updated_at
                ) VALUES (
                    :id, :group_id, :code, :description, TRUE,
                    'active', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(permission_id),
                "group_id": str(group_id),
                "code": PERMISSION_CODE,
                "description": PERMISSION_DESCRIPTION,
            },
        )

    # Restore the permission to the built-in templates/role and their
    # uncustomized template-derived organization roles.
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT r.id, :permission_id
            FROM identity_roles r
            WHERE r.deleted_at IS NULL
              AND (
                  (
                      r.organization_id IS NULL
                      AND r.slug IN (
                          'organization_admin',
                          'read_user',
                          'create_update_user',
                          'full_user'
                      )
                  )
                  OR (
                      r.permissions_customized=FALSE
                      AND r.source_template_role_id IN (
                          SELECT id
                          FROM identity_roles
                          WHERE organization_id IS NULL
                            AND slug IN ('read_user', 'create_update_user', 'full_user')
                            AND deleted_at IS NULL
                      )
                  )
              )
            ON CONFLICT DO NOTHING
            """
        ),
        {"permission_id": permission_id},
    )
