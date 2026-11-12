from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk

RETENTION_KINDS = ("keyframe", "clip", "camera_video", "confirmed_case")


class RetentionPolicy(UUIDPk, TenantScoped, Timestamped, Base):
    """How many days evidence of one kind is kept. ``confirmed_case`` applies to the evidence of
    alerts an operator confirmed (kept longer than unreviewed or rejected material)."""

    __tablename__ = "retention_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", name="uq_retention_policies_tenant_kind"),
        CheckConstraint("days >= 1 AND days <= 3650", name="ck_retention_policies_days"),
        CheckConstraint(
            "kind IN ('keyframe', 'clip', 'camera_video', 'confirmed_case')",
            name="ck_retention_policies_kind",
        ),
    )

    kind: Mapped[str] = mapped_column(String(32))
    days: Mapped[int] = mapped_column(Integer)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
