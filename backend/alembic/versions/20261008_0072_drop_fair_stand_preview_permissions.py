"""Drop Fair Stand catalog preview permissions.

Catalog preview administration uses fair_crm.admin.fair_stand.catalog.*.
The shared fair_crm.admin.fair_stand group stays; catalog, settings, and
item permissions still belong to it.

Revision ID: 20261008_0072
Revises: 20261007_0071
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20261008_0072"
down_revision = "20261007_0071"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.admin.fair_stand"
SYSTEM_SCOPE = "system"
PERMISSIONS = (
    ("fair_crm.admin.fair_stand.previews.read", "Read Fair Stand catalog previews"),
    ("fair_crm.admin.fair_stand.previews.create", "Create Fair Stand catalog previews"),
    ("fair_crm.admin.fair_stand.previews.update", "Update Fair Stand catalog previews"),
    ("fair_crm.admin.fair_stand.previews.archive", "Archive Fair Stand catalog previews"),
)


def _delete_grants(connection: sa.Connection, code: str) -> None:
    connection.execute(
        sa.text(
            """
            DELETE FROM identity_role_permissions
            WHERE permission_id IN (
                SELECT id FROM identity_permissions WHERE code=:code
            )
            """
        ),
        {"code": code},
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
            {"code": code},
        )


def upgrade() -> None:
    connection = op.get_bind()
    for code, _description in PERMISSIONS:
        _delete_grants(connection, code)
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE code=:code"),
            {"code": code},
        )


def downgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code=:code LIMIT 1"),
        {"code": GROUP_CODE},
    ).scalar_one_or_none()
    if group_id is None:
        return
    for code, description in PERMISSIONS:
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
                "code": code,
                "description": description,
                "permission_scope": SYSTEM_SCOPE,
            },
        )
