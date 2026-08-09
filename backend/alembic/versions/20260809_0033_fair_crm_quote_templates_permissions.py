"""Seed FAIR CRM quote template permissions.

Revision ID: 20260809_0033
Revises: 20260701_0032
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0033"
down_revision: Union[str, Sequence[str], None] = "20260701_0032"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.quote_templates"
PERMISSIONS = (
    ("fair_crm.quote_templates.read", "Read CRM quote templates"),
    ("fair_crm.quote_templates.create", "Create CRM quote templates"),
    ("fair_crm.quote_templates.update", "Update CRM quote templates"),
)


def upgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code = :code LIMIT 1"),
        {"code": GROUP_CODE},
    ).scalar()
    if group_id is None:
        group_id = str(uuid.uuid4())
        connection.execute(sa.text("""
            INSERT INTO identity_permission_groups
                (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
            VALUES
                (:id, :code, :name, 'fair_crm', :description, 87, :is_system,
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {
            "id": group_id,
            "code": GROUP_CODE,
            "name": "FAIR CRM Quote Templates",
            "description": "FAIR CRM quote template permissions",
            "is_system": True,
        })
    for code, description in PERMISSIONS:
        connection.execute(sa.text("""
            INSERT INTO identity_permissions
                (id, group_id, code, description, is_system, created_at, updated_at)
            SELECT :id, :group_id, :code, :description, :is_system,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code = :code)
        """), {
            "id": str(uuid.uuid4()), "group_id": str(group_id), "code": code,
            "description": description, "is_system": True,
        })


def downgrade() -> None:
    connection = op.get_bind()
    for code, _ in PERMISSIONS:
        connection.execute(sa.text("DELETE FROM identity_permissions WHERE code = :code"), {"code": code})
    connection.execute(sa.text("DELETE FROM identity_permission_groups WHERE code = :code"), {"code": GROUP_CODE})
