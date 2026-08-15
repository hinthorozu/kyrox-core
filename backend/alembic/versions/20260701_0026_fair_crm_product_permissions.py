"""Seed remaining fair_crm.* product permissions for FAIR CRM integration.

Revision ID: 20260701_0026
Revises: 20260701_0025
Create Date: 2026-07-05
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0026"
down_revision: Union[str, Sequence[str], None] = "20260701_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
FAIR_CRM_MODULE = "fair_crm"

PERMISSION_GROUPS: tuple[dict, ...] = (
    {
        "code": "fair_crm.fairs",
        "name": "FAIR CRM Fairs",
        "description": "FAIR CRM fair module permissions",
        "sort_order": 20,
        "permissions": (
            ("fair_crm.fairs.read", "Read CRM fairs"),
            ("fair_crm.fairs.create", "Create CRM fairs"),
            ("fair_crm.fairs.update", "Update CRM fairs"),
            ("fair_crm.fairs.archive", "Archive and restore CRM fairs"),
        ),
    },
    {
        "code": "fair_crm.imports",
        "name": "FAIR CRM Imports",
        "description": "FAIR CRM import pipeline permissions",
        "sort_order": 30,
        "permissions": (
            ("fair_crm.imports.read", "Read CRM import batches"),
            ("fair_crm.imports.create", "Create CRM import batches"),
            ("fair_crm.imports.update", "Update CRM import batches"),
            ("fair_crm.imports.delete", "Delete CRM import batches"),
            ("fair_crm.imports.apply", "Apply CRM import batches"),
        ),
    },
    {
        "code": "fair_crm.contacts",
        "name": "FAIR CRM Contacts",
        "description": "FAIR CRM contact module permissions",
        "sort_order": 40,
        "permissions": (
            ("fair_crm.contacts.read", "Read CRM contacts"),
            ("fair_crm.contacts.create", "Create CRM contacts"),
            ("fair_crm.contacts.update", "Update CRM contacts"),
            ("fair_crm.contacts.delete", "Delete CRM contacts"),
        ),
    },
    {
        "code": "fair_crm.participations",
        "name": "FAIR CRM Participations",
        "description": "FAIR CRM fair participation permissions",
        "sort_order": 50,
        "permissions": (
            ("fair_crm.participations.read", "Read CRM participations"),
            ("fair_crm.participations.create", "Create CRM participations"),
            ("fair_crm.participations.update", "Update CRM participations"),
            ("fair_crm.participations.delete", "Delete CRM participations"),
        ),
    },
    {
        "code": "fair_crm.activities",
        "name": "FAIR CRM Activities",
        "description": "FAIR CRM activity timeline permissions",
        "sort_order": 60,
        "permissions": (
            ("fair_crm.activities.read", "Read CRM activities"),
            ("fair_crm.activities.create", "Create CRM activities"),
            ("fair_crm.activities.update", "Update CRM activities"),
            ("fair_crm.activities.delete", "Delete CRM activities"),
        ),
    },
    {
        "code": "fair_crm.scraper",
        "name": "FAIR CRM Scraper",
        "description": "FAIR CRM adapter and scraper permissions",
        "sort_order": 70,
        "permissions": (
            ("fair_crm.scraper.read", "Read CRM scraper adapters and runs"),
            ("fair_crm.scraper.create", "Create CRM scraper adapters"),
            ("fair_crm.scraper.update", "Update CRM scraper adapters"),
            ("fair_crm.scraper.delete", "Delete CRM scraper adapters"),
            ("fair_crm.scraper.run", "Run CRM scraper adapters"),
            ("fair_crm.scraper.download", "Download CRM scraper run outputs"),
        ),
    },
    {
        "code": "fair_crm.smtp",
        "name": "FAIR CRM SMTP",
        "description": "FAIR CRM SMTP account permissions",
        "sort_order": 80,
        "permissions": (
            ("fair_crm.smtp.read", "Read CRM SMTP accounts"),
            ("fair_crm.smtp.create", "Create CRM SMTP accounts"),
            ("fair_crm.smtp.update", "Update CRM SMTP accounts"),
            ("fair_crm.smtp.delete", "Delete CRM SMTP accounts"),
        ),
    },
    {
        "code": "fair_crm.admin.backups",
        "name": "FAIR CRM Admin Backups",
        "description": "FAIR CRM database backup permissions",
        "sort_order": 90,
        "permissions": (
            ("fair_crm.admin.backups.read", "Read CRM database backups"),
            ("fair_crm.admin.backups.create", "Create CRM database backups"),
            ("fair_crm.admin.backups.download", "Download CRM database backups"),
        ),
    },
    {
        "code": "fair_crm.admin.data_operations",
        "name": "FAIR CRM Admin Data Operations",
        "description": "FAIR CRM admin data operation permissions",
        "sort_order": 91,
        "permissions": (
            ("fair_crm.admin.data_operations.read", "Read CRM admin data operations"),
            ("fair_crm.admin.data_operations.run", "Run CRM admin data operations"),
        ),
    },
)

ALL_NEW_PERMISSION_CODES: tuple[str, ...] = tuple(
    code for group in PERMISSION_GROUPS for code, _ in group["permissions"]
)


def _ensure_permission_group(
    connection: sa.Connection,
    *,
    code: str,
    name: str,
    description: str,
    sort_order: int,
) -> uuid.UUID:
    group_id = connection.execute(
        sa.text(
            f"""
            SELECT id FROM {GROUPS_TABLE}
            WHERE code = :code
            LIMIT 1
            """
        ),
        {"code": code},
    ).scalar()

    if group_id is not None:
        return uuid.UUID(str(group_id))

    group_id = uuid.uuid4()
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {GROUPS_TABLE} (
                id, code, name, module, description, sort_order, is_system, created_at, updated_at
            ) VALUES (
                :id, :code, :name, :module, :description, :sort_order, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "id": str(group_id),
            "code": code,
            "name": name,
            "module": FAIR_CRM_MODULE,
            "description": description,
            "sort_order": sort_order,
            "is_system": True,
        },
    )
    return group_id


def _ensure_permission(
    connection: sa.Connection,
    *,
    group_id: uuid.UUID,
    code: str,
    description: str,
) -> None:
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {PERMISSIONS_TABLE} (
                id, group_id, code, description, is_system, created_at, updated_at
            )
            SELECT :id, :group_id, :code, :description, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM {PERMISSIONS_TABLE} WHERE code = :code
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "group_id": str(group_id),
            "code": code,
            "description": description,
            "is_system": True,
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    for group in PERMISSION_GROUPS:
        group_id = _ensure_permission_group(
            connection,
            code=group["code"],
            name=group["name"],
            description=group["description"],
            sort_order=group["sort_order"],
        )
        for code, description in group["permissions"]:
            _ensure_permission(
                connection,
                group_id=group_id,
                code=code,
                description=description,
            )


def downgrade() -> None:
    connection = op.get_bind()
    for code in ALL_NEW_PERMISSION_CODES:
        connection.execute(
            sa.text(f"DELETE FROM {PERMISSIONS_TABLE} WHERE code = :code"),
            {"code": code},
        )
