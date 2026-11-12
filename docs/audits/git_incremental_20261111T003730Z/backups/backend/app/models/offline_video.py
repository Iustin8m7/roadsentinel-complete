from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class Recording(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "recordings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_recordings_tenant_id"),
        UniqueConstraint("tenant_id", "sha256", name="uq_recordings_tenant_sha256"),
        Index("ix_recordings_tenant_created", "tenant_id", "created_at"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    codec: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    fps_num: Mapped[int] = mapped_column(Integer)
    fps_den: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provenance_note: Mapped[str] = mapped_column(
        String(300),
        default="User-imported recorded screen capture; capture wall-clock time unverified.",
    )
    status: Mapped[str] = mapped_column(String(16), default="ready")
    crop: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    crop_revision: Mapped[int] = mapped_column(Integer, default=0)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalysisRun(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recordings.tenant_id", "recordings.id"],
            ondelete="CASCADE",
            name="fk_analysis_runs_recording_tenant",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_analysis_runs_tenant_id"),
        Index("ix_analysis_runs_tenant_recording", "tenant_id", "recording_id", "created_at"),
    )

    recording_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="queued")
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    config_sha256: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(100))
    model_sha256: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_frames: Mapped[int] = mapped_column(BigInteger, default=0)
    decoded_frames: Mapped[int] = mapped_column(BigInteger, default=0)
    skipped_frames: Mapped[int] = mapped_column(BigInteger, default=0)
    total_estimated_frames: Mapped[int] = mapped_column(BigInteger, default=0)
    latest_media_pts_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    inference_fps: Mapped[float] = mapped_column(Float, default=0)
    counts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_storage_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    output_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    preview_sequence: Mapped[int] = mapped_column(BigInteger, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    worker_instance: Mapped[str | None] = mapped_column(String(36), nullable=True)
    observation_storage_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    observation_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observation_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    observation_count: Mapped[int] = mapped_column(BigInteger, default=0)
    observation_schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observations_complete: Mapped[bool] = mapped_column(Boolean, default=False)
