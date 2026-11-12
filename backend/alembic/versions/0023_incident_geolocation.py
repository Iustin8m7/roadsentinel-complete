"""Append-only geographic provenance and canonical incident source links. No coordinate backfill.

Revision ID: 0023
Revises: 0022
"""

import os

import sqlalchemy as sa
from sqlalchemy.engine import make_url

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant-composite targets; do not change existing primary keys or historical rows.
    for table in ("cameras", "alerts", "users", "camera_config_versions"):
        op.create_unique_constraint(f"uq_geo_{table}_tenant_id", table, ["tenant_id", "id"])
    from sqlalchemy.dialects.postgresql import UUID

    bind = op.get_bind()
    uuid_fields = (
        "camera_id",
        "recording_id",
        "alert_id",
        "actor_id",
        "request_id",
        "source_location_id",
        "config_version_id",
        "proposal_id",
    )
    columns = [
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]
    columns += [
        sa.Column(name, UUID(as_uuid=True), nullable=name not in {"actor_id", "request_id"})
        for name in uuid_fields
    ]
    columns += [
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("config_revision", sa.BigInteger()),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
    ]
    columns += [sa.Column(name, sa.Float()) for name in ("latitude", "longitude", "accuracy_m")]
    columns += [
        sa.Column(name, sa.String(size), nullable=nullable)
        for name, size, nullable in (
            ("state", 16, False),
            ("confidence", 24, False),
            ("source_type", 24, False),
            ("anchor_kind", 24, False),
            ("region", 24, False),
            ("county_code", 12, True),
            ("city_label", 100, True),
            ("explanation", 500, False),
            ("source_reference", 300, False),
            ("motion", 16, False),
        )
    ]
    constraints = [
        sa.UniqueConstraint("tenant_id", "id", name="uq_location_revisions_tenant_id"),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_location_request"),
        sa.UniqueConstraint("tenant_id", "config_version_id", name="uq_geo_config_version"),
    ]
    constraints += [
        sa.UniqueConstraint("tenant_id", col, "revision", name=f"uq_{name}_geo_revision")
        for name, col in (
            ("camera", "camera_id"),
            ("recording", "recording_id"),
            ("alert", "alert_id"),
        )
    ]
    constraints += [
        sa.ForeignKeyConstraint(
            ["tenant_id", col],
            [f"{table}.tenant_id", f"{table}.id"],
            ondelete="RESTRICT",
            name=f"fk_geo_{col}",
        )
        for col, table in (
            ("camera_id", "cameras"),
            ("recording_id", "recordings"),
            ("alert_id", "alerts"),
            ("actor_id", "users"),
            ("source_location_id", "location_revisions"),
            ("config_version_id", "camera_config_versions"),
        )
    ]
    op.create_table("location_revisions", *columns, *constraints)
    op.create_index("ix_location_revisions_tenant_id", "location_revisions", ["tenant_id"])
    op.create_index(
        "ix_geo_point", "location_revisions", ["tenant_id", "region", "latitude", "longitude"]
    )
    op.create_table(
        "incident_geo_sources",
        sa.Column("alert_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recording_id", UUID(as_uuid=True)),
        sa.Column("camera_location_id", UUID(as_uuid=True)),
        *[
            sa.ForeignKeyConstraint(
                ["tenant_id", col], [f"{table}.tenant_id", f"{table}.id"], ondelete="RESTRICT"
            )
            for col, table in (
                ("alert_id", "alerts"),
                ("recording_id", "recordings"),
                ("camera_location_id", "location_revisions"),
            )
        ],
    )
    op.create_index("ix_incident_geo_sources_tenant_id", "incident_geo_sources", ["tenant_id"])
    op.create_index(
        "ix_incident_geo_sources_recording_id", "incident_geo_sources", ["recording_id"]
    )
    op.create_check_constraint(
        "one_subject", "location_revisions", "num_nonnulls(camera_id,recording_id,alert_id)=1"
    )
    op.create_check_constraint(
        "geo_coordinates",
        "location_revisions",
        "(latitude IS NULL AND longitude IS NULL) OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND NOT (latitude=0 AND longitude=0))",
    )
    op.create_check_constraint(
        "geo_accuracy",
        "location_revisions",
        "accuracy_m IS NULL OR accuracy_m BETWEEN 1 AND 1000000",
    )
    op.create_check_constraint(
        "geo_state",
        "location_revisions",
        "state IN ('confirmed','pending','rejected','unknown') AND revision>0",
    )
    op.create_check_constraint(
        "geo_confirmed",
        "location_revisions",
        "state!='confirmed' OR (latitude IS NOT NULL AND longitude IS NOT NULL AND accuracy_m IS NOT NULL AND motion='fixed')",
    )
    op.create_check_constraint(
        "geo_unknown",
        "location_revisions",
        "state!='unknown' OR (latitude IS NULL AND longitude IS NULL)",
    )
    op.create_check_constraint(
        "geo_source_choice",
        "incident_geo_sources",
        "num_nonnulls(recording_id,camera_location_id)<=1",
    )
    role = make_url(os.environ["RS_DATABASE_URL"]).username
    if not role or not role.replace("_", "").isalnum():
        raise ValueError("Invalid app role")
    quoted = bind.dialect.identifier_preparer.quote(role)
    for table in ("location_revisions", "incident_geo_sources"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING (tenant_id=rs_current_tenant()) WITH CHECK (tenant_id=rs_current_tenant())"
        )
        op.execute(f"GRANT SELECT,INSERT ON {table} TO {quoted}")
    op.execute(
        """CREATE FUNCTION rs_geo_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION 'Geographic revisions and incident source links are immutable'; END $$"""
    )
    for table in ("location_revisions", "incident_geo_sources"):
        op.execute(
            f"CREATE TRIGGER geo_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rs_geo_immutable()"
        )


def downgrade():
    # Explicit disposable-only downgrade drops new metadata, never old media/incidents.
    op.drop_table("incident_geo_sources")
    op.drop_table("location_revisions")
    op.execute("DROP FUNCTION rs_geo_immutable()")
    for table in ("camera_config_versions", "users", "alerts", "cameras"):
        op.drop_constraint(f"uq_geo_{table}_tenant_id", table, type_="unique")
