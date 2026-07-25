"""Rename fair_crm.smtp.* permissions to fair_crm.email_accounts.* (in-place).

Keeps the same permission row IDs so existing identity_role_permissions grants
remain valid. No dual-catalog / dual-read period.

Revision ID: 20260701_0032
Revises: 20260701_0031
Create Date: 2026-07-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0032"
down_revision: Union[str, Sequence[str], None] = "20260701_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"

# old_code -> (new_code, new_description)
PERMISSION_RENAMES: tuple[tuple[str, str, str], ...] = (
    ("fair_crm.smtp.read", "fair_crm.email_accounts.read", "Read CRM email accounts"),
    ("fair_crm.smtp.create", "fair_crm.email_accounts.create", "Create CRM email accounts"),
    ("fair_crm.smtp.update", "fair_crm.email_accounts.update", "Update CRM email accounts"),
    ("fair_crm.smtp.delete", "fair_crm.email_accounts.delete", "Delete CRM email accounts"),
)

GROUP_OLD = "fair_crm.smtp"
GROUP_NEW = "fair_crm.email_accounts"
GROUP_NEW_NAME = "FAIR CRM Email Accounts"
GROUP_NEW_DESCRIPTION = "FAIR CRM email account permissions"

GROUP_OLD_NAME = "FAIR CRM SMTP"
GROUP_OLD_DESCRIPTION = "FAIR CRM SMTP account permissions"


def _rename_permission(connection: sa.Connection, old_code: str, new_code: str, description: str) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {PERMISSIONS_TABLE}
            SET code = :new_code,
                description = :description,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :old_code
            """
        ),
        {"old_code": old_code, "new_code": new_code, "description": description},
    )


def _rename_group(
    connection: sa.Connection,
    *,
    old_code: str,
    new_code: str,
    name: str,
    description: str,
) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {GROUPS_TABLE}
            SET code = :new_code,
                name = :name,
                description = :description,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :old_code
            """
        ),
        {
            "old_code": old_code,
            "new_code": new_code,
            "name": name,
            "description": description,
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    # Rename permissions first so unique(code) never collides with the group rename.
    for old_code, new_code, description in PERMISSION_RENAMES:
        _rename_permission(connection, old_code, new_code, description)
    _rename_group(
        connection,
        old_code=GROUP_OLD,
        new_code=GROUP_NEW,
        name=GROUP_NEW_NAME,
        description=GROUP_NEW_DESCRIPTION,
    )


def downgrade() -> None:
    connection = op.get_bind()
    _rename_group(
        connection,
        old_code=GROUP_NEW,
        new_code=GROUP_OLD,
        name=GROUP_OLD_NAME,
        description=GROUP_OLD_DESCRIPTION,
    )
    reverse = (
        ("fair_crm.email_accounts.read", "fair_crm.smtp.read", "Read CRM SMTP accounts"),
        ("fair_crm.email_accounts.create", "fair_crm.smtp.create", "Create CRM SMTP accounts"),
        ("fair_crm.email_accounts.update", "fair_crm.smtp.update", "Update CRM SMTP accounts"),
        ("fair_crm.email_accounts.delete", "fair_crm.smtp.delete", "Delete CRM SMTP accounts"),
    )
    for old_code, new_code, description in reverse:
        _rename_permission(connection, old_code, new_code, description)
