"""Append-only attribution metadata; never an alternative incident/evidence system."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class LocationRevision(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "location_revisions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_location_revisions_tenant_id"),
        UniqueConstraint("tenant_id", "request_id", name="uq_location_request"),
        UniqueConstraint("tenant_id", "camera_id", "revision", name="uq_camera_geo_revision"),
        UniqueConstraint("tenant_id", "recording_id", "revision", name="uq_recording_geo_revision"),
        UniqueConstraint("tenant_id", "alert_id", "revision", name="uq_alert_geo_revision"),
        UniqueConstraint("tenant_id", "config_version_id", name="uq_geo_config_version"),
        *[
            ForeignKeyConstraint(
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
        ],
        Index("ix_geo_point", "tenant_id", "region", "latitude", "longitude"),
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    recording_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(BigInteger)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    state: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[str] = mapped_column(String(24))
    source_type: Mapped[str] = mapped_column(String(24))
    anchor_kind: Mapped[str] = mapped_column(String(24))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    region: Mapped[str] = mapped_column(String(24), default="unknown")
    county_code: Mapped[str | None] = mapped_column(String(12))
    city_label: Mapped[str | None] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(String(500))
    source_reference: Mapped[str] = mapped_column(String(300))
    motion: Mapped[str] = mapped_column(String(16), default="fixed")
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    source_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    config_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    config_revision: Mapped[int | None] = mapped_column(BigInteger)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class IncidentGeoSource(TenantScoped, Timestamped, Base):
    __tablename__ = "incident_geo_sources"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "alert_id"], ["alerts.tenant_id", "alerts.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recordings.tenant_id", "recordings.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "camera_location_id"],
            ["location_revisions.tenant_id", "location_revisions.id"],
            ondelete="RESTRICT",
        ),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    recording_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    camera_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
