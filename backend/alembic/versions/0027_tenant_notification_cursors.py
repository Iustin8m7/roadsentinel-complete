"""Make notification stream cursors tenant-local and database-enforced.

Revision ID: 0027
Revises: 0026
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("notification_events", "sequence", server_default=None)
    op.execute("DROP SEQUENCE notification_events_sequence")
    op.drop_index("ix_notification_events_tenant_seq", table_name="notification_events")
    op.create_unique_constraint("uq_notification_event_tenant_seq", "notification_events", ["tenant_id", "sequence"])


def downgrade():
    op.drop_constraint("uq_notification_event_tenant_seq", "notification_events", type_="unique")
    op.create_index("ix_notification_events_tenant_seq", "notification_events", ["tenant_id", "sequence"])
    op.execute("CREATE SEQUENCE notification_events_sequence")
    op.alter_column("notification_events", "sequence", server_default=sa.text("nextval('notification_events_sequence')"))
