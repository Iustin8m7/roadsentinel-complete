"""Shapes for the investigation completion features: related cases and explicit links,
follow-up items, legal holds, timeline context, detection references, package verification and
the auditor's evidence-integrity view."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FollowupStatusName = Literal["open", "done", "cancelled"]
RelationKind = Literal["link", "same_track", "same_camera_window"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- related cases


class RelationReason(BaseModel):
    kind: RelationKind
    label: str  # Romanian, shown verbatim next to the related case
    link_id: uuid.UUID | None = None
    reason: str | None = None  # the investigator's stated reason (links only)
    created_by: str | None = None
    created_at: datetime | None = None
    can_remove: bool = False


class RelatedCase(BaseModel):
    number: int
    type: str
    type_label: str
    status: str
    priority: str
    observed_at: datetime
    camera_id: str
    reasons: list[RelationReason]


class LinkIn(_In):
    number: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=300)


class ContextEvent(BaseModel):
    """A neighbouring event from the same camera, as a marker on the case timeline."""

    number: int
    type: str
    type_label: str
    status: str
    observed_at: datetime
    delta_s: float  # seconds relative to this case's detection (negative = before)


class TimelineContext(BaseModel):
    window_s: int
    limit_per_side: int
    before: list[ContextEvent]
    after: list[ContextEvent]
    truncated_before: bool
    truncated_after: bool
    note: str


# --------------------------------------------------------------------------- follow-ups


class FollowupIn(_In):
    body: str = Field(min_length=1, max_length=500)
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class FollowupPatch(_In):
    revision: int = Field(ge=1)
    status: FollowupStatusName | None = None
    assignee_id: uuid.UUID | None = None  # explicit null clears the assignee
    due_date: date | None = None  # explicit null clears the due date


class FollowupEventOut(BaseModel):
    revision: int
    change: str
    status: FollowupStatusName
    assignee: str | None
    due_date: date | None
    actor: str
    at: datetime


class FollowupOut(BaseModel):
    id: uuid.UUID
    body: str
    status: FollowupStatusName
    author: str
    author_is_me: bool
    assignee_id: uuid.UUID | None
    assignee: str | None
    assignee_is_me: bool
    due_date: date | None
    overdue: bool
    created_at: datetime
    updated_at: datetime
    revision: int
    can_change_status: bool
    can_reassign: bool
    history: list[FollowupEventOut]


class PersonOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    is_me: bool


# --------------------------------------------------------------------------- legal hold


class LegalHoldIn(_In):
    reason: str = Field(min_length=10, max_length=500)


class LegalHoldOut(BaseModel):
    id: uuid.UUID
    active: bool
    reason: str
    placed_by: str
    placed_at: datetime
    released_at: datetime | None
    released_by: str | None
    release_reason: str | None


class LegalHoldState(BaseModel):
    active: LegalHoldOut | None
    history: list[LegalHoldOut]
    can_manage: bool
    effect: str  # what the hold does and does not do, shown verbatim


# --------------------------------------------------------------------------- references


class DetectionReference(BaseModel):
    """What a note may point at: only values the pipeline recorded for this case."""

    track_id: int | None
    bbox: list[float] | None
    bbox_status: Literal["recorded", "not_recorded", "malformed"]
    video_t_s: float | None
    run_id: str | None
    note: str


# --------------------------------------------------------------------------- verification


class ServerRecord(BaseModel):
    export_id: uuid.UUID
    event_id: int
    state: str


class PackageVerifyOut(BaseModel):
    ok: bool
    manifest_sha256: str | None
    expected_manifest_sha256: str | None
    files_checked: int
    errors: list[str]
    size_bytes: int
    server_record: ServerRecord | None  # this package's job, if you can see it
    note: str


IntegrityState = Literal[
    "match", "mismatch", "missing", "purged", "unavailable", "unreadable", "no_hash", "not_checked"
]


class EvidenceIntegrityItem(BaseModel):
    id: uuid.UUID
    kind: str
    event_id: int | None
    camera_id: str | None
    created_at: datetime
    size_bytes: int
    sha256_recorded: bool
    distinct_original: bool
    storage_state: Literal["available", "missing", "purged", "unavailable"]
    integrity: IntegrityState


class EvidenceIntegrityPage(BaseModel):
    items: list[EvidenceIntegrityItem]
    next_cursor: str | None
    total: int
    verified: bool
    note: str
