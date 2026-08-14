"""User management foundation.

Revision ID: 20260814_0037
Revises: 20260809_0036
Create Date: 2026-08-14

Adds forced-password-change state and reusable identity user-management permissions.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0037"
down_revision: Union[str, Sequence[str], None] = "20260809_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("identity.users.read", "View organization users"),
    ("identity.users.create", "Create organization users"),
    ("identity.users.update", "Manage organization users and roles"),
    ("identity.roles.read", "View roles and permissions"),
    ("identity.roles.update", "Manage role permissions"),
)


def upgrade() -> None:
    op.add_column(
        "identity_users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    connection = op.get_bind()
    group_id = connection.execute(
        sa.text(
            "SELECT id FROM identity_permission_groups "
            "WHERE code = 'identity' LIMIT 1"
        )
    ).scalar_one()

    for code, description in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions
                    (id, group_id, code, description, is_system, created_at, updated_at)
                SELECT
                    :id, :group_id, :code, :description, :is_system,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (
                    SELECT 1 FROM identity_permissions WHERE code = :code
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "group_id": str(group_id),
                "code": code,
                "description": description,
                "is_system": True,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    for code, _ in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_role_permissions
                WHERE permission_id = (
                    SELECT id FROM identity_permissions WHERE code = :code
                )
                """
            ),
            {"code": code},
        )
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE code = :code"),
            {"code": code},
        )
    op.drop_column("identity_users", "must_change_password")
