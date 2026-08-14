"""Seed reusable user management permissions.

Revision ID: 20260814_0044
Revises: 20260814_0043
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260814_0044"
down_revision = "20260814_0043"
branch_labels = None
depends_on = None

GROUP_CODE = "identity"
ORGANIZATION_ADMIN_ROLE_SLUG = "organization_admin"
PERMISSIONS = (
    ("identity.users.read", "Read organization users"),
    ("identity.users.create", "Create organization users"),
    ("identity.users.update", "Update and remove organization users"),
    ("identity.roles.read", "Read assignable organization roles"),
    ("identity.roles.update", "Manage organization role assignments"),
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
                SELECT :id, :group_id, :code, :description, TRUE,
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
            },
        )

    role_id = connection.execute(
        sa.text(
            """
            SELECT id FROM identity_roles
            WHERE slug=:slug AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"slug": ORGANIZATION_ADMIN_ROLE_SLUG},
    ).scalar()
    if role_id is None:
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
            {"role_id": str(role_id), "permission_id": str(permission_id)},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for code, _ in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_role_permissions
                WHERE permission_id=(SELECT id FROM identity_permissions WHERE code=:code)
                """
            ),
            {"code": code},
        )
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE code=:code"),
            {"code": code},
        )
