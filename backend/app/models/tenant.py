from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPk


class Tenant(UUIDPk, Timestamped, Base):
    """A police unit. ``is_platform`` marks the single operator tenant of system admins."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    is_platform: Mapped[bool] = mapped_column(Boolean, default=False)


class TenantKey(UUIDPk, Timestamped, Base):
    """A per-tenant data key, stored only in wrapped (encrypted) form.

    ``purpose`` is ``data`` (AES-256-GCM field/file encryption) or ``index`` (HMAC blind index).
    ``version`` increases on rotation; old versions stay available for decryption.
    """

    __tablename__ = "tenant_keys"
    __table_args__ = (UniqueConstraint("tenant_id", "purpose", "version"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer)
    wrapped_key: Mapped[bytes] = mapped_column(LargeBinary)
    master_key_version: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
