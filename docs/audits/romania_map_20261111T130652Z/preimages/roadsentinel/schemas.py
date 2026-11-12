"""API data shapes: the contract between the backend and any frontend. See API.md."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

CAMERA_ID = r"^[A-Za-z0-9_-]{1,64}$"   # also used in media keys, so no dots or slashes

Priority = Literal["critical", "high", "medium", "info"]
Status = Literal["new", "confirmed", "rejected"]
VlmStatus = Literal["pending", "confirmed", "rejected", "uncertain", "skipped"]


class Event(BaseModel):
    id: int
    camera_id: str
    camera_name: str | None
    location: str | None
    type: str                       # see GET /api/meta for labels
    priority: Priority
    occurred_at: datetime           # local time at the camera
    video_t: float                  # seconds into the source recording
    track_id: int | None
    object_class: str | None     # car | truck | bus | motorcycle | person | null (scene-level)
    speed_kmh: float | None
    rule: str                       # human-readable: which threshold fired and by how much
    details: dict[str, Any]         # rule-specific numbers, plus "vlm" verdict when available
    keyframe_url: str | None
    clip_url: str | None
    vlm_status: VlmStatus
    vlm_text: str | None         # one-line Romanian description from the vision model
    status: Status
    action: str | None


class AuditEntry(BaseModel):
    id: int
    event_id: int | None
    actor: str
    action: str                     # detected | viewed | confirmed | rejected | vlm_confirmed | ...
    note: str | None
    at: datetime
    type: str | None = None      # event type, on GET /api/audit


class EventDetail(Event):
    audit: list[AuditEntry]


class Decision(BaseModel):
    decision: Literal["confirm", "reject"]
    action: str | None = None    # required when confirming; key from GET /api/meta "actions"
    note: str | None = None


class Login(BaseModel):
    operator: str
    password: str


class Me(BaseModel):
    operator: str | None
    auth_required: bool


class Camera(BaseModel):
    id: str
    name: str
    location: str | None
    video_url: str | None        # annotated recording, when one has been processed


class Stats(BaseModel):
    total: int
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_type: dict[str, int]
    vlm_available: bool


class Meta(BaseModel):
    event_types: dict[str, dict[str, str]]   # type -> {"priority", "label"}
    actions: dict[str, str]                  # action key -> Romanian label


class SearchResponse(BaseModel):
    filter: dict[str, Any]          # how the query was understood; "explanation" is shown to the user
    results: list[Event]


class IngestEvent(BaseModel):
    """What the pipeline posts. Priority is not accepted: the server derives it from the type."""
    camera_id: str = Field(pattern=CAMERA_ID)
    camera_name: str | None = None
    location: str | None = None
    type: str
    occurred_at: datetime            # local wall-clock time, without a UTC offset
    video_t: float
    track_id: int | None = None
    object_class: Literal["car", "truck", "bus", "motorcycle", "bicycle", "person"] | None = None
    speed_kmh: float | None = None
    rule: str = Field(min_length=1)
    details: dict[str, Any] = {}
    vlm_status: VlmStatus = "pending"
    vlm_text: str | None = None

    @field_validator("type")
    @classmethod
    def known_type(cls, v):
        from .rules import EVENT_TYPES

        if v not in EVENT_TYPES:
            raise ValueError(f"tip de eveniment necunoscut: {v}")
        return v

    @field_validator("occurred_at")
    @classmethod
    def local_time(cls, v):
        if v.tzinfo is not None:
            raise ValueError("occurred_at trebuie să fie ora locală, fără fus orar")
        return v


class Created(BaseModel):
    id: int
