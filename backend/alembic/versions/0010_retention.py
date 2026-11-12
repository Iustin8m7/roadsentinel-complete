"""Retention: per-tenant policy per evidence kind, legal hold on alerts, purge marker on evidence.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-05
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def upgrade() -> None:
    app = _app_role()
    op.create_table(
        "retention_policies",
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_retention_policies_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name="fk_retention_policies_updated_by_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_retention_policies"),
        sa.UniqueConstraint("tenant_id", "kind", name="uq_retention_policies_tenant_kind"),
        sa.CheckConstraint("days >= 1 AND days <= 3650", name="ck_retention_policies_days"),
        sa.CheckConstraint(
            "kind IN ('keyframe', 'clip', 'camera_video', 'confirmed_case')",
            name="ck_retention_policies_kind",
        ),
    )
    op.create_index("ix_retention_policies_tenant_id", "retention_policies", ["tenant_id"])
    op.execute("ALTER TABLE retention_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE retention_policies FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON retention_policies
        USING (tenant_id = rs_current_tenant())
        WITH CHECK (tenant_id = rs_current_tenant())
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON retention_policies TO {app}")

    op.add_column(
        "alerts", sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("alerts", sa.Column("legal_hold_reason", sa.String(length=500), nullable=True))
    op.add_column("alerts", sa.Column("legal_hold_by", sa.UUID(), nullable=True))
    op.add_column("alerts", sa.Column("legal_hold_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_alerts_legal_hold_by_users", "alerts", "users", ["legal_hold_by"], ["id"]
    )
    op.add_column("evidence", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_evidence_purge_scan", "evidence", ["tenant_id", "kind", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_evidence_purge_scan", table_name="evidence")
    op.drop_column("evidence", "purged_at")
    op.drop_constraint("fk_alerts_legal_hold_by_users", "alerts", type_="foreignkey")
    for col in ("legal_hold_at", "legal_hold_by", "legal_hold_reason", "legal_hold"):
        op.drop_column("alerts", col)
    op.drop_table("retention_policies")
