from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class SavedSearch(UUIDPk, TenantScoped, Timestamped, Base):
    """A user's reusable, parsed archive filter; free-text query strings are not retained."""

    __tablename__ = "saved_searches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_id", "name", name="uq_saved_searches_owner_name"),
        ForeignKeyConstraint(
            ["tenant_id", "owner_id"],
            ["users.tenant_id", "users.id"],
            name="fk_saved_searches_tenant_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint("jsonb_typeof(filters) = 'object'", name="filters_object"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
