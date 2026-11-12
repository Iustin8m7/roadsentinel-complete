"""Shapes of the API.md contract (copied from ``roadsentinel/schemas.py``: no field renamed or
removed). Additions are optional fields only, so existing clients keep working."""

from __future__ import annotations

import json
import uuid as uuid_
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.catalog import ACTIONS, EVENT_TYPES, OBJECT_CLASSES

CAMERA_ID = r"^[A-Za-z0-9_-]{1,64}$"

PriorityName = Literal["critical", "high", "medium", "info"]
StatusName = Literal["new", "confirmed", "rejected"]
VlmStatus = Literal["pending", "confirmed", "rejected", "uncertain", "skipped"]
ObjectClass = Literal["car", "truck", "bus", "motorcycle", "bicycle", "person", "object"]

REDACTION_LEVELS = ("full", "heads_only", "off")
MAX_DETAILS_BYTES = 4096
MAX_DETAILS_DEPTH = 3


class Event(BaseModel):
    id: int
    camera_id: str
    camera_name: str | None
    location: str | None
    type: str
    priority: PriorityName
    occurred_at: datetime  # local time at the camera, without offset
    video_t: float
    track_id: int | None
    object_class: str | None
    speed_kmh: float | None
    rule: str
    details: dict[str, Any]
    keyframe_url: str | None
    clip_url: str | None
    vlm_status: VlmStatus
    vlm_text: str | None
    status: StatusName
    action: str | None
    # Additive: how the evidence was redacted ("full" or "heads_only": plates not blurred).
    redaction: str | None = None
    # False when only one stored copy exists: no unblur / original export is possible.
    has_original: bool | None = None
    # True when the retention policy already deleted the files (the alert itself remains).
    evidence_purged: bool = False


class AuditEntry(BaseModel):
    id: int
    event_id: int | None
    actor: str
    action: str
    note: str | None
    at: datetime
    type: str | None = None


class EventDetail(Event):
    audit: list[AuditEntry]


class Decision(BaseModel):
    decision: Literal["confirm", "reject"]
    action: str | None = None
    note: str | None = Field(default=None, max_length=500)


class Login(BaseModel):
    operator: str = Field(min_length=3, max_length=320)  # the account e-mail
    password: str = Field(min_length=1, max_length=1024)


class MfaCode(BaseModel):
    code: str | None = Field(default=None, pattern=r"^\d{6}$")
    recovery_code: str | None = Field(default=None, max_length=64)


class Me(BaseModel):
    operator: str | None
    auth_required: bool
    # Additive (MFA): set after a correct password, before the second factor.
    mfa_required: bool = False
    mfa_enrollment: bool = False


class Camera(BaseModel):
    id: str  # slug
    name: str
    location: str | None
    video_url: str | None


class CameraOut(Camera):
    source_kind: str | None = None
    # Additive: registry fields for the police UI's map (the contract id stays the slug).
    uuid: uuid_.UUID
    timezone: str = "Europe/Bucharest"
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True
    last_seen_at: datetime | None = None
    # Measured frame rate and per-rule capability as reported by the pipeline heartbeat.
    status_info: dict[str, Any] | None = None


class Stats(BaseModel):
    total: int
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_type: dict[str, int]
    vlm_available: bool


class Meta(BaseModel):
    event_types: dict[str, dict[str, str]]
    actions: dict[str, str]


class SearchResponse(BaseModel):
    filter: dict[str, Any]
    results: list[Event]
    next_cursor: str | None = None


class SearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: str = Field(min_length=1, max_length=500)
    cursor: str | None = Field(default=None, min_length=16, max_length=1024)
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def _strip_nonempty_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class SearchPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cursor: str | None = Field(default=None, min_length=16, max_length=1024)
    limit: int = Field(default=50, ge=1, le=100)


class SavedSearchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=500)

    @field_validator("name", "query")
    @classmethod
    def _strip_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class SavedSearchOut(BaseModel):
    id: uuid_.UUID
    name: str
    filters: dict[str, Any]
    created_at: datetime


class Created(BaseModel):
    id: int


def _depth(value: Any, level: int = 1) -> int:
    if isinstance(value, dict):
        return max([level, *(_depth(v, level + 1) for v in value.values())])
    if isinstance(value, list):
        return max([level, *(_depth(v, level + 1) for v in value)])
    return level - 1


class IngestEvent(BaseModel):
    """What the pipeline posts. Unknown fields are refused; priority is never accepted (it is
    derived from ``type``); camera name and location come from the registered camera."""

    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(pattern=CAMERA_ID)
    camera_name: str | None = Field(default=None, max_length=200)  # ignored
    location: str | None = Field(default=None, max_length=300)  # ignored
    type: str
    occurred_at: datetime
    video_t: float = Field(ge=0, le=86400)
    track_id: int | None = Field(default=None, ge=0, le=2**31 - 1)
    object_class: ObjectClass | None = None
    speed_kmh: float | None = Field(default=None, ge=0, le=400)
    rule: str = Field(min_length=1, max_length=300)
    details: dict[str, Any] = {}
    # Idempotency: a retry with the same key returns the existing alert instead of a duplicate.
    event_key: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]{8,80}$")
    vlm_status: VlmStatus = "pending"
    vlm_text: str | None = Field(default=None, max_length=300)

    @field_validator("vlm_text", mode="before")
    @classmethod
    def _truncate_vlm_text(cls, v: object) -> object:
        # Model output can be long; truncating beats losing the whole alert mid-demo.
        return v[:300] if isinstance(v, str) else v

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError("unknown event type")
        return v

    @field_validator("occurred_at")
    @classmethod
    def _local_time(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            raise ValueError("occurred_at must be local camera time without a UTC offset")
        return v

    @field_validator("details")
    @classmethod
    def _bounded(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(v, default=str)) > MAX_DETAILS_BYTES:
            raise ValueError("details too large")
        if _depth(v) > MAX_DETAILS_DEPTH:
            raise ValueError("details nested too deeply")
        if v.get("redaction") not in (None, *REDACTION_LEVELS):
            raise ValueError("details.redaction must be 'full', 'heads_only' or 'off'")
        return v


assert set(OBJECT_CLASSES) == set(ObjectClass.__args__)  # type: ignore[attr-defined]
assert all(a.isidentifier() for a in ACTIONS)
