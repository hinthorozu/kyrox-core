"""Authorization RBAC performance indexes.

Revision ID: 20260701_0013
Revises: 20260701_0012
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260701_0013"
down_revision: Union[str, Sequence[str], None] = "20260701_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_identity_role_permissions_role_id",
        "identity_role_permissions",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_organization_roles_active",
        "identity_organization_roles",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_identity_user_roles_effective",
        "identity_user_roles",
        ["user_id", "organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_user_roles_effective", table_name="identity_user_roles")
    op.drop_index("ix_identity_organization_roles_active", table_name="identity_organization_roles")
    op.drop_index("ix_identity_role_permissions_role_id", table_name="identity_role_permissions")
