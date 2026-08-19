"""Add organization-scoped customer execute permission for export operations.

Revision ID: 20260820_0060
Revises: 20260817_0059
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260820_0060"
down_revision = "20260817_0059"
branch_labels = None
depends_on = None

PERMISSION_CODE = "fair_crm.customers.execute"
PERMISSION_DESCRIPTION = "Execute customer operations such as export"
GROUP_CODE = "fair_crm.customers"


def upgrade() -> None:
    connection = op.get_bind()

    group_id = connection.execute(
        sa.text(
            "SELECT group_id FROM identity_permissions "
            "WHERE code='fair_crm.customers.read' LIMIT 1"
        )
    ).scalar_one_or_none()

    if group_id is None:
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
                    (:id, :code, 'FAIR CRM Customers', 'fair_crm',
                     'FAIR CRM customer module permissions', 10, TRUE,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": str(group_id), "code": GROUP_CODE},
        )

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
            "code": PERMISSION_CODE,
            "description": PERMISSION_DESCRIPTION,
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
        {
            "group_id": str(group_id),
            "code": PERMISSION_CODE,
            "description": PERMISSION_DESCRIPTION,
        },
    )

    # Execute is a full-access capability. OrganizationAdmin and FullUser get it;
    # ReadUser and CreateUpdateUser do not.
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT role.id, permission.id
            FROM identity_roles AS role
            CROSS JOIN identity_permissions AS permission
            WHERE role.organization_id IS NULL
              AND role.deleted_at IS NULL
              AND role.slug IN ('organization_admin', 'full_user')
              AND permission.code=:code
              AND permission.lifecycle_state='active'
              AND permission.permission_scope='organization'
            ON CONFLICT DO NOTHING
            """
        ),
        {"code": PERMISSION_CODE},
    )

    connection.execute(
        sa.text(
            """
            UPDATE identity_roles
            SET template_version=template_version + 1,
                updated_at=CURRENT_TIMESTAMP
            WHERE role_kind='template'
              AND organization_id IS NULL
              AND deleted_at IS NULL
              AND slug='full_user'
            """
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT derived.id, permission.id
            FROM identity_roles AS derived
            JOIN identity_roles AS template ON template.id=derived.source_template_role_id
            CROSS JOIN identity_permissions AS permission
            WHERE derived.role_kind='organization'
              AND derived.permissions_customized=FALSE
              AND derived.deleted_at IS NULL
              AND template.slug='full_user'
              AND permission.code=:code
            ON CONFLICT DO NOTHING
            """
        ),
        {"code": PERMISSION_CODE},
    )

    connection.execute(
        sa.text(
            """
            UPDATE identity_roles AS derived
            SET source_template_version=template.template_version,
                updated_at=CURRENT_TIMESTAMP
            FROM identity_roles AS template
            WHERE template.id=derived.source_template_role_id
              AND derived.role_kind='organization'
              AND derived.permissions_customized=FALSE
              AND derived.deleted_at IS NULL
              AND template.slug='full_user'
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
                    SELECT id FROM identity_permissions WHERE code=:code
                )
                """
            ),
            {"code": PERMISSION_CODE},
        )
    connection.execute(
        sa.text(
            """
            DELETE FROM identity_role_permissions
            WHERE permission_id IN (
                SELECT id FROM identity_permissions WHERE code=:code
            )
            """
        ),
        {"code": PERMISSION_CODE},
    )
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE code=:code"),
        {"code": PERMISSION_CODE},
    )
