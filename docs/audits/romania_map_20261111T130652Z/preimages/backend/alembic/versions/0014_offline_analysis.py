"""Tenant-scoped offline recordings and durable analysis runs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-08
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def _rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation ON {table}
        USING (tenant_id = rs_current_tenant())
        WITH CHECK (tenant_id = rs_current_tenant())
    """)


def upgrade() -> None:
    app = _app_role()
    op.create_table(
        "recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("codec", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("fps_num", sa.Integer(), nullable=False),
        sa.Column("fps_den", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "provenance_note",
            sa.String(300),
            nullable=False,
            server_default="User-imported recorded screen capture; capture wall-clock time unverified.",
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="ready"),
        sa.Column("crop", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("crop_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_recordings_tenant_id_tenants",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_recordings_owner_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recordings"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_recordings_tenant_id"),
        sa.UniqueConstraint("tenant_id", "sha256", name="uq_recordings_tenant_sha256"),
        sa.CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 1073741824", name="recordings_size_bound"
        ),
        sa.CheckConstraint(
            "duration_ms > 0 AND duration_ms <= 7200000", name="recordings_duration_bound"
        ),
        sa.CheckConstraint(
            "width BETWEEN 64 AND 7680 AND height BETWEEN 64 AND 4320",
            name="recordings_dimensions_bound",
        ),
        sa.CheckConstraint("fps_num > 0 AND fps_den > 0", name="recordings_frame_rate_positive"),
        sa.CheckConstraint("status IN ('ready', 'deleting')", name="recordings_status"),
    )
    op.create_index("ix_recordings_tenant_created", "recordings", ["tenant_id", "created_at"])
    _rls("recordings")
    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recording_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("config_sha256", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_sha256", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_frames", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("decoded_frames", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("skipped_frames", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_estimated_frames", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("latest_media_pts_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("inference_fps", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("output_storage_key", sa.String(300), nullable=True),
        sa.Column("output_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("output_duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("output_fps", sa.Float(), nullable=True),
        sa.Column("preview_sequence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("worker_instance", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_analysis_runs_tenant_id_tenants",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recordings.tenant_id", "recordings.id"],
            ondelete="CASCADE",
            name="fk_analysis_runs_recording_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], ondelete="RESTRICT", name="fk_analysis_runs_actor_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_runs"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_analysis_runs_tenant_id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')",
            name="analysis_runs_status",
        ),
        sa.CheckConstraint(
            "processed_frames >= 0 AND decoded_frames >= processed_frames",
            name="analysis_runs_frame_counts",
        ),
    )
    op.create_index(
        "ix_analysis_runs_tenant_recording",
        "analysis_runs",
        ["tenant_id", "recording_id", "created_at"],
    )
    _rls("analysis_runs")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON recordings, analysis_runs TO {app}")


def downgrade() -> None:
    op.drop_table("analysis_runs")
    op.drop_table("recordings")
