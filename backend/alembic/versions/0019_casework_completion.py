"""Investigation completion (Workstream B, lane E): explicit case links, structured follow-up
items with an append-only history, manual legal holds; note revisions may carry the recorded
detection box; export jobs count storage outages separately from attempts. The cross-tenant
probe allow-list (``rs_resource_tenant``) is extended to every tenant table that the API looks
up by id, including those of 0007, 0008 and this revision.

Same security pattern as 0002/0003/0008: ``tenant_id`` on every new table with ENABLE + FORCE
RLS and the ``tenant_isolation`` policy, composite (tenant_id, x_id) foreign keys, and
least-privilege grants (the follow-up history is INSERT-only and protected by the append-only
trigger function from 0008).

Does not touch Workstream A's camera runtime tables (lane D, revision 0009).

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-09
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "rsint_case2"
down_revision: str | None = "rsint_run1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("case_links", "case_followups", "case_followup_events", "case_legal_holds")

# Allow-list before this revision (0003; 0007 and 0008 did not redefine the function).
PREVIOUS_PROBE_TABLES = (
    "users",
    "cameras",
    "alerts",
    "evidence",
    "approval_requests",
    "user_sessions",
    "invitations",
    "service_accounts",
)
PROBE_TABLES = (
    *PREVIOUS_PROBE_TABLES,
    # 0007: camera control plane
    "camera_source_grants",
    "camera_config_versions",
    "camera_worker_status",
    "camera_health_events",
    # 0008: investigation workspace
    "case_notes",
    "case_note_revisions",
    "case_bookmarks",
    "export_jobs",
    "saved_searches",
    # 0010
    *NEW_TABLES,
)

# (child table, child column, parent table, constraint name)
TENANT_FKS = (
    ("case_links", "alert_a_id", "alerts", "fk_case_links_tenant_alert_a"),
    ("case_links", "alert_b_id", "alerts", "fk_case_links_tenant_alert_b"),
    ("case_links", "created_by", "users", "fk_case_links_tenant_creator"),
    ("case_links", "removed_by", "users", "fk_case_links_tenant_remover"),
    ("case_followups", "alert_id", "alerts", "fk_case_followups_tenant_alert"),
    ("case_followups", "author_id", "users", "fk_case_followups_tenant_author"),
    ("case_followups", "assignee_id", "users", "fk_case_followups_tenant_assignee"),
    ("case_followup_events", "followup_id", "case_followups", "fk_case_followup_events_tenant_fu"),
    ("case_followup_events", "actor_id", "users", "fk_case_followup_events_tenant_actor"),
    ("case_followup_events", "assignee_id", "users", "fk_case_followup_events_tenant_assignee"),
    ("case_legal_holds", "alert_id", "alerts", "fk_case_legal_holds_tenant_alert"),
    ("case_legal_holds", "placed_by", "users", "fk_case_legal_holds_tenant_placer"),
    ("case_legal_holds", "released_by", "users", "fk_case_legal_holds_tenant_releaser"),
)

GRANTS = {
    "case_links": "SELECT, INSERT, UPDATE",
    "case_followups": "SELECT, INSERT, UPDATE",
    "case_followup_events": "SELECT, INSERT",
    "case_legal_holds": "SELECT, INSERT, UPDATE",
}


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def _resource_tenant_fn(tables: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{t}'" for t in tables)
    return f"""
        CREATE OR REPLACE FUNCTION rs_resource_tenant(p_table text, p_id uuid) RETURNS uuid
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
        DECLARE result uuid;
        BEGIN
            IF p_table NOT IN ({allowed}) THEN
                RAISE EXCEPTION 'table not allowed';
            END IF;
            EXECUTE format('SELECT tenant_id FROM %I WHERE id = $1', p_table)
                INTO result USING p_id;
            RETURN result;
        END $$
    """  # noqa: S608 - fixed allow-list, no user input


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants", ondelete="RESTRICT"
    )


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '15s'")  # fail the deploy rather than queue traffic
    app = _app_role()
    tz = sa.DateTime(timezone=True)

    op.create_table(
        "case_links",
        *_base_columns(),
        sa.Column("alert_a_id", sa.UUID(), nullable=False),
        sa.Column("alert_b_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("removed_at", tz, nullable=True),
        sa.Column("removed_by", sa.UUID(), nullable=True),
        sa.CheckConstraint("alert_a_id < alert_b_id", name="ck_case_links_ordered_pair"),
        sa.ForeignKeyConstraint(
            ["alert_a_id"],
            ["alerts.id"],
            name="fk_case_links_alert_a_id_alerts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["alert_b_id"],
            ["alerts.id"],
            name="fk_case_links_alert_b_id_alerts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_case_links_created_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["removed_by"], ["users.id"], name="fk_case_links_removed_by_users"
        ),
        _tenant_fk("case_links"),
        sa.PrimaryKeyConstraint("id", name="pk_case_links"),
    )
    op.create_index("ix_case_links_alert_a_id", "case_links", ["alert_a_id"])
    op.create_index("ix_case_links_alert_b_id", "case_links", ["alert_b_id"])
    op.create_index("ix_case_links_tenant_id", "case_links", ["tenant_id"])
    op.create_index(
        "ix_case_links_active_pair",
        "case_links",
        ["alert_a_id", "alert_b_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )

    op.create_table(
        "case_followups",
        *_base_columns(),
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", tz, nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'done', 'cancelled')", name="ck_case_followups_status"
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name="fk_case_followups_alert_id_alerts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_case_followups_author_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name="fk_case_followups_assignee_id_users"
        ),
        _tenant_fk("case_followups"),
        sa.PrimaryKeyConstraint("id", name="pk_case_followups"),
    )
    op.create_index("ix_case_followups_alert_id", "case_followups", ["alert_id"])
    op.create_index("ix_case_followups_tenant_id", "case_followups", ["tenant_id"])

    op.create_table(
        "case_followup_events",
        *_base_columns(),
        sa.Column("followup_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("change", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["followup_id"],
            ["case_followups.id"],
            name="fk_case_followup_events_followup_id_case_followups",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_case_followup_events_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name="fk_case_followup_events_assignee_id_users"
        ),
        _tenant_fk("case_followup_events"),
        sa.PrimaryKeyConstraint("id", name="pk_case_followup_events"),
        sa.UniqueConstraint("followup_id", "revision", name="uq_case_followup_events_rev"),
    )
    op.create_index("ix_case_followup_events_followup_id", "case_followup_events", ["followup_id"])
    op.create_index("ix_case_followup_events_tenant_id", "case_followup_events", ["tenant_id"])

    op.create_table(
        "case_legal_holds",
        *_base_columns(),
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("placed_by", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("released_at", tz, nullable=True),
        sa.Column("released_by", sa.UUID(), nullable=True),
        sa.Column("release_reason", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name="fk_case_legal_holds_alert_id_alerts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["placed_by"], ["users.id"], name="fk_case_legal_holds_placed_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["released_by"], ["users.id"], name="fk_case_legal_holds_released_by_users"
        ),
        _tenant_fk("case_legal_holds"),
        sa.PrimaryKeyConstraint("id", name="pk_case_legal_holds"),
    )
    op.create_index("ix_case_legal_holds_alert_id", "case_legal_holds", ["alert_id"])
    op.create_index("ix_case_legal_holds_tenant_id", "case_legal_holds", ["tenant_id"])
    op.create_index(
        "ix_case_legal_holds_active",
        "case_legal_holds",
        ["alert_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )

    op.add_column(
        "case_note_revisions",
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "export_jobs",
        sa.Column("storage_retries", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_unique_constraint(
        "uq_case_followups_tenant_id_id", "case_followups", ["tenant_id", "id"]
    )
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

    # Follow-up history is append-only for every role (same function as note revisions).
    op.execute("""
        CREATE TRIGGER case_followup_events_append_only
        BEFORE UPDATE OR DELETE ON case_followup_events
        FOR EACH ROW EXECUTE FUNCTION rs_append_only()
    """)

    op.execute(_resource_tenant_fn(PROBE_TABLES))


def downgrade() -> None:
    op.execute(_resource_tenant_fn(PREVIOUS_PROBE_TABLES))
    op.execute("DROP TRIGGER IF EXISTS case_followup_events_append_only ON case_followup_events")
    for child, _, _, name in TENANT_FKS:
        op.drop_constraint(name, child, type_="foreignkey")
    op.drop_constraint("uq_case_followups_tenant_id_id", "case_followups", type_="unique")
    op.drop_column("export_jobs", "storage_retries")
    op.drop_column("case_note_revisions", "bbox")
    op.drop_table("case_legal_holds")
    op.drop_table("case_followup_events")
    op.drop_table("case_followups")
    op.drop_table("case_links")
