"""Add SYSTEM-scoped organization reactivation permission.

Revision ID: 20260903_0065
Revises: 20260827_0064
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260903_0065"
down_revision = "20260827_0064"
branch_labels = None
depends_on = None

PERMISSION_CODE = "identity.organizations.reactivate"
PERMISSION_DESCRIPTION = "Reactivate organizations"
SYSTEM_SCOPE = "system"


def upgrade() -> None:
    connection = op.get_bind()

    group_id = connection.execute(
        sa.text(
            """
            SELECT group_id
            FROM identity_permissions
            WHERE code='identity.organizations.update'
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if group_id is None:
        raise RuntimeError("identity.organizations.update permission group is missing")

    permission_id = connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code LIMIT 1"),
        {"code": PERMISSION_CODE},
    ).scalar_one_or_none()

    if permission_id is None:
        permission_id = str(uuid.uuid4())
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
                "id": permission_id,
                "group_id": str(group_id),
                "code": PERMISSION_CODE,
                "description": PERMISSION_DESCRIPTION,
                "permission_scope": SYSTEM_SCOPE,
            },
        )
    else:
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET description=:description,
                    is_system=TRUE,
                    lifecycle_state='active',
                    is_assignable=FALSE,
                    permission_scope=:permission_scope,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=:permission_id
                """
            ),
            {
                "permission_id": str(permission_id),
                "description": PERMISSION_DESCRIPTION,
                "permission_scope": SYSTEM_SCOPE,
            },
        )

    connection.execute(
        sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:permission_id"),
        {"permission_id": str(permission_id)},
    )

    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                "DELETE FROM identity_role_template_exclusions WHERE permission_id=:permission_id"
            ),
            {"permission_id": str(permission_id)},
        )


def downgrade() -> None:
    connection = op.get_bind()
    permission_id = connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code LIMIT 1"),
        {"code": PERMISSION_CODE},
    ).scalar_one_or_none()
    if permission_id is None:
        return

    connection.execute(
        sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:permission_id"),
        {"permission_id": str(permission_id)},
    )
    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                "DELETE FROM identity_role_template_exclusions WHERE permission_id=:permission_id"
            ),
            {"permission_id": str(permission_id)},
        )
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE id=:permission_id"),
        {"permission_id": str(permission_id)},
    )
