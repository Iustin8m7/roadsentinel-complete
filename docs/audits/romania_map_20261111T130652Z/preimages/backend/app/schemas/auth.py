from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models import Role
from app.schemas.common import Email


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=256)


class LoginOut(BaseModel):
    mfa_required: bool = True
    enrollment_required: bool


class MfaIn(BaseModel):
    code: str | None = Field(default=None, max_length=10)
    recovery_code: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _one_factor(self) -> MfaIn:
        if bool(self.code) == bool(self.recovery_code):
            raise ValueError("provide exactly one of code or recovery_code")
        return self


class EnrollStartOut(BaseModel):
    otpauth_uri: str
    qr_svg_data_uri: str
    secret: str


class EnrollConfirmIn(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class EnrollConfirmOut(BaseModel):
    recovery_codes: list[str]


class CsrfOut(BaseModel):
    csrf_token: str


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: Role
    tenant_id: uuid.UUID
    tenant_name: str
    permissions: list[str]
    session_id: uuid.UUID
    mfa_fresh_until: datetime


class InvitationInspectIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class InvitationInspectOut(BaseModel):
    email: str
    role: Role
    tenant_name: str
    expires_at: datetime


class InvitationAcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    display_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=1, max_length=256)


class SessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip: str | None
    user_agent: str | None
    revoked_at: datetime | None
    revoked_reason: str | None
    current: bool = False


class ResetInspectOut(BaseModel):
    email: str
    reset_mfa: bool
    expires_at: datetime


class ResetAcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)
