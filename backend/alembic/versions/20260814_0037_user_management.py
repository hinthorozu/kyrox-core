"""User management foundation.

Revision ID: 20260814_0037
Revises: 20260809_0036
Create Date: 2026-08-14

Adds forced-password-change state and reusable identity user-management permissions.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0037"
down_revision: Union[str, Sequence[str], None] = "20260809_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("identity.users.read", "Kullanıcıları görüntüle"),
    ("identity.users.create", "Kullanıcı oluştur"),
    ("identity.users.update", "Kullanıcı durumunu ve rollerini yönet"),
    ("identity.roles.read", "Rolleri ve izinleri görüntüle"),
    ("identity.roles.update", "Rol izinlerini yönet"),
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
            "WHERE slug = 'identity' AND deleted_at IS NULL LIMIT 1"
        )
    ).scalar_one_or_none()

    for code, name in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions
                    (id, code, name, group_id, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :code, :name, :group_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "name": name, "group_id": group_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    codes = [code for code, _ in PERMISSIONS]
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE code = ANY(:codes)"),
        {"codes": codes},
    )
    op.drop_column("identity_users", "must_change_password")
