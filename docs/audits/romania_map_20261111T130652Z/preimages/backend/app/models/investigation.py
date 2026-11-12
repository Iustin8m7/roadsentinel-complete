"""Investigation workspace: case notes (append-only revisions), timeline bookmarks, evidence
package export jobs and user-owned saved archive filters. All tenant-scoped (RLS, migration
0008). A "case" is an existing ``alerts`` row; nothing here duplicates it."""

from __future__ import annotations

import enum
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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class NoteKind(enum.StrEnum):
    observation = "observation"  # what is objectively visible in the evidence
    interpretation = "interpretation"  # the analyst's reading of it


class CaseNote(UUIDPk, TenantScoped, Timestamped, Base):
    """A note's identity and lifecycle. Its text lives in append-only ``case_note_revisions``;
    an edit adds a revision, a retraction only sets ``retracted_*`` (nothing is deleted)."""

    __tablename__ = "case_notes"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))
    current_revision: Mapped[int] = mapped_column(Integer, default=1)
    retracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retracted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    retract_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CaseNoteRevision(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "case_note_revisions"
    __table_args__ = (UniqueConstraint("note_id", "revision", name="uq_case_note_revisions_rev"),)

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_notes.id", ondelete="RESTRICT"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Optional reference into the case's evidence (validated against the case on write).
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=True
    )
    offset_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Copy of the detection box recorded by the pipeline in ``alerts.details.bbox`` (migration
    # 0010). Accepted only when it equals that recorded box; never drawn or inferred.
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)


class CaseBookmark(UUIDPk, TenantScoped, Timestamped, Base):
    """A labelled point on one evidence item's timeline (seconds from the clip start)."""

    __tablename__ = "case_bookmarks"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT")
    )
    offset_s: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(120))
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class ExportState(enum.StrEnum):
    pending_approval = "pending_approval"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    denied = "denied"
    canceled = "canceled"
    expired = "expired"


class ExportJob(UUIDPk, TenantScoped, Timestamped, Base):
    """Evidence package request + durable generation job (one row; claimed atomically)."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "requester_id", "idempotency_key", name="uq_export_jobs_idempotency"
        ),
        Index("ix_export_jobs_claim", "state", "lease_expires_at"),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64))
    include_original: Mapped[bool] = mapped_column(Boolean, default=False)
    # Evidence ids fixed at request time: the scope cannot grow after approval.
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    state: Mapped[str] = mapped_column(String(20), default=ExportState.pending_approval.value)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    package_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    package_key: Mapped[str | None] = mapped_column(String(400), nullable=True)
    package_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Storage outages seen by this job (migration 0010): retried without consuming an attempt,
    # up to exports.MAX_STORAGE_RETRIES.
    storage_retries: Mapped[int] = mapped_column(Integer, default=0, server_default="0")



# Reuse the local model and its established migration lineage.
from app.models.saved_search import SavedSearch  # noqa: E402,F401
