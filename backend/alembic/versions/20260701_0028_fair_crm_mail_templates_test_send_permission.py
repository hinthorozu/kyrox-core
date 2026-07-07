"""Add fair_crm.mail_templates.test_send permission for FAIR CRM product integration.

Revision ID: 20260701_0028
Revises: 20260701_0027
Create Date: 2026-07-05
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0028"
down_revision: Union[str, Sequence[str], None] = "20260701_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
GROUP_CODE = "fair_crm.mail_templates"
PERMISSION_CODE = "fair_crm.mail_templates.test_send"
PERMISSION_DESCRIPTION = "Send test email from CRM mail templates"


def upgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text(
            f"""
            SELECT id FROM {GROUPS_TABLE}
            WHERE code = :code
            LIMIT 1
            """
        ),
        {"code": GROUP_CODE},
    ).scalar()
    if group_id is None:
        raise RuntimeError(f"Permission group not found: {GROUP_CODE}")

    connection.execute(
        sa.text(
            f"""
            INSERT INTO {PERMISSIONS_TABLE} (
                id, group_id, code, description, is_system, created_at, updated_at
            )
            SELECT :id, :group_id, :code, :description, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM {PERMISSIONS_TABLE} WHERE code = :code
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "group_id": str(group_id),
            "code": PERMISSION_CODE,
            "description": PERMISSION_DESCRIPTION,
            "is_system": True,
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(f"DELETE FROM {PERMISSIONS_TABLE} WHERE code = :code"),
        {"code": PERMISSION_CODE},
    )
