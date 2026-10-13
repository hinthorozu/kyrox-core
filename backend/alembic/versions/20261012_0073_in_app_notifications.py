"""Extend existing platform notifications with durable in-app delivery."""
from alembic import op

revision = "20261012_0073"
down_revision = "20261008_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("platform_notifications") as batch:
        batch.drop_constraint("ck_platform_notifications_channel", type_="check")
        batch.create_check_constraint("ck_platform_notifications_channel", "channel IN ('email', 'in_app')")


def downgrade() -> None:
    # Never silently discard delivered inbox records on schema downgrade.
    with op.batch_alter_table("platform_notifications") as batch:
        batch.drop_constraint("ck_platform_notifications_channel", type_="check")
        batch.create_check_constraint("ck_platform_notifications_channel", "channel IN ('email')")
