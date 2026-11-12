"""Request/response shapes of the investigation workspace (case dossier, notes, bookmarks,
archive search, saved filters, evidence-package exports)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas import casework as cw
from app.schemas.contract import AuditEntry

NoteKindName = Literal["observation", "interpretation"]
StorageState = Literal["available", "missing", "purged", "unavailable"]
IDEMPOTENCY_KEY = r"^[A-Za-z0-9_-]{8,64}$"


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- notes


class NoteIn(_In):
    kind: NoteKindName
    body: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    evidence_id: uuid.UUID | None = None
    offset_s: float | None = Field(default=None, ge=0, le=86400)
    track_id: int | None = Field(default=None, ge=0, le=2**31 - 1)
    # Must equal the detection box recorded for the case (details.bbox); never free-drawn.
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class NoteReviseIn(_In):
    body: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    evidence_id: uuid.UUID | None = None
    offset_s: float | None = Field(default=None, ge=0, le=86400)
    track_id: int | None = Field(default=None, ge=0, le=2**31 - 1)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class RetractIn(_In):
    reason: str = Field(min_length=3, max_length=500)


class NoteRevisionOut(BaseModel):
    revision: int
    author: str
    created_at: datetime
    body: str
    tags: list[str]
    evidence_id: uuid.UUID | None
    offset_s: float | None
    track_id: int | None
    bbox: list[float] | None = None


class NoteOut(BaseModel):
    id: uuid.UUID
    kind: NoteKindName
    author: str
    author_is_me: bool
    created_at: datetime
    updated_at: datetime
    revision: int
    body: str
    tags: list[str]
    evidence_id: uuid.UUID | None
    offset_s: float | None
    track_id: int | None
    bbox: list[float] | None = None
    retracted_at: datetime | None
    retracted_by: str | None
    retract_reason: str | None
    can_revise: bool
    can_retract: bool


# --------------------------------------------------------------------------- bookmarks


class BookmarkIn(_In):
    evidence_id: uuid.UUID
    offset_s: float = Field(ge=0, le=86400)
    label: str = Field(min_length=1, max_length=120)


class BookmarkOut(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    offset_s: float
    label: str
    author: str
    created_at: datetime
    can_remove: bool


# --------------------------------------------------------------------------- dossier


class EvidenceItem(BaseModel):
    id: uuid.UUID
    kind: str
    content_type: str
    redaction: str
    redaction_label: str
    original_exists: bool  # a separate unredacted original was stored
    size_bytes: int
    sha256_recorded: bool  # SHA-256 of the stored original, taken at ingestion
    storage_state: StorageState
    purged_at: datetime | None
    duration_s: float | None
    media_url: str | None  # signed, short-lived, redacted variant; None unless available


class DecisionOut(BaseModel):
    status: str
    action: str | None
    action_label: str | None
    note: str | None
    decided_by: str | None
    decided_at: datetime | None
    external_effect: str  # always states that nothing was dispatched/issued externally


class Provenance(BaseModel):
    source_kind: Literal["live", "recorded_replay", "unknown"]
    source_basis: str
    model_id: str | None
    model_hash: str | None
    model_status: Literal["recorded", "not_recorded"]
    speed_kmh: float | None
    speed_status: Literal["uncalibrated_estimate", "not_applicable"]
    recorded_details: dict[str, Any]


class CasePermissions(BaseModel):
    can_decide: bool
    can_annotate: bool
    can_request_export: bool
    can_approve_export: bool


class CaseDossier(BaseModel):
    number: int
    status: str
    priority: str
    type: str
    type_label: str
    camera_id: str
    camera_name: str
    location: str
    timezone: str
    observed_at: datetime  # UTC, with offset
    observed_at_local: str  # ISO 8601 with the camera zone's offset
    first_observed_at: datetime
    last_observed_at: datetime | None  # not recorded by the pipeline -> null
    observation_note: str
    video_t_s: float | None
    track_id: int | None
    object_class: str | None
    rule: str
    provenance: Provenance
    evidence: list[EvidenceItem]
    decision: DecisionOut
    notes: list[NoteOut]
    bookmarks: list[BookmarkOut]
    history: list[AuditEntry]
    permissions: CasePermissions
    tag_catalog: dict[str, str]
    # Investigation completion (filled by the API from app.services.casework).
    related: list[cw.RelatedCase] = []
    context: cw.TimelineContext | None = None
    followups: list[cw.FollowupOut] = []
    legal_hold: cw.LegalHoldState | None = None
    detection_ref: cw.DetectionReference | None = None


# --------------------------------------------------------------------------- archive


class ArchiveFilters(_In):
    """Structured archive filters. Also the only thing a saved search stores."""

    camera_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    types: list[str] = Field(default_factory=list, max_length=20)
    statuses: list[Literal["new", "confirmed", "rejected"]] = Field(
        default_factory=list, max_length=3
    )
    priorities: list[Literal["critical", "high", "medium", "info"]] = Field(
        default_factory=list, max_length=4
    )
    date_from: AwareDatetime | None = None
    date_to: AwareDatetime | None = None
    has_evidence: bool | None = None
    # A user id, or "unassigned". Only for roles that may see assignments (alerts:assign).
    assigned_to: str | None = Field(
        default=None,
        pattern=r"^(unassigned|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$",
    )
    # Cases with at least one (not purged) item of these kinds; camera_video = the case's camera
    # has an annotated recording stored.
    evidence_types: list[Literal["keyframe", "clip", "camera_video"]] = Field(
        default_factory=list, max_length=3
    )
    # Applied by the server so totals and keyset pages stay exact; not stored in saved searches.
    exclude_types: list[str] = Field(default_factory=list, max_length=20)
    exclude_numbers: list[int] = Field(default_factory=list, max_length=500)


class ArchiveSearchIn(_In):
    q: str | None = Field(default=None, max_length=500)
    filters: ArchiveFilters = Field(default_factory=ArchiveFilters)
    cursor: str | None = Field(default=None, max_length=300)
    limit: int = Field(default=24, ge=1, le=100)


class TokenInterpretation(BaseModel):
    token: str
    status: Literal["recognized", "ignored", "unsupported"]
    meanings: list[str] = []
    ambiguous: bool = False


class FilterChip(BaseModel):
    key: str
    label: str  # Romanian, how the server applied the structured filter


class ArchivePage(BaseModel):
    results: list[Any]  # contract Event objects
    next_cursor: str | None
    total: int  # exact count of the filtered, role-scoped set (computed, not capped)
    sort: str
    filter: dict[str, Any]
    interpretation: list[TokenInterpretation]
    applied_filters: list[FilterChip] = []


class SavedSearchIn(_In):
    name: str = Field(min_length=1, max_length=80)
    filters: ArchiveFilters


class SavedSearchOut(BaseModel):
    id: uuid.UUID
    name: str
    filters: dict[str, Any]
    created_at: datetime


# --------------------------------------------------------------------------- exports


class ExportIn(_In):
    include_original: bool = False
    justification: str = Field(min_length=10, max_length=2000)
    case_reference: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(pattern=IDEMPOTENCY_KEY)


class ExportOut(BaseModel):
    id: uuid.UUID
    event_id: int
    state: str
    include_original: bool
    requester: str
    requested_by_me: bool
    created_at: datetime
    approval_id: uuid.UUID | None
    approval_status: str | None
    approved_by: str | None
    attempt: int
    error: str | None
    completed_at: datetime | None
    expires_at: datetime | None
    manifest_sha256: str | None
    package_sha256: str | None
    package_size: int | None
    file_count: int | None
    signature: Literal["none"] = "none"
    legal_hold: bool = False  # the case is held: the package is kept past its window
    storage_retries: int = 0


class ExportLinkOut(BaseModel):
    url: str
    expires_at: datetime
