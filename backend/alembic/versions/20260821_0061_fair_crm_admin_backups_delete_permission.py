"""Add Super Admin-only FAIR CRM backup delete permission.

Revision ID: 20260821_0061
Revises: 20260820_0060
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260821_0061"
down_revision = "20260820_0060"
branch_labels = None
depends_on = None

PERMISSION_CODE = "fair_crm.admin.backups.delete"
PERMISSION_DESCRIPTION = "Delete CRM database backups and restore jobs"
SYSTEM_SCOPE = "system"


def upgrade() -> None:
    connection = op.get_bind()

    group_id = connection.execute(
        sa.text(
            "SELECT group_id FROM identity_permissions "
            "WHERE code='fair_crm.admin.backups.read' LIMIT 1"
        )
    ).scalar_one_or_none()
    if group_id is None:
        raise RuntimeError("FAIR CRM admin backups permission group is missing")

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_permissions
                (id, group_id, code, description, is_system, lifecycle_state,
                 is_assignable, permission_scope, created_at, updated_at)
            SELECT
                :id, :group_id, :code, :description, TRUE, 'active', FALSE,
                :permission_scope, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code=:code)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "group_id": str(group_id),
            "code": PERMISSION_CODE,
            "description": PERMISSION_DESCRIPTION,
            "permission_scope": SYSTEM_SCOPE,
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
                is_assignable=FALSE,
                permission_scope=:permission_scope,
                updated_at=CURRENT_TIMESTAMP
            WHERE code=:code
            """
        ),
        {
            "group_id": str(group_id),
            "code": PERMISSION_CODE,
            "description": PERMISSION_DESCRIPTION,
            "permission_scope": SYSTEM_SCOPE,
        },
    )

    # System-scoped permissions are Super Admin capabilities and must never be
    # granted through organization or template roles.
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
