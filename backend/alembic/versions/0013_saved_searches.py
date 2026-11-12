"""User-owned saved archive searches with tenant RLS.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-06
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

revision: str = "0013"
down_revision: str | None = "0012"
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
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_saved_searches_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "owner_id"],
            ["users.tenant_id", "users.id"],
            name="fk_saved_searches_tenant_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_saved_searches"),
        sa.UniqueConstraint("tenant_id", "owner_id", "name", name="uq_saved_searches_owner_name"),
        sa.CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 80", name="ck_saved_searches_name_length"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(filters) = 'object'", name="ck_saved_searches_filters_object"
        ),
    )
    op.create_index("ix_saved_searches_tenant_id", "saved_searches", ["tenant_id"])
    op.create_index("ix_saved_searches_owner_id", "saved_searches", ["owner_id"])
    op.execute("ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE saved_searches FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON saved_searches
        USING (tenant_id = rs_current_tenant())
        WITH CHECK (tenant_id = rs_current_tenant())
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON saved_searches TO {app}")


def downgrade() -> None:
    op.drop_table("saved_searches")
