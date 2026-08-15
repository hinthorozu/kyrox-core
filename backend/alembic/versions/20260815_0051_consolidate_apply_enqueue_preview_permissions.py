"""Consolidate apply/enqueue/preview permissions into common semantics.

Revision ID: 20260815_0051
Revises: 20260815_0050
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260815_0051"
down_revision = "20260815_0050"
branch_labels = None
depends_on = None

PERMISSION_RENAMES = (
    (
        "fair_crm.imports.apply",
        "fair_crm.imports.execute",
        "Execute CRM import application",
    ),
    (
        "jobs.platform.enqueue",
        "jobs.platform.execute",
        "Execute organization background jobs",
    ),
    (
        "fair_crm.fair_emails.preview",
        "fair_crm.fair_emails.read",
        "Read CRM fair email previews and batch history",
    ),
)

DOWNGRADE_RENAMES = (
    (
        "fair_crm.imports.execute",
        "fair_crm.imports.apply",
        "Apply CRM import batch decisions",
    ),
    (
        "jobs.platform.execute",
        "jobs.platform.enqueue",
        "Enqueue organization background jobs",
    ),
    (
        "fair_crm.fair_emails.read",
        "fair_crm.fair_emails.preview",
        "Preview CRM fair email recipients and content",
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
            "UPDATE identity_permissions "
            "SET description=:description, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=:new_id"
        ),
        {"new_id": new_id, "description": description},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for old_code, new_code, description in PERMISSION_RENAMES:
        _merge_permission(connection, old_code, new_code, description)


def downgrade() -> None:
    connection = op.get_bind()
    for old_code, new_code, description in DOWNGRADE_RENAMES:
        _merge_permission(connection, old_code, new_code, description)
