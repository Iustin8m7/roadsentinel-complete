from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class ApprovalKind(enum.StrEnum):
    unblur = "unblur"
    export = "export"
    account_reset = "account_reset"


class ApprovalStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    denied = "denied"
    revoked = "revoked"


class ApprovalRequest(UUIDPk, TenantScoped, Timestamped, Base):
    """Generic four-eyes request. Once approved it acts as a time-limited grant for the
    requester on one resource (``grant_expires_at``)."""

    __tablename__ = "approval_requests"

    kind: Mapped[ApprovalKind] = mapped_column(Enum(ApprovalKind, name="approval_kind"))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    justification: Mapped[str] = mapped_column(String(2000))
    case_reference: Mapped[str] = mapped_column(String(100))
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"), default=ApprovalStatus.pending
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    grant_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Kind-specific parameters (account_reset: {"reset_mfa": bool}).
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
