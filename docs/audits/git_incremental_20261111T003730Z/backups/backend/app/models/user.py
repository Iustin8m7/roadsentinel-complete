from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPk


class Role(enum.StrEnum):
    system_admin = "system_admin"
    tenant_admin = "tenant_admin"
    operator = "operator"
    patrol = "patrol"
    auditor = "auditor"


class User(UUIDPk, TenantScoped, Timestamped, Base):
    __tablename__ = "users"

    # Globally unique, always stored lower-cased.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # TOTP secret, encrypted with the tenant DEK (AAD binds tenant + field).
    totp_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Demo-only escape hatch: password-only login for this account. Set with
    # `python -m app.cli set-mfa-exempt`; every such login is audited as mfa=exempt.
    mfa_exempt: Mapped[bool] = mapped_column(Boolean, default=False)
    # Last accepted TOTP time-step: a code can never be replayed.
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
