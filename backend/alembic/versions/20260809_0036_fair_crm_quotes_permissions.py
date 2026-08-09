"""Seed FAIR CRM quote workflow permissions.

Revision ID: 20260809_0036
Revises: 20260809_0035
"""
import uuid
import sqlalchemy as sa
from alembic import op

revision = "20260809_0036"
down_revision = "20260809_0035"
branch_labels = None
depends_on = None
GROUP_CODE = "fair_crm.quotes"
PERMISSIONS = (
    ("fair_crm.quotes.read", "Read CRM quotes"),
    ("fair_crm.quotes.create", "Create CRM quotes"),
    ("fair_crm.quotes.update", "Update CRM quotes"),
    ("fair_crm.quotes.delete", "Delete CRM quotes"),
)


def upgrade():
    connection = op.get_bind()
    group_id = connection.execute(sa.text("SELECT id FROM identity_permission_groups WHERE code=:code"), {"code": GROUP_CODE}).scalar()
    if group_id is None:
        group_id = str(uuid.uuid4())
        connection.execute(sa.text("""INSERT INTO identity_permission_groups
            (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
            VALUES (:id, :code, 'FAIR CRM Quotes', 'fair_crm', 'Task-linked customer quote permissions', 89, :system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""),
            {"id": group_id, "code": GROUP_CODE, "system": True})
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
    connection.execute(sa.text("DELETE FROM identity_permission_groups WHERE code=:code"), {"code": GROUP_CODE})
