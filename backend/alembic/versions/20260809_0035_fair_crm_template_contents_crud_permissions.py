"""Add update/delete permissions for template contents.

Revision ID: 20260809_0035
Revises: 20260809_0034
"""
from __future__ import annotations
import uuid
import sqlalchemy as sa
from alembic import op

revision = "20260809_0035"
down_revision = "20260809_0034"
branch_labels = None
depends_on = None
GROUP_CODE = "fair_crm.template_contents"
PERMISSIONS = (
    ("fair_crm.template_contents.update", "Update CRM template contents"),
    ("fair_crm.template_contents.delete", "Delete CRM template contents"),
)


def upgrade():
    connection = op.get_bind()
    group_id = connection.execute(sa.text("SELECT id FROM identity_permission_groups WHERE code=:code"), {"code": GROUP_CODE}).scalar_one()
    for code, description in PERMISSIONS:
        connection.execute(sa.text("""INSERT INTO identity_permissions
            (id, group_id, code, description, is_system, created_at, updated_at)
            SELECT :id, :group_id, :code, :description, :system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code=:code)"""),
            {"id": str(uuid.uuid4()), "group_id": str(group_id), "code": code, "description": description, "system": True})


def downgrade():
    connection = op.get_bind()
    for code, _ in PERMISSIONS:
        connection.execute(sa.text("DELETE FROM identity_role_permissions WHERE permission_id=(SELECT id FROM identity_permissions WHERE code=:code)"), {"code": code})
        connection.execute(sa.text("DELETE FROM identity_permissions WHERE code=:code"), {"code": code})
