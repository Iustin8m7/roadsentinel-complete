"""Investigation workspace (Workstream B): case notes with append-only revisions, timeline
bookmarks, evidence-package export jobs, user-owned saved archive filters; evidence gets
``duration_s`` (from the MP4 header) and ``purged_at``/``purge_reason`` (explicit purge state).

Same security pattern as 0002/0003: every new table has ``tenant_id`` with ENABLE + FORCE RLS
and the ``tenant_isolation`` policy, composite (tenant_id, x_id) foreign keys so a row can never
point into another tenant, and least-privilege grants for the runtime role (note revisions are
INSERT-only and additionally protected by an append-only trigger).

Does not touch Workstream A's tables (0007).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-09
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "rsint_case1"
down_revision: str | None = "rsint_cam1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = (
    "case_notes",
    "case_note_revisions",
    "case_bookmarks",
    "export_jobs",
)

# Parents that need a (tenant_id, id) unique key for composite FKs (alerts/users have one).
NEW_PARENT_KEYS = ("evidence", "approval_requests", "case_notes")

# (child table, child column, parent table, constraint name)
TENANT_FKS = (
    ("case_notes", "alert_id", "alerts", "fk_case_notes_tenant_alert"),
    ("case_notes", "author_id", "users", "fk_case_notes_tenant_author"),
    ("case_note_revisions", "note_id", "case_notes", "fk_case_note_revisions_tenant_note"),
    ("case_note_revisions", "evidence_id", "evidence", "fk_case_note_revisions_tenant_evidence"),
    ("case_bookmarks", "alert_id", "alerts", "fk_case_bookmarks_tenant_alert"),
    ("case_bookmarks", "evidence_id", "evidence", "fk_case_bookmarks_tenant_evidence"),
    ("export_jobs", "alert_id", "alerts", "fk_export_jobs_tenant_alert"),
    ("export_jobs", "requester_id", "users", "fk_export_jobs_tenant_requester"),
    ("export_jobs", "approval_id", "approval_requests", "fk_export_jobs_tenant_approval"),
)

GRANTS = {
    "case_notes": "SELECT, INSERT, UPDATE",
    "case_note_revisions": "SELECT, INSERT",
    "case_bookmarks": "SELECT, INSERT, UPDATE",
    "export_jobs": "SELECT, INSERT, UPDATE",
}


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '15s'")  # fail the deploy rather than queue traffic
    app = _app_role()
    op.create_table(
        "case_notes",
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("retracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retracted_by", sa.UUID(), nullable=True),
        sa.Column("retract_reason", sa.String(length=500), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_case_notes_alert_id_alerts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_case_notes_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["retracted_by"], ["users.id"], name=op.f("fk_case_notes_retracted_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_case_notes_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_notes")),
    )
    op.create_index(op.f("ix_case_notes_alert_id"), "case_notes", ["alert_id"], unique=False)
    op.create_index(op.f("ix_case_notes_tenant_id"), "case_notes", ["tenant_id"], unique=False)
    op.create_table(
        "export_jobs",
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("requester_id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("include_original", sa.Boolean(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=64), nullable=True),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("package_sha256", sa.String(length=64), nullable=True),
        sa.Column("package_key", sa.String(length=400), nullable=True),
        sa.Column("package_size", sa.BigInteger(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_export_jobs_alert_id_alerts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["approval_requests.id"],
            name=op.f("fk_export_jobs_approval_id_approval_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"], ["users.id"], name=op.f("fk_export_jobs_requester_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_export_jobs_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_jobs")),
        sa.UniqueConstraint(
            "tenant_id", "requester_id", "idempotency_key", name="uq_export_jobs_idempotency"
        ),
    )
    op.create_index(op.f("ix_export_jobs_alert_id"), "export_jobs", ["alert_id"], unique=False)
    op.create_index(
        "ix_export_jobs_claim", "export_jobs", ["state", "lease_expires_at"], unique=False
    )
    op.create_index(op.f("ix_export_jobs_tenant_id"), "export_jobs", ["tenant_id"], unique=False)
    op.create_table(
        "case_bookmarks",
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("evidence_id", sa.UUID(), nullable=False),
        sa.Column("offset_s", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_case_bookmarks_alert_id_alerts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_case_bookmarks_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name=op.f("fk_case_bookmarks_evidence_id_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["removed_by"], ["users.id"], name=op.f("fk_case_bookmarks_removed_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_case_bookmarks_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_bookmarks")),
    )
    op.create_index(
        op.f("ix_case_bookmarks_alert_id"), "case_bookmarks", ["alert_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_bookmarks_tenant_id"), "case_bookmarks", ["tenant_id"], unique=False
    )
    op.create_table(
        "case_note_revisions",
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_id", sa.UUID(), nullable=True),
        sa.Column("offset_s", sa.Float(), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_case_note_revisions_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name=op.f("fk_case_note_revisions_evidence_id_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["case_notes.id"],
            name=op.f("fk_case_note_revisions_note_id_case_notes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_case_note_revisions_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_note_revisions")),
        sa.UniqueConstraint("note_id", "revision", name="uq_case_note_revisions_rev"),
    )
    op.create_index(
        op.f("ix_case_note_revisions_note_id"), "case_note_revisions", ["note_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_note_revisions_tenant_id"), "case_note_revisions", ["tenant_id"], unique=False
    )
    op.add_column("evidence", sa.Column("duration_s", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("purge_reason", sa.String(length=200), nullable=True))

    for parent in NEW_PARENT_KEYS:
        op.create_unique_constraint(f"uq_{parent}_tenant_id_id", parent, ["tenant_id", "id"])
    for child, col, parent, name in TENANT_FKS:
        op.create_foreign_key(name, child, parent, ["tenant_id", col], ["tenant_id", "id"])

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = rs_current_tenant())
            WITH CHECK (tenant_id = rs_current_tenant())
        """)
        op.execute(f"GRANT {GRANTS[table]} ON {table} TO {app}")

    # Note revisions are history: no UPDATE/DELETE for any role (the app role has no grant
    # either). Retraction is recorded on case_notes, never by rewriting a revision.
    op.execute("""
        CREATE FUNCTION rs_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only (% blocked)', TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER case_note_revisions_append_only
        BEFORE UPDATE OR DELETE ON case_note_revisions
        FOR EACH ROW EXECUTE FUNCTION rs_append_only()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS case_note_revisions_append_only ON case_note_revisions")
    op.execute("DROP FUNCTION IF EXISTS rs_append_only()")
    for child, _, _, name in TENANT_FKS:
        op.drop_constraint(name, child, type_="foreignkey")
    for parent in NEW_PARENT_KEYS:
        op.drop_constraint(f"uq_{parent}_tenant_id_id", parent, type_="unique")
    op.drop_column("evidence", "purge_reason")
    op.drop_column("evidence", "duration_s")
    op.drop_index(op.f("ix_case_note_revisions_tenant_id"), table_name="case_note_revisions")
    op.drop_index(op.f("ix_case_note_revisions_note_id"), table_name="case_note_revisions")
    op.drop_table("case_note_revisions")
    op.drop_index(op.f("ix_case_bookmarks_tenant_id"), table_name="case_bookmarks")
    op.drop_index(op.f("ix_case_bookmarks_alert_id"), table_name="case_bookmarks")
    op.drop_table("case_bookmarks")
    op.drop_index(op.f("ix_export_jobs_tenant_id"), table_name="export_jobs")
    op.drop_index("ix_export_jobs_claim", table_name="export_jobs")
    op.drop_index(op.f("ix_export_jobs_alert_id"), table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index(op.f("ix_case_notes_tenant_id"), table_name="case_notes")
    op.drop_index(op.f("ix_case_notes_alert_id"), table_name="case_notes")
    op.drop_table("case_notes")
