"""Camera control plane: lifecycle/source columns on cameras, processing grants, immutable
config versions, worker status (lease) and a bounded health-event history.

* Additive only. Existing cameras get ``lifecycle_state = 'legacy'``: their ingest behaves
  exactly as before until an admin adopts them into the control plane.
* New tables are tenant-scoped with forced RLS and the same ``tenant_isolation`` policy as
  0002/0003; composite (tenant_id, x) FKs stop cross-tenant references.
* ``camera_config_versions``: a trigger makes config/fingerprint/revision/attribution
  immutable, allows only forward status transitions, and blocks DELETE for every role. A CHECK
  enforces four-eyes in the database: the deciding admin is never the creator or submitter.
* The runtime role gets no DELETE on grants/versions/status (history is kept); it may DELETE
  health events only (the per-camera retention cap).

NOTE: written by hand (autogenerate would drop the composite tenant FKs).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-09
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

from alembic import op

revision: str = "rsint_cam1"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = (
    "camera_source_grants",
    "camera_config_versions",
    "camera_worker_status",
    "camera_health_events",
)
LIFECYCLE = ("legacy", "discovered", "onboarding", "approved", "disabled")
SOURCE_KINDS = ("recorded_replay", "owned_optical_live", "authorized_network_live")
VERSION_STATUSES = (
    "draft",
    "validated",
    "awaiting_approval",
    "approved",
    "active",
    "superseded",
    "rejected",
)


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = (make_url(url).username if url else None) or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
    ]


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id"], ["tenants.id"], name=f"fk_{table}_tenant_id_tenants", ondelete="RESTRICT"
    )


def _camera_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "camera_id"],
        ["cameras.tenant_id", "cameras.id"],
        name=f"fk_{table}_tenant_camera",
        ondelete="RESTRICT",
    )


def _user_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["users.id"], name=f"fk_{table}_{column}_users")


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '15s'")  # fail the deploy rather than queue traffic
    app = _app_role()
    tz = sa.DateTime(timezone=True)

    # --- cameras (additive)
    op.add_column(
        "cameras",
        sa.Column("lifecycle_state", sa.String(16), nullable=False, server_default="legacy"),
    )
    op.add_column("cameras", sa.Column("source_kind", sa.String(32), nullable=True))
    op.add_column("cameras", sa.Column("source_display", sa.String(300), nullable=True))
    op.add_column("cameras", sa.Column("source_url_enc", sa.LargeBinary(), nullable=True))
    op.add_column(
        "cameras",
        sa.Column("source_has_credentials", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "cameras",
        sa.Column("desired_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "cameras", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("cameras", sa.Column("active_config_id", sa.UUID(), nullable=True))
    op.add_column("cameras", sa.Column("disabled_reason", sa.String(300), nullable=True))
    op.add_column("cameras", sa.Column("enable_requested_by", sa.UUID(), nullable=True))
    op.add_column("cameras", sa.Column("enable_requested_at", tz, nullable=True))
    op.create_foreign_key(
        "fk_cameras_enable_requested_by_users", "cameras", "users", ["enable_requested_by"], ["id"]
    )
    op.create_check_constraint("lifecycle_state", "cameras", _in("lifecycle_state", LIFECYCLE))
    op.create_check_constraint(
        "source_kind", "cameras", f"source_kind IS NULL OR {_in('source_kind', SOURCE_KINDS)}"
    )
    op.create_check_constraint("revision", "cameras", "revision >= 0")
    # A legacy/discovered camera can never be switched on by the control plane.
    op.create_check_constraint(
        "desired_enabled_state",
        "cameras",
        "NOT desired_enabled OR lifecycle_state = 'approved'",
    )

    # --- processing authorizations
    op.create_table(
        "camera_source_grants",
        *_base_columns(),
        sa.Column("created_at", tz, nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("granting_party", sa.String(200), nullable=False),
        sa.Column("basis", sa.String(32), nullable=False),
        sa.Column("basis_reference", sa.String(200), nullable=False),
        sa.Column("purpose", sa.String(500), nullable=False),
        sa.Column("valid_from", tz, nullable=False),
        sa.Column("valid_until", tz, nullable=False),
        sa.Column("capture_method", sa.String(32), nullable=False),
        sa.Column("max_analysis_fps", sa.Float(), nullable=False),
        sa.Column("max_frame_height", sa.Integer(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("export_allowed", sa.Boolean(), nullable=False),
        sa.Column("media_scope", sa.String(32), nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revoked_at", tz, nullable=True),
        sa.Column("revoked_by", sa.UUID(), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_camera_source_grants"),
        _tenant_fk("camera_source_grants"),
        _camera_fk("camera_source_grants"),
        _user_fk("camera_source_grants", "reviewed_by"),
        _user_fk("camera_source_grants", "revoked_by"),
        sa.CheckConstraint("valid_until > valid_from", name="validity"),
        sa.CheckConstraint(
            _in(
                "basis", ("written_agreement", "licence", "own_infrastructure", "statutory_mandate")
            ),
            name="basis",
        ),
        sa.CheckConstraint(_in("capture_method", SOURCE_KINDS), name="capture_method"),
        sa.CheckConstraint(
            _in("media_scope", ("events_only", "events_and_recordings")), name="media_scope"
        ),
        sa.CheckConstraint(_in("status", ("active", "revoked")), name="status"),
        sa.CheckConstraint(
            "max_analysis_fps > 0 AND max_frame_height > 0 AND retention_days > 0", name="limits"
        ),
    )
    op.create_index("ix_camera_source_grants_tenant_id", "camera_source_grants", ["tenant_id"])
    op.create_index("ix_camera_source_grants_camera_id", "camera_source_grants", ["camera_id"])

    # --- immutable config versions
    op.create_table(
        "camera_config_versions",
        *_base_columns(),
        sa.Column("created_at", tz, nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("validated_at", tz, nullable=True),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", tz, nullable=True),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", tz, nullable=True),
        sa.Column("decision_note", sa.String(500), nullable=True),
        sa.Column("activated_by", sa.UUID(), nullable=True),
        sa.Column("activated_at", tz, nullable=True),
        sa.Column("activation_reason", sa.String(500), nullable=True),
        sa.Column("superseded_at", tz, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_camera_config_versions"),
        sa.UniqueConstraint("camera_id", "revision", name="uq_camera_config_versions_camera_rev"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_camera_config_versions_tenant_id_id"),
        _tenant_fk("camera_config_versions"),
        _camera_fk("camera_config_versions"),
        _user_fk("camera_config_versions", "created_by"),
        _user_fk("camera_config_versions", "submitted_by"),
        _user_fk("camera_config_versions", "decided_by"),
        _user_fk("camera_config_versions", "activated_by"),
        sa.CheckConstraint(_in("status", VERSION_STATUSES), name="status"),
        sa.CheckConstraint("revision > 0", name="revision"),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="fingerprint"),
        sa.CheckConstraint(
            "decided_by IS NULL OR (decided_by <> created_by AND "
            "(submitted_by IS NULL OR decided_by <> submitted_by))",
            name="four_eyes",
        ),
    )
    op.create_index("ix_camera_config_versions_tenant_id", "camera_config_versions", ["tenant_id"])
    op.create_index("ix_camera_config_versions_camera_id", "camera_config_versions", ["camera_id"])
    op.create_foreign_key(
        "fk_cameras_tenant_active_config",
        "cameras",
        "camera_config_versions",
        ["tenant_id", "active_config_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.execute("""
        CREATE FUNCTION rs_camera_config_guard() RETURNS trigger
        LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'camera_config_versions rows cannot be deleted'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF NEW.config IS DISTINCT FROM OLD.config
               OR NEW.fingerprint IS DISTINCT FROM OLD.fingerprint
               OR NEW.revision IS DISTINCT FROM OLD.revision
               OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
               OR NEW.camera_id IS DISTINCT FROM OLD.camera_id
               OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
               OR NEW.reason IS DISTINCT FROM OLD.reason
               OR NEW.created_by IS DISTINCT FROM OLD.created_by
               OR NEW.created_at IS DISTINCT FROM OLD.created_at
               OR (OLD.submitted_by IS NOT NULL
                   AND NEW.submitted_by IS DISTINCT FROM OLD.submitted_by)
               OR (OLD.decided_by IS NOT NULL
                   AND NEW.decided_by IS DISTINCT FROM OLD.decided_by)
               OR (OLD.status <> 'draft'
                   AND NEW.validation_errors IS DISTINCT FROM OLD.validation_errors) THEN
                RAISE EXCEPTION 'camera config versions are immutable'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                   (OLD.status = 'draft' AND NEW.status IN ('validated', 'rejected'))
                OR (OLD.status = 'validated' AND NEW.status IN ('awaiting_approval', 'rejected'))
                OR (OLD.status = 'awaiting_approval' AND NEW.status IN ('approved', 'rejected'))
                OR (OLD.status = 'approved' AND NEW.status = 'active')
                OR (OLD.status = 'active' AND NEW.status = 'superseded')
                OR (OLD.status = 'superseded' AND NEW.status = 'active')) THEN
                RAISE EXCEPTION 'invalid config status transition % -> %', OLD.status, NEW.status
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER camera_config_versions_guard BEFORE UPDATE OR DELETE
        ON camera_config_versions FOR EACH ROW EXECUTE FUNCTION rs_camera_config_guard()
    """)

    # --- worker status (one row per camera) and bounded history
    op.create_table(
        "camera_worker_status",
        *_base_columns(),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("lease_epoch", sa.String(64), nullable=True),
        sa.Column("lease_expires_at", tz, nullable=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("last_heartbeat_at", tz, nullable=True),
        sa.Column("health", sa.String(24), nullable=True),
        sa.Column("applied_revision", sa.Integer(), nullable=True),
        sa.Column("applied_fingerprint", sa.String(64), nullable=True),
        sa.Column("applied_at", tz, nullable=True),
        sa.Column("last_ack_status", sa.String(16), nullable=True),
        sa.Column("last_ack_revision", sa.Integer(), nullable=True),
        sa.Column("last_ack_reason", sa.String(64), nullable=True),
        sa.Column("last_ack_at", tz, nullable=True),
        sa.Column("source_fps", sa.Float(), nullable=True),
        sa.Column("processing_fps", sa.Float(), nullable=True),
        sa.Column("last_frame_at", tz, nullable=True),
        sa.Column("dropped_frames", sa.BigInteger(), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.String(120), nullable=True),
        sa.Column("frame_width", sa.Integer(), nullable=True),
        sa.Column("frame_height", sa.Integer(), nullable=True),
        sa.Column("last_error_code", sa.String(40), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("conflict_epoch", sa.String(64), nullable=True),
        sa.Column("conflict_at", tz, nullable=True),
        sa.Column("updated_at", tz, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_camera_worker_status"),
        sa.UniqueConstraint("camera_id", name="uq_camera_worker_status_camera_id"),
        _tenant_fk("camera_worker_status"),
        _camera_fk("camera_worker_status"),
    )
    op.create_index("ix_camera_worker_status_tenant_id", "camera_worker_status", ["tenant_id"])
    op.create_table(
        "camera_health_events",
        *_base_columns(),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("at", tz, nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("worker_epoch", sa.String(64), nullable=True),
        sa.Column("health", sa.String(24), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=True),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("message", sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_camera_health_events"),
        _tenant_fk("camera_health_events"),
        _camera_fk("camera_health_events"),
    )
    op.create_index("ix_camera_health_events_tenant_id", "camera_health_events", ["tenant_id"])
    op.create_index(
        "ix_camera_health_events_camera_at", "camera_health_events", ["camera_id", "at"]
    )

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = rs_current_tenant())
            WITH CHECK (tenant_id = rs_current_tenant())
        """)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON camera_source_grants, camera_config_versions, "
        f"camera_worker_status TO {app}"
    )
    op.execute(f"GRANT SELECT, INSERT, DELETE ON camera_health_events TO {app}")


def downgrade() -> None:
    for table in ("camera_health_events", "camera_worker_status"):
        op.drop_table(table)
    op.drop_constraint("fk_cameras_tenant_active_config", "cameras", type_="foreignkey")
    op.execute("DROP TRIGGER IF EXISTS camera_config_versions_guard ON camera_config_versions")
    op.execute("DROP FUNCTION IF EXISTS rs_camera_config_guard()")
    op.drop_table("camera_config_versions")
    op.drop_table("camera_source_grants")
    for name in ("desired_enabled_state", "revision", "source_kind", "lifecycle_state"):
        op.drop_constraint(op.f(f"ck_cameras_{name}"), "cameras", type_="check")
    op.drop_constraint("fk_cameras_enable_requested_by_users", "cameras", type_="foreignkey")
    for column in (
        "enable_requested_at",
        "enable_requested_by",
        "disabled_reason",
        "active_config_id",
        "revision",
        "desired_enabled",
        "source_has_credentials",
        "source_url_enc",
        "source_display",
        "source_kind",
        "lifecycle_state",
    ):
        op.drop_column("cameras", column)
