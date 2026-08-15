"""Consolidate special action permissions under execute permissions.

Revision ID: 20260815_0049
Revises: 20260815_0048
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260815_0049"
down_revision = "20260815_0048"
branch_labels = None
depends_on = None

PERMISSION_RENAMES = (
    (
        "fair_crm.scraper.run",
        "fair_crm.scraper.execute",
        "Execute CRM scraper runs and output downloads",
    ),
    (
        "fair_crm.scraper.download",
        "fair_crm.scraper.execute",
        "Execute CRM scraper runs and output downloads",
    ),
    (
        "fair_crm.admin.backups.download",
        "fair_crm.admin.backups.execute",
        "Execute CRM database backup downloads",
    ),
    (
        "fair_crm.mail_templates.render",
        "fair_crm.mail_templates.execute",
        "Execute CRM mail template rendering",
    ),
    (
        "fair_crm.admin.data_operations.run",
        "fair_crm.admin.data_operations.execute",
        "Execute CRM admin data operations",
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

    scraper_run_id = _rename_permission_back(
        connection,
        "fair_crm.scraper.execute",
        "fair_crm.scraper.run",
        "Run CRM scraper adapters",
    )
    if scraper_run_id is not None:
        _clone_permission_with_grants(
            connection,
            source_id=scraper_run_id,
            code="fair_crm.scraper.download",
            description="Download CRM scraper run outputs",
        )

    _rename_permission_back(
        connection,
        "fair_crm.admin.backups.execute",
        "fair_crm.admin.backups.download",
        "Download CRM database backups",
    )
    _rename_permission_back(
        connection,
        "fair_crm.mail_templates.execute",
        "fair_crm.mail_templates.render",
        "Render CRM mail templates",
    )
    _rename_permission_back(
        connection,
        "fair_crm.admin.data_operations.execute",
        "fair_crm.admin.data_operations.run",
        "Run CRM admin data operations",
    )
