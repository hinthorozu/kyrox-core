"""Add dedicated FAIR CRM mail send operation permissions.

Revision ID: 20260821_0062
Revises: 20260821_0061
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260821_0062"
down_revision = "20260821_0061"
branch_labels = None
depends_on = None

GROUP_CODE = "fair_crm.mail_send_operations"
GROUP_NAME = "FAIR CRM Mail Send Operations"
GROUP_DESCRIPTION = "FAIR CRM mail send operation permissions"

PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    (
        "fair_crm.mail_send_operations.read",
        "Read CRM mail send operations",
        "fair_crm.email_accounts.read",
    ),
    (
        "fair_crm.mail_send_operations.execute",
        "Execute CRM mail sends and retries",
        "fair_crm.email_accounts.update",
    ),
)


def _ensure_group(connection: sa.Connection) -> str:
    group_id = connection.execute(
        sa.text("SELECT id FROM identity_permission_groups WHERE code=:code LIMIT 1"),
        {"code": GROUP_CODE},
    ).scalar_one_or_none()
    if group_id is not None:
        return str(group_id)

    group_id = str(uuid.uuid4())
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_permission_groups
                (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
            VALUES
                (:id, :code, :name, 'fair_crm', :description, 70, TRUE,
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": group_id,
            "code": GROUP_CODE,
            "name": GROUP_NAME,
            "description": GROUP_DESCRIPTION,
        },
    )
    return group_id


def _ensure_permission(
    connection: sa.Connection,
    *,
    group_id: str,
    code: str,
    description: str,
) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_permissions
                (id, group_id, code, description, is_system, lifecycle_state,
                 is_assignable, permission_scope, created_at, updated_at)
            SELECT
                :id, :group_id, :code, :description, TRUE, 'active', TRUE,
                'organization', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM identity_permissions WHERE code=:code)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "group_id": group_id,
            "code": code,
            "description": description,
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
                is_assignable=TRUE,
                permission_scope='organization',
                updated_at=CURRENT_TIMESTAMP
            WHERE code=:code
            """
        ),
        {"group_id": group_id, "code": code, "description": description},
    )


def _copy_role_state(connection: sa.Connection, *, source_code: str, target_code: str) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT grants.role_id, target.id
            FROM identity_role_permissions AS grants
            JOIN identity_permissions AS source ON source.id=grants.permission_id
            CROSS JOIN identity_permissions AS target
            WHERE source.code=:source_code
              AND target.code=:target_code
            ON CONFLICT DO NOTHING
            """
        ),
        {"source_code": source_code, "target_code": target_code},
    )

    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_role_template_exclusions (role_id, permission_id)
                SELECT exclusions.role_id, target.id
                FROM identity_role_template_exclusions AS exclusions
                JOIN identity_permissions AS source ON source.id=exclusions.permission_id
                CROSS JOIN identity_permissions AS target
                WHERE source.code=:source_code
                  AND target.code=:target_code
                ON CONFLICT DO NOTHING
                """
            ),
            {"source_code": source_code, "target_code": target_code},
        )


def upgrade() -> None:
    connection = op.get_bind()
    group_id = _ensure_group(connection)

    for code, description, source_code in PERMISSIONS:
        _ensure_permission(connection, group_id=group_id, code=code, description=description)
        _copy_role_state(connection, source_code=source_code, target_code=code)


def downgrade() -> None:
    connection = op.get_bind()
    target_codes = tuple(code for code, _description, _source_code in PERMISSIONS)

    for code in target_codes:
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
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE code=:code"),
            {"code": code},
        )

    connection.execute(
        sa.text(
            """
            DELETE FROM identity_permission_groups
            WHERE code=:code
              AND NOT EXISTS (
                  SELECT 1 FROM identity_permissions
                  WHERE group_id=identity_permission_groups.id
              )
            """
        ),
        {"code": GROUP_CODE},
    )
