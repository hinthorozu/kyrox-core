"""Baseline migration for KYROX Core data foundation.

Revision ID: 20260701_0001
Revises:
Create Date: 2026-07-01

No application tables yet. Identity and platform modules add tables in later migrations.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260701_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
