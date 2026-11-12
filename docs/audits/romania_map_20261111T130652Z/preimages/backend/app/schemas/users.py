from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Role
from app.schemas.common import Email


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: Role
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class UserUpdateIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class InvitationIn(BaseModel):
    email: Email
    role: Role


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationCreatedOut(InvitationOut):
    # Shown exactly once. In production this would be e-mailed instead of returned.
    token: str
    accept_path: str


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class TenantCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    admin_email: Email


class TenantCreatedOut(BaseModel):
    tenant: TenantOut
    admin_invitation: InvitationCreatedOut


class KeyRotationOut(BaseModel):
    new_data_key_version: int
    reencrypted_fields: int


class ResetRequestIn(BaseModel):
    reset_mfa: bool = False  # lost authenticator: remove TOTP + recovery codes (must enroll again)
    justification: str = Field(min_length=20, max_length=2000)
    case_reference: str = Field(min_length=3, max_length=100)


class ResetIssuedOut(BaseModel):
    # Shown exactly once, to the requester, who hands it to the user out of band.
    token: str
    accept_path: str
    expires_at: datetime
