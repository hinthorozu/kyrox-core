"""Consolidate send-style permissions under execute permissions.

Revision ID: 20260815_0050
Revises: 20260815_0049
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260815_0050"
down_revision = "20260815_0049"
branch_labels = None
depends_on = None

PERMISSION_RENAMES = (
    (
        "notifications.platform.send",
        "notifications.platform.execute",
        "Execute organization notification delivery",
    ),
    (
        "fair_crm.fair_emails.send",
        "fair_crm.fair_emails.execute",
        "Execute CRM fair bulk email campaigns",
    ),
    (
        "fair_crm.mail_templates.test_send",
        "fair_crm.mail_templates.execute",
        "Execute CRM mail template rendering and test email delivery",
    ),
)


def _permission_id(connection, code: str):
    return connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code"),
        {"code": code},
    ).scalar_one_or_none()


def _merge_permission(connection, old_code: str, new_code: str, description: str) -> None:
    old_id = _permission_id(connection, old_code)
    if old_id is None:
        return

    new_id = _permission_id(connection, new_code)
    if new_id is None:
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET code=:new_code, description=:description, updated_at=CURRENT_TIMESTAMP
                WHERE id=:old_id
                """
            ),
            {"new_code": new_code, "description": description, "old_id": old_id},
        )
        return

    if new_id == old_id:
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT role_id, :new_id
            FROM identity_role_permissions
            WHERE permission_id=:old_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"old_id": old_id, "new_id": new_id},
    )

    inspector = sa.inspect(connection)
    if inspector.has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_role_template_exclusions (role_id, permission_id)
                SELECT role_id, :new_id
                FROM identity_role_template_exclusions
                WHERE permission_id=:old_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"old_id": old_id, "new_id": new_id},
        )
        connection.execute(
            sa.text("DELETE FROM identity_role_template_exclusions WHERE permission_id=:old_id"),
            {"old_id": old_id},
        )

    connection.execute(
        sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:old_id"),
        {"old_id": old_id},
    )
    connection.execute(
        sa.text("DELETE FROM identity_permissions WHERE id=:old_id"),
        {"old_id": old_id},
    )
    connection.execute(
        sa.text(
            "UPDATE identity_permissions SET description=:description, updated_at=CURRENT_TIMESTAMP WHERE id=:new_id"
        ),
        {"new_id": new_id, "description": description},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for old_code, new_code, description in PERMISSION_RENAMES:
        _merge_permission(connection, old_code, new_code, description)


def _rename_permission_back(connection, new_code: str, old_code: str, description: str):
    if _permission_id(connection, old_code) is not None:
        return _permission_id(connection, old_code)

    new_id = _permission_id(connection, new_code)
    if new_id is None:
        return None

    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET code=:old_code, description=:description, updated_at=CURRENT_TIMESTAMP
            WHERE id=:new_id
            """
        ),
        {"old_code": old_code, "description": description, "new_id": new_id},
    )
    return new_id


def _clone_permission_with_grants(
    connection,
    *,
    source_id,
    code: str,
    description: str,
) -> None:
    if _permission_id(connection, code) is not None:
        return

    row = connection.execute(
        sa.text(
            """
            SELECT group_id, is_system, lifecycle_state, is_assignable
            FROM identity_permissions
            WHERE id=:source_id
            """
        ),
        {"source_id": source_id},
    ).mappings().one()

    permission_id = uuid.uuid4()
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_permissions
                (id, group_id, code, description, is_system, lifecycle_state,
                 is_assignable, created_at, updated_at)
            VALUES
                (:id, :group_id, :code, :description, :is_system, :lifecycle_state,
                 :is_assignable, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": str(permission_id),
            "group_id": str(row["group_id"]),
            "code": code,
            "description": description,
            "is_system": row["is_system"],
            "lifecycle_state": row["lifecycle_state"],
            "is_assignable": row["is_assignable"],
        },
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT role_id, :permission_id
            FROM identity_role_permissions
            WHERE permission_id=:source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"source_id": source_id, "permission_id": permission_id},
    )

    inspector = sa.inspect(connection)
    if inspector.has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_role_template_exclusions (role_id, permission_id)
                SELECT role_id, :permission_id
                FROM identity_role_template_exclusions
                WHERE permission_id=:source_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"source_id": source_id, "permission_id": permission_id},
        )


def downgrade() -> None:
    connection = op.get_bind()

    _rename_permission_back(
        connection,
        "notifications.platform.execute",
        "notifications.platform.send",
        "Send organization notifications",
    )
    _rename_permission_back(
        connection,
        "fair_crm.fair_emails.execute",
        "fair_crm.fair_emails.send",
        "Send fair bulk email campaigns",
    )

    mail_templates_execute_id = _permission_id(connection, "fair_crm.mail_templates.execute")
    if mail_templates_execute_id is not None:
        _clone_permission_with_grants(
            connection,
            source_id=mail_templates_execute_id,
            code="fair_crm.mail_templates.test_send",
            description="Send test email from CRM mail templates",
        )
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET description=:description, updated_at=CURRENT_TIMESTAMP
                WHERE id=:permission_id
                """
            ),
            {
                "permission_id": mail_templates_execute_id,
                "description": "Execute CRM mail template rendering",
            },
        )
