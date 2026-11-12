"""Durable in-app notification event log and recipient state.

Revision ID: 0025
Revises: 0024
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import make_url

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE notification_events_sequence")
    op.create_table(
        "notification_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False, server_default=sa.text("nextval('notification_events_sequence')")),
        sa.Column("alert_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column("dedup_key", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "alert_id"], ["alerts.tenant_id", "alerts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_notification_events_tenant_id"),
        sa.UniqueConstraint("tenant_id", "dedup_key", name="uq_notification_event_dedup"),
    )
    op.create_index("ix_notification_events_tenant_seq", "notification_events", ["tenant_id", "sequence"])
    op.create_table(
        "notification_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("dismissed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "event_id"], ["notification_events.tenant_id", "notification_events.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "user_id", "event_id", name="uq_notification_receipt_user_event"),
    )
    op.create_index("ix_notification_receipts_user", "notification_receipts", ["tenant_id", "user_id", "event_id"])
    role = make_url(os.environ["RS_DATABASE_URL"]).username
    if not role or not role.replace("_", "").isalnum():
        raise ValueError("Invalid application role")
    quoted = op.get_bind().dialect.identifier_preparer.quote(role)
    for table in ("notification_events", "notification_receipts"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (tenant_id=rs_current_tenant()) WITH CHECK (tenant_id=rs_current_tenant())")
    op.execute(f"GRANT SELECT, INSERT ON notification_events TO {quoted}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON notification_receipts TO {quoted}")
    op.execute(f"GRANT USAGE, SELECT ON SEQUENCE notification_events_sequence TO {quoted}")
    op.execute("CREATE FUNCTION rs_notification_event_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION 'Notification events are immutable'; END $$")
    op.execute("CREATE TRIGGER notification_event_immutable BEFORE UPDATE OR DELETE ON notification_events FOR EACH ROW EXECUTE FUNCTION rs_notification_event_immutable()")


def downgrade():
    op.drop_table("notification_receipts")
    op.drop_table("notification_events")
    op.execute("DROP FUNCTION rs_notification_event_immutable()")
    op.execute("DROP SEQUENCE notification_events_sequence")
