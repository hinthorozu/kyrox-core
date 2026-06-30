"""Drop redundant index on identity_permissions.code.

Revision ID: 20260701_0005
Revises: 20260701_0004
Create Date: 2026-07-01

The unique constraint uq_identity_permissions_code already indexes code.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260701_0005"
down_revision: Union[str, Sequence[str], None] = "20260701_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_identity_permissions_code", table_name="identity_permissions")


def downgrade() -> None:
    op.create_index(
        "ix_identity_permissions_code",
        "identity_permissions",
        ["code"],
        unique=False,
    )
