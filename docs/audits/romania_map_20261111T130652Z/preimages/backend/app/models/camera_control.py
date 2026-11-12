"""Camera control plane: processing authorizations (grants), immutable config versions, worker
status and a bounded health-event history. Business rules live in
``app.services.camera_control``; database-level guards (CHECKs, immutability trigger, composite
tenant FKs, RLS) are created in migration 0007."""

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
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk, utcnow


class CameraSourceGrant(UUIDPk, TenantScoped, Timestamped, Base):
    """A documented authorization to process one camera's media. A viewing-page link is not one.

    Rows are never deleted; revocation is a status change. ``camera_id`` has a composite tenant
    FK (migration 0007)."""

    __tablename__ = "camera_source_grants"

    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    granting_party: Mapped[str] = mapped_column(String(200))
    # written_agreement | licence | own_infrastructure | statutory_mandate
    basis: Mapped[str] = mapped_column(String(32))
    basis_reference: Mapped[str] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(String(500))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Must equal the camera's source_kind for the grant to apply.
    capture_method: Mapped[str] = mapped_column(String(32))
    max_analysis_fps: Mapped[float] = mapped_column(Float)
    max_frame_height: Mapped[int] = mapped_column(Integer)
    retention_days: Mapped[int] = mapped_column(Integer)
    export_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    # events_only | events_and_recordings (annotated full recordings need the latter).
    media_scope: Mapped[str] = mapped_column(String(32))
    reviewed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | revoked
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CameraConfigVersion(UUIDPk, TenantScoped, Timestamped, Base):
    """One immutable configuration snapshot of a camera. ``config``/``fingerprint``/``revision``
    can never change after insert and rows can never be deleted (trigger, migration 0007);
    only the review/activation status and its attribution columns move forward."""

    __tablename__ = "camera_config_versions"
    __table_args__ = (
        UniqueConstraint("camera_id", "revision", name="uq_camera_config_versions_camera_rev"),
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fingerprint: Mapped[str] = mapped_column(String(64))
    # draft | validated | awaiting_approval | approved | active | superseded | rejected
    status: Mapped[str] = mapped_column(String(20), default="draft")
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    reason: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CameraWorkerStatus(UUIDPk, TenantScoped, Base):
    """Latest worker telemetry for one camera (one row per camera) plus the processing lease.

    Only the lease holder's heartbeats update the metrics; another worker epoch heartbeating
    while the lease is valid is recorded as a conflict and told to stop."""

    __tablename__ = "camera_worker_status"
    __table_args__ = (UniqueConstraint("camera_id", name="uq_camera_worker_status_camera_id"),)

    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    lease_epoch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seq: Mapped[int] = mapped_column(BigInteger, default=0)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    health: Mapped[str | None] = mapped_column(String(24), nullable=True)
    applied_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ack_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_ack_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_ack_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_frame_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dropped_frames: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    queue_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    frame_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    conflict_epoch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conflict_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # --- migration 0009: bounded runtime metrics measured by the worker (see the contract doc).
    # Latency of the model.track call (pre/post-processing + tracker) over the worker's window.
    inference_p50_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rss_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Frozen-image check: mean absolute grey difference between consecutive sampled frames,
    # the worker's confidence that the image is frozen, and seconds since the last change.
    frozen_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    frozen_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    unchanged_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Source identity fingerprint reported by the current lease holder (never returned in full).
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # {state: ISO time of the last failure notification}: throttle per camera and state.
    failure_notified: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)


class CameraHealthEvent(UUIDPk, TenantScoped, Base):
    """Bounded history of state changes (health transitions, acks, lease changes/conflicts,
    admin control actions). Capped per camera on insert (see HEALTH_HISTORY_CAP)."""

    __tablename__ = "camera_health_events"
    __table_args__ = (Index("ix_camera_health_events_camera_at", "camera_id", "at"),)

    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(24))
    worker_epoch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    health: Mapped[str | None] = mapped_column(String(24), nullable=True)
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(String(300), nullable=True)
