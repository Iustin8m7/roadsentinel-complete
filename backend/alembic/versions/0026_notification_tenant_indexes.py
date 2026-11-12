"""Align tenant lookup indexes with the notification models.

Revision ID: 0026
Revises: 0025
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_notification_events_tenant_id", "notification_events", ["tenant_id"])
    op.create_index("ix_notification_receipts_tenant_id", "notification_receipts", ["tenant_id"])


def downgrade():
    op.drop_index("ix_notification_receipts_tenant_id", "notification_receipts")
    op.drop_index("ix_notification_events_tenant_id", "notification_events")
