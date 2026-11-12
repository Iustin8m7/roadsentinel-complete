"""Durable, tenant-scoped in-app events and per-user receipt state."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class NotificationEvent(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "alert_id"], ["alerts.tenant_id", "alerts.id"], ondelete="RESTRICT"),
        UniqueConstraint("tenant_id", "dedup_key", name="uq_notification_event_dedup"),
        UniqueConstraint("tenant_id", "sequence", name="uq_notification_event_tenant_seq"),
    )

    sequence: Mapped[int] = mapped_column(BigInteger)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    provenance: Mapped[str] = mapped_column(String(32))
    dedup_key: Mapped[str] = mapped_column(String(160))


class NotificationReceipt(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "notification_receipts"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "event_id"], ["notification_events.tenant_id", "notification_events.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="RESTRICT"),
        UniqueConstraint("tenant_id", "user_id", "event_id", name="uq_notification_receipt_user_event"),
        Index("ix_notification_receipts_user", "tenant_id", "user_id", "event_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationPreference(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="RESTRICT"),
        UniqueConstraint("tenant_id", "user_id", name="uq_notification_preference_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    sound_on_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
