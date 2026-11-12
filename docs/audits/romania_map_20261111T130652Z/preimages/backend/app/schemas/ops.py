from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertStatus, Priority


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    location: str
    timezone: str
    latitude: float | None
    longitude: float | None
    is_active: bool


class CameraIn(BaseModel):
    managed: bool = False
    slug: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    location: str = Field(min_length=2, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str = Field(default="Europe/Bucharest", max_length=64)


class CameraWorkerCommandIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_ref: str = Field(min_length=5, max_length=72, pattern=r"^[A-Za-z0-9_-]+\.ya?ml$")


class CameraUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, min_length=2, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class AlertOut(BaseModel):
    id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: str | None = None
    priority: Priority
    status: AlertStatus
    event_type: str
    description: str
    detected_at: datetime
    plate_masked: str | None
    assigned_to: uuid.UUID | None
    assigned_to_name: str | None = None
    patrol_status: str | None = None
    patrol_status_at: datetime | None = None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    evidence_ids: list[uuid.UUID] = []


class AlertIn(BaseModel):
    camera_id: uuid.UUID
    priority: Priority
    event_type: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    description: str = Field(min_length=2, max_length=500)
    plate: str | None = Field(default=None, max_length=20)
    detected_at: datetime | None = None


class AlertDecisionIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AlertAssignIn(BaseModel):
    user_id: uuid.UUID


class EvidenceOut(BaseModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    kind: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    redaction: str = "unknown"
    has_original: bool = False
    unblur_grant_expires_at: datetime | None = None
    # Only populated while the viewer holds an active unblur grant.
    plate: str | None = None


class EvidenceAccessIn(BaseModel):
    variant: Literal["redacted", "original"] = "redacted"


class SignedUrlOut(BaseModel):
    url: str
    expires_at: datetime


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=1000, pattern=r"^https://")
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=100)


class VapidKeyOut(BaseModel):
    public_key: str | None
