"""Machine identities for the detection pipeline (service-to-service authentication)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class ServiceAccount(UUIDPk, TenantScoped, Timestamped, Base):
    """A pipeline instance allowed to create alerts/evidence for its own tenant only.

    ``camera_ids`` optionally narrows it further to specific cameras (NULL = every camera of
    the tenant). Service accounts can never read data."""

    __tablename__ = "service_accounts"

    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    camera_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class ServiceKey(UUIDPk, TenantScoped, Timestamped, Base):
    """An HMAC key of a service account. The secret is stored encrypted with the tenant DEK
    (HMAC verification needs the raw secret) and is shown exactly once at creation."""

    __tablename__ = "service_keys"

    # Composite FK (tenant_id, account_id) is created in migration 0003.
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    key_id: Mapped[str] = mapped_column(String(40), unique=True)
    secret_enc: Mapped[bytes] = mapped_column(LargeBinary)
    # Set when a newer key replaces this one: the old key keeps working until then (overlap).
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IngestNonce(Base):
    """Replay protection: every (key, nonce) pair is accepted once while its timestamp is
    within the allowed skew. Expired rows are purged (``python -m app.cli purge-nonces``)."""

    __tablename__ = "ingest_nonces"

    key_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
