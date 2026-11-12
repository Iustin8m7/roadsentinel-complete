"""Investigation completion (migration 0010): explicit case links, structured follow-up items
with an append-only history, and manual legal holds. All tenant-scoped (RLS); a "case" is an
existing ``alerts`` row."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk, utcnow


class CaseLink(UUIDPk, TenantScoped, Timestamped, Base):
    """An investigator-asserted relation between two cases. Stored once per pair in canonical
    order (``alert_a_id < alert_b_id``) so a link cannot exist twice; removal is soft."""

    __tablename__ = "case_links"
    __table_args__ = (
        CheckConstraint("alert_a_id < alert_b_id", name="ordered_pair"),
        Index(
            "ix_case_links_active_pair",
            "alert_a_id",
            "alert_b_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    alert_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    alert_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    reason: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class FollowupStatus(enum.StrEnum):
    open = "open"
    done = "done"
    cancelled = "cancelled"


class CaseFollowup(UUIDPk, TenantScoped, Timestamped, Base):
    """A durable, attributed task on a case. Its text is fixed at creation; status, assignee
    and due date change through audited transitions recorded in ``case_followup_events``."""

    __tablename__ = "case_followups"
    __table_args__ = (CheckConstraint("status IN ('open', 'done', 'cancelled')", name="status"),)

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(12), default=FollowupStatus.open.value)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Optimistic concurrency: a change names the revision it was based on.
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CaseFollowupEvent(UUIDPk, TenantScoped, Timestamped, Base):
    """Append-only history: one row per revision, holding the state after the change."""

    __tablename__ = "case_followup_events"
    __table_args__ = (
        UniqueConstraint("followup_id", "revision", name="uq_case_followup_events_rev"),
    )

    followup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_followups.id", ondelete="RESTRICT"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    change: Mapped[str] = mapped_column(String(16))  # created | status | assignee | due_date
    status: Mapped[str] = mapped_column(String(12))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class CaseLegalHold(UUIDPk, TenantScoped, Timestamped, Base):
    """Manual preservation order on a case, placed and released by a tenant admin. At most one
    active hold per case; released holds stay as history."""

    __tablename__ = "case_legal_holds"
    __table_args__ = (
        Index(
            "ix_case_legal_holds_active",
            "alert_id",
            unique=True,
            postgresql_where=text("released_at IS NULL"),
        ),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), index=True
    )
    placed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(500))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    release_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
