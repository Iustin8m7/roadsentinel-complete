"""Operational domain: cameras, alerts and evidence (clip metadata)."""

from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    FetchedValue,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class Priority(enum.StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    info = "info"


PRIORITY_ORDER = {Priority.critical: 0, Priority.high: 1, Priority.medium: 2, Priority.info: 3}


class AlertStatus(enum.StrEnum):
    new = "new"
    confirmed = "confirmed"
    rejected = "rejected"


class Camera(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "cameras"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_cameras_tenant_slug"),)

    # Public id in the API.md contract (pattern ^[A-Za-z0-9_-]{1,64}$), unique per tenant.
    slug: Mapped[str] = mapped_column(String(64), default=lambda: f"cam-{secrets.token_hex(4)}")
    # The pipeline sends naive local times; this zone converts them to UTC and back.
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Bucharest")
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Last heartbeat or event from the pipeline; the UI shows the camera as live while recent.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Pipeline-reported measured fps and rule capabilities (replaced by each heartbeat).
    status_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Camera-control plane fields (introduced by integration revision 0016).
    lifecycle_state: Mapped[str] = mapped_column(String(16), default="legacy", server_default="legacy")
    source_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_display: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_has_credentials: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    desired_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active_config_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    enable_requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    enable_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_alerts_tenant_number"),
        Index("ix_alerts_queue", "tenant_id", "status", "priority", "detected_at"),
        Index(
            "uq_alerts_event_key",
            "tenant_id",
            "camera_id",
            "event_key",
            unique=True,
            postgresql_where=text("event_key IS NOT NULL"),
        ),
    )

    # Public, per-tenant monotonic id of the API.md contract (UUID stays the internal key).
    # Assigned by the ``alerts_number`` trigger (migration 0004) and fetched back on insert.
    number: Mapped[int] = mapped_column(BigInteger, server_default=FetchedValue())

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"), index=True
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="alert_priority"))
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"), default=AlertStatus.new
    )
    event_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(500))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Plate number: AES-256-GCM ciphertext + HMAC blind index for exact-match search.
    plate_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    plate_bidx: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, index=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Detection details sent by the pipeline (API.md ``Event``), bounded on ingestion.
    video_t: Mapped[float | None] = mapped_column(Float, nullable=True)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    object_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    event_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Patrol workflow: assigned -> en_route -> on_scene -> done (forward only), set by the assignee.
    patrol_status: Mapped[str | None] = mapped_column(String(12), nullable=True)
    patrol_status_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # First time someone who can decide opened the alert (response-time statistics).
    first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Legal hold: evidence of a held alert is never purged by the retention job.
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    legal_hold_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    legal_hold_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    legal_hold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule: Mapped[str | None] = mapped_column(String(300), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    vlm_status: Mapped[str] = mapped_column(String(12), default="skipped")
    vlm_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    action: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Set when a dev/demo camera reset hides undecided alerts. Nothing is ever deleted.
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Evidence(UUIDPk, TenantScoped, Timestamped, Base):
    """Metadata for an encrypted evidence file. Two variants exist on disk: the redacted
    (faces/plates blurred) version shown by default, and the original, which needs a grant."""

    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_purge_scan", "tenant_id", "kind", "created_at"),)

    # An alert's keyframe/clip, or (alert_id NULL) a camera's annotated recording.
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32))  # keyframe | clip | camera_video
    # What the pipeline reports it blurred: "full" (heuristic faces+plates), "heads_only",
    # "off" (nothing: shown as FĂRĂ REDACTARE) or "unknown" (pipeline did not say).
    redaction: Mapped[str] = mapped_column(String(20), default="full")
    # False when only one stored copy exists (no distinct original): unblur/export-original
    # are refused for such evidence.
    has_original: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    content_type: Mapped[str] = mapped_column(String(100))
    redacted_path: Mapped[str] = mapped_column(String(400))
    original_path: Mapped[str] = mapped_column(String(400))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    # SHA-256 of the original plaintext, for chain-of-custody checks.
    sha256: Mapped[str] = mapped_column(String(64))
    key_version: Mapped[int] = mapped_column(Integer)
    # Set by the retention job after the files were deleted; the row (hash, size) stays for audit.
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purge_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
