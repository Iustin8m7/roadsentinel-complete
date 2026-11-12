"""Per-user opt-in for audible in-app incident cues.

Revision ID: 0028
Revises: 0027
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import make_url

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sound_on_critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_notification_preference_user"),
    )
    op.create_index("ix_notification_preferences_tenant_id", "notification_preferences", ["tenant_id"])
    role = make_url(os.environ["RS_DATABASE_URL"]).username
    if not role or not role.replace("_", "").isalnum():
        raise ValueError("Invalid application role")
    quoted = op.get_bind().dialect.identifier_preparer.quote(role)
    op.execute("ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notification_preferences FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON notification_preferences USING (tenant_id=rs_current_tenant()) WITH CHECK (tenant_id=rs_current_tenant())")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON notification_preferences TO {quoted}")


def downgrade():
    op.drop_table("notification_preferences")
