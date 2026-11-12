"""Fields of the API.md contract: camera slugs and timezones, public alert numbers, detection
details, VLM verdicts, operator actions, and camera-level evidence (annotated recordings).

* ``cameras.slug`` is the contract's camera id (unique per tenant); existing rows get
  ``cam-<first 8 hex of the uuid>``.
* ``alerts.number`` is the contract's event id: per-tenant, monotonic, assigned by a BEFORE
  INSERT trigger under a per-tenant advisory lock (so every insert path gets one). Existing
  rows are numbered by creation time.
* ``evidence.alert_id`` becomes nullable so an annotated camera recording can be stored as
  evidence of the camera (``camera_id``); exactly one owner is required.
* ``alerts.superseded_at`` hides undecided alerts after a demo camera reset. Nothing is deleted.

NOTE: written by hand (autogenerate would drop the composite tenant FKs from 0002).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VLM_STATUSES = ("pending", "confirmed", "rejected", "uncertain", "skipped")
OBJECT_CLASSES = ("car", "truck", "bus", "motorcycle", "bicycle", "person")
ACTIONS = ("dispatch_patrol", "warning_sign", "enforcement", "monitor")


def _in(column: str, values: tuple[str, ...], nullable: bool = True) -> str:
    listed = ", ".join(f"'{v}'" for v in values)
    clause = f"{column} IN ({listed})"
    return f"{column} IS NULL OR {clause}" if nullable else clause


def upgrade() -> None:
    # --- cameras
    op.add_column("cameras", sa.Column("slug", sa.String(length=64), nullable=True))
    op.add_column(
        "cameras",
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default="Europe/Bucharest"
        ),
    )
    op.execute("UPDATE cameras SET slug = 'cam-' || left(replace(id::text, '-', ''), 8)")
    op.alter_column("cameras", "slug", nullable=False)
    op.create_unique_constraint("uq_cameras_tenant_slug", "cameras", ["tenant_id", "slug"])
    op.create_check_constraint("slug", "cameras", "slug ~ '^[A-Za-z0-9_-]{1,64}$'")

    # --- alerts
    op.add_column("alerts", sa.Column("number", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE alerts a SET number = n.rn FROM (
            SELECT id, row_number() OVER (PARTITION BY tenant_id ORDER BY created_at, id) AS rn
            FROM alerts
        ) n WHERE a.id = n.id
    """)
    op.alter_column("alerts", "number", nullable=False)
    op.execute("""
        CREATE FUNCTION rs_alert_number() RETURNS trigger
        LANGUAGE plpgsql SET search_path = public, pg_temp
        AS $$
        BEGIN
            IF NEW.number IS NULL THEN
                PERFORM pg_advisory_xact_lock(hashtextextended(NEW.tenant_id::text, 11));
                SELECT coalesce(max(number), 0) + 1 INTO NEW.number
                FROM alerts WHERE tenant_id = NEW.tenant_id;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER alerts_number BEFORE INSERT ON alerts
        FOR EACH ROW EXECUTE FUNCTION rs_alert_number()
    """)
    op.create_unique_constraint("uq_alerts_tenant_number", "alerts", ["tenant_id", "number"])
    for name, column in (
        ("video_t", sa.Float()),
        ("track_id", sa.Integer()),
        ("object_class", sa.String(length=20)),
        ("speed_kmh", sa.Float()),
        ("rule", sa.String(length=300)),
        ("vlm_text", sa.String(length=300)),
        ("action", sa.String(length=40)),
        ("decision_note", sa.String(length=500)),
        ("superseded_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("alerts", sa.Column(name, column, nullable=True))
    op.add_column(
        "alerts",
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "alerts",
        sa.Column("vlm_status", sa.String(length=12), nullable=False, server_default="skipped"),
    )
    op.create_check_constraint("vlm_status", "alerts", _in("vlm_status", VLM_STATUSES, False))
    op.create_check_constraint("object_class", "alerts", _in("object_class", OBJECT_CLASSES))
    op.create_check_constraint("action", "alerts", _in("action", ACTIONS))
    op.create_check_constraint(
        "video_t", "alerts", "video_t IS NULL OR video_t BETWEEN 0 AND 86400"
    )
    op.create_check_constraint(
        "speed_kmh", "alerts", "speed_kmh IS NULL OR speed_kmh BETWEEN 0 AND 400"
    )
    op.create_check_constraint("details_size", "alerts", "pg_column_size(details) <= 8192")
    op.create_index("ix_alerts_queue", "alerts", ["tenant_id", "status", "priority", "detected_at"])

    # --- evidence: camera recordings, redaction level
    op.alter_column("evidence", "alert_id", nullable=True)
    op.add_column("evidence", sa.Column("camera_id", sa.UUID(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("redaction", sa.String(length=20), nullable=False, server_default="full"),
    )
    op.create_foreign_key(
        "fk_evidence_camera_id_cameras",
        "evidence",
        "cameras",
        ["camera_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_evidence_tenant_camera",
        "evidence",
        "cameras",
        ["tenant_id", "camera_id"],
        ["tenant_id", "id"],
    )
    op.create_index("ix_evidence_camera_id", "evidence", ["camera_id"])
    op.create_check_constraint("owner", "evidence", "(alert_id IS NULL) <> (camera_id IS NULL)")
    op.create_check_constraint("redaction", "evidence", "redaction IN ('full', 'heads_only')")


def downgrade() -> None:
    op.drop_constraint("ck_evidence_redaction", "evidence", type_="check")
    op.drop_constraint("ck_evidence_owner", "evidence", type_="check")
    op.drop_index("ix_evidence_camera_id", table_name="evidence")
    op.drop_constraint("fk_evidence_tenant_camera", "evidence", type_="foreignkey")
    op.drop_constraint("fk_evidence_camera_id_cameras", "evidence", type_="foreignkey")
    op.drop_column("evidence", "redaction")
    op.drop_column("evidence", "camera_id")
    op.execute("DELETE FROM evidence WHERE alert_id IS NULL")
    op.alter_column("evidence", "alert_id", nullable=False)

    op.drop_index("ix_alerts_queue", table_name="alerts")
    for name in ("details_size", "speed_kmh", "video_t", "action", "object_class", "vlm_status"):
        op.drop_constraint(f"ck_alerts_{name}", "alerts", type_="check")
    op.drop_constraint("uq_alerts_tenant_number", "alerts", type_="unique")
    op.execute("DROP TRIGGER IF EXISTS alerts_number ON alerts")
    op.execute("DROP FUNCTION IF EXISTS rs_alert_number()")
    for name in (
        "vlm_status",
        "details",
        "superseded_at",
        "decision_note",
        "action",
        "vlm_text",
        "rule",
        "speed_kmh",
        "object_class",
        "track_id",
        "video_t",
        "number",
    ):
        op.drop_column("alerts", name)

    op.drop_constraint("ck_cameras_slug", "cameras", type_="check")
    op.drop_constraint("uq_cameras_tenant_slug", "cameras", type_="unique")
    op.drop_column("cameras", "timezone")
    op.drop_column("cameras", "slug")
