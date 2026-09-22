"""Add SYSTEM-scoped Fair Stand settings admin permissions (read/update).

Revision ID: 20260922_0068
Revises: 20260922_0067
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260922_0068"
down_revision = "20260922_0067"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.admin.fair_stand"
SYSTEM_SCOPE = "system"
PERMISSIONS = (
    ("fair_crm.admin.fair_stand.settings.read", "Read Fair Stand stand envelope and runtime settings"),
    (
        "fair_crm.admin.fair_stand.settings.update",
        "Update Fair Stand stand envelope and runtime settings",
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    group_columns = {column["name"] for column in sa.inspect(connection).get_columns("identity_permission_groups")}
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code=:code LIMIT 1"),
        {"code": GROUP_CODE},
    ).scalar_one_or_none()
    if group_id is None:
        group_id = uuid.uuid4()
        if {"name", "module", "description", "sort_order", "is_system", "created_at", "updated_at"}.issubset(
            group_columns
        ):
            connection.execute(
                sa.text(
                    """
                    INSERT INTO identity_permission_groups
                        (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
                    VALUES
                        (:id, :code, 'FAIR CRM Fair Stand Admin', 'fair_crm',
                         'SYSTEM Super Admin Fair Stand catalog, preview, and settings administration', 96, TRUE,
                         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": str(group_id), "code": GROUP_CODE},
            )
        else:
            connection.execute(
                sa.text("INSERT INTO identity_permission_groups (id, code) VALUES (:id, :code)"),
                {"id": str(group_id), "code": GROUP_CODE},
            )
    elif {"name", "module", "description", "sort_order", "is_system", "updated_at"}.issubset(group_columns):
        connection.execute(
            sa.text(
                """
                UPDATE identity_permission_groups
                SET name='FAIR CRM Fair Stand Admin',
                    module='fair_crm',
                    description='SYSTEM Super Admin Fair Stand catalog, preview, and settings administration',
                    sort_order=96,
                    is_system=TRUE,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=:group_id
                """
            ),
            {"group_id": str(group_id)},
        )

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
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET group_id=:group_id,
                    description=:description,
                    is_system=TRUE,
                    lifecycle_state='active',
                    is_assignable=FALSE,
                    permission_scope=:permission_scope,
                    updated_at=CURRENT_TIMESTAMP
                WHERE code=:code
                """
            ),
            {
                "group_id": str(group_id),
                "code": code,
                "description": description,
                "permission_scope": SYSTEM_SCOPE,
            },
        )
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


def downgrade() -> None:
    connection = op.get_bind()
    codes = [code for code, _description in PERMISSIONS]
    for code in codes:
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
        connection.execute(sa.text("DELETE FROM identity_permissions WHERE code=:code"), {"code": code})
