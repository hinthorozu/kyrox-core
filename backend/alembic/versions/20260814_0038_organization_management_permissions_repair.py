"""Repair organization management permissions after reused 0037 revision.

Revision ID: 20260814_0038
Revises: 20260814_0037
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260814_0038"
down_revision = "20260814_0037"
branch_labels = None
depends_on = None

GROUP_CODE = "identity"
OWNER_ROLE_SLUG = "owner"
PERMISSIONS = (
    ("identity.organizations.read", "Read organizations"),
    ("identity.organizations.update", "Update organizations"),
    ("identity.organizations.delete", "Delete organizations"),
)


def upgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code=:code"),
        {"code": GROUP_CODE},
    ).scalar_one()

    for code, description in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions
                    (id, group_id, code, description, is_system, created_at, updated_at)
                SELECT :id, :group_id, :code, :description, :system,
                       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (
                    SELECT 1 FROM identity_permissions WHERE code=:code
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "group_id": str(group_id),
                "code": code,
                "description": description,
                "system": True,
            },
        )

    owner_role_id = connection.execute(
        sa.text(
            """
            SELECT id FROM identity_roles
            WHERE scope='organization' AND slug=:slug AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"slug": OWNER_ROLE_SLUG},
    ).scalar()
    if owner_role_id is None:
        return

    for code, _ in PERMISSIONS:
        permission_id = connection.execute(
            sa.text("SELECT id FROM identity_permissions WHERE code=:code"),
            {"code": code},
        ).scalar_one()
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_role_permissions (role_id, permission_id)
                SELECT :role_id, :permission_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM identity_role_permissions
                    WHERE role_id=:role_id AND permission_id=:permission_id
                )
                """
            ),
            {"role_id": str(owner_role_id), "permission_id": str(permission_id)},
        )


def downgrade() -> None:
    # This is a repair migration. The permissions may legitimately have been
    # created by 0037 on databases that never saw the historical reused 0037.
    # Removing them here would make downgrade behavior depend on deployment
    # history, so downgrade intentionally leaves the repaired data intact.
    pass
