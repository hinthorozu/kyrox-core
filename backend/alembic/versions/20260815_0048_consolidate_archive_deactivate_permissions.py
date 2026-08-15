"""Consolidate archive/deactivate permissions under delete permissions.

Revision ID: 20260815_0048
Revises: 20260814_0047
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260815_0048"
down_revision = "20260814_0047"
branch_labels = None
depends_on = None

PERMISSION_RENAMES = (
    ("fair_crm.customers.archive", "fair_crm.customers.delete", "Delete or archive CRM customers"),
    ("fair_crm.fairs.archive", "fair_crm.fairs.delete", "Delete or archive CRM fairs"),
    ("fair_crm.todos.archive", "fair_crm.todos.delete", "Delete or archive CRM todos"),
    (
        "fair_crm.todos.outcomes.deactivate",
        "fair_crm.todos.outcomes.delete",
        "Delete or deactivate CRM todo outcomes",
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


def _restore_permission(connection, old_code: str, new_code: str, description: str) -> None:
    if _permission_id(connection, old_code) is not None:
        return

    new_id = _permission_id(connection, new_code)
    if new_id is None:
        return

    # todos.delete existed before this migration, so recreating todos.archive must
    # preserve delete and copy its current grants. The other targets were introduced
    # by the upgrade and can safely be renamed back when no legacy target existed.
    if old_code == "fair_crm.todos.archive":
        row = connection.execute(
            sa.text(
                """
                SELECT group_id, is_system, lifecycle_state, is_assignable
                FROM identity_permissions WHERE id=:new_id
                """
            ),
            {"new_id": new_id},
        ).mappings().one()
        old_id = uuid.uuid4()
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
                "id": str(old_id),
                "group_id": str(row["group_id"]),
                "code": old_code,
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
                SELECT role_id, :old_id FROM identity_role_permissions
                WHERE permission_id=:new_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"old_id": old_id, "new_id": new_id},
        )
        return

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


def downgrade() -> None:
    connection = op.get_bind()
    _restore_permission(
        connection,
        "fair_crm.customers.archive",
        "fair_crm.customers.delete",
        "Archive CRM customers",
    )
    _restore_permission(
        connection,
        "fair_crm.fairs.archive",
        "fair_crm.fairs.delete",
        "Archive CRM fairs",
    )
    _restore_permission(
        connection,
        "fair_crm.todos.archive",
        "fair_crm.todos.delete",
        "Archive CRM todos",
    )
    _restore_permission(
        connection,
        "fair_crm.todos.outcomes.deactivate",
        "fair_crm.todos.outcomes.delete",
        "Deactivate CRM todo outcomes",
    )
