"""Request/response shapes of the camera control plane (``/api/camera-control``) and of the
worker handshake (``/api/ingest/cameras/{slug}/config``, ``.../config/ack``, ``.../heartbeat``).

No response model has a field that could carry the source URL or its credentials: only the
host-level ``source_display`` exists."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceKind = Literal["recorded_replay", "owned_optical_live", "authorized_network_live"]
Lifecycle = Literal["legacy", "discovered", "onboarding", "approved", "disabled"]
EPOCH = r"^[A-Za-z0-9_-]{8,64}$"
Reason = Field(min_length=3, max_length=500)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- requests


class RevisionedAction(Strict):
    expected_revision: int = Field(ge=0)
    reason: str = Reason


class LifecycleIn(RevisionedAction):
    to: Literal["onboarding"]


class CameraPatch(Strict):
    expected_revision: int = Field(ge=0)
    reason: str = Reason
    name: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, min_length=2, max_length=300)
    timezone: str | None = Field(default=None, max_length=64)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SourceIn(Strict):
    expected_revision: int = Field(ge=0)
    reason: str = Reason
    kind: SourceKind
    # Never echoed back, logged or audited; validated by camera_control.parse_source.
    url: str = Field(min_length=3, max_length=2048)


class GrantIn(Strict):
    granting_party: str = Field(min_length=2, max_length=200)
    basis: Literal["written_agreement", "licence", "own_infrastructure", "statutory_mandate"]
    basis_reference: str = Field(min_length=2, max_length=200)
    purpose: str = Field(min_length=3, max_length=500)
    valid_from: datetime
    valid_until: datetime
    capture_method: SourceKind
    max_analysis_fps: float = Field(gt=0, le=60)
    max_frame_height: int = Field(gt=0, le=8192)
    retention_days: int = Field(gt=0, le=3650)
    export_allowed: bool = False
    media_scope: Literal["events_only", "events_and_recordings"] = "events_only"

    @field_validator("valid_from", "valid_until")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("must include a UTC offset")
        return v


class RevokeIn(Strict):
    reason: str = Reason


class DraftIn(Strict):
    config: dict[str, Any]
    reason: str = Reason


class ValidateIn(Strict):
    config: dict[str, Any]


class DecisionIn(Strict):
    note: str | None = Field(default=None, max_length=500)


class SubmitIn(Strict):
    reason: str | None = Field(default=None, max_length=500)


class ActivateIn(Strict):
    version_id: uuid.UUID
    expected_revision: int = Field(ge=0)
    reason: str = Reason


# --------------------------------------------------------------------------- responses


class ConfigErrorOut(BaseModel):
    path: str
    code: str
    message: str


class ValidationOut(BaseModel):
    valid: bool
    errors: list[ConfigErrorOut]
    fingerprint: str | None = None
    min_fps: float | None = None


class UnmetOut(BaseModel):
    code: str
    message: str


class EligibilityOut(BaseModel):
    eligible: bool
    unmet: list[UnmetOut]
    version_id: uuid.UUID | None
    evaluated_at: datetime


class GrantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    granting_party: str
    basis: str
    basis_reference: str
    purpose: str
    valid_from: datetime
    valid_until: datetime
    capture_method: str
    max_analysis_fps: float
    max_frame_height: int
    retention_days: int
    export_allowed: bool
    media_scope: str
    reviewed_by: uuid.UUID
    status: str
    revoked_at: datetime | None
    revocation_reason: str | None
    created_at: datetime


class VersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    revision: int
    schema_version: int
    fingerprint: str
    status: str
    reason: str
    validation_errors: list[ConfigErrorOut]
    created_by: uuid.UUID
    created_at: datetime
    validated_at: datetime | None
    submitted_by: uuid.UUID | None
    submitted_at: datetime | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    decision_note: str | None
    activated_by: uuid.UUID | None
    activated_at: datetime | None
    activation_reason: str | None
    superseded_at: datetime | None


class VersionOut(VersionSummary):
    config: dict[str, Any]


class DiffOut(BaseModel):
    from_version_id: uuid.UUID | None
    from_revision: int | None
    to_version_id: uuid.UUID
    to_revision: int
    changes: list[dict[str, Any]]


class WorkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lease_epoch: str | None
    lease_expires_at: datetime | None
    seq: int
    last_heartbeat_at: datetime | None
    health: str | None
    applied_revision: int | None
    applied_fingerprint: str | None
    applied_at: datetime | None
    last_ack_status: str | None
    last_ack_revision: int | None
    last_ack_reason: str | None
    last_ack_at: datetime | None
    source_fps: float | None
    processing_fps: float | None
    last_frame_at: datetime | None
    dropped_frames: int | None
    queue_depth: int | None
    retries: int | None
    model_id: str | None
    frame_width: int | None
    frame_height: int | None
    last_error_code: str | None
    last_error: str | None
    conflict_epoch: str | None
    conflict_at: datetime | None
    inference_p50_ms: float | None
    inference_p95_ms: float | None
    rss_mb: float | None
    frozen_signal: float | None
    frozen_confidence: float | None
    unchanged_s: float | None


class RuntimeOut(BaseModel):
    state: str
    is_live: bool
    freshness: str
    heartbeat_age_s: float | None
    stale_after_s: float
    offline_after_s: float
    runnable: bool
    blocked_reason: str | None
    unmet: list[UnmetOut]
    desired_revision: int | None
    desired_fingerprint: str | None
    applied_revision: int | None
    applied_fingerprint: str | None
    revision_in_sync: bool
    reference_frame_mismatch: bool | None
    duplicate_worker: bool
    # match | mismatch | unreported (no current worker attests) | unknown (no registered
    # fingerprint: source set before migration 0009). The fingerprints themselves are not returned.
    source_attestation: Literal["match", "mismatch", "unreported", "unknown"]
    server_time: datetime


class ControlSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    location: str
    timezone: str
    lifecycle_state: str
    source_kind: str | None
    source_display: str | None
    source_has_credentials: bool
    desired_enabled: bool
    revision: int
    active_version_id: uuid.UUID | None
    disabled_reason: str | None
    enable_requested_by: uuid.UUID | None
    enable_requested_at: datetime | None
    runtime: RuntimeOut


class ControlDetail(ControlSummary):
    worker: WorkerOut | None
    grants: list[GrantOut]
    eligibility: EligibilityOut
    unsupported_actions: dict[str, str]


class HealthEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    kind: str
    worker_epoch: str | None
    health: str | None
    revision: int | None
    reason_code: str | None
    message: str | None


class ActivationOut(BaseModel):
    changed: bool
    camera: ControlSummary
    version: VersionSummary
    previous_version_id: uuid.UUID | None


# --------------------------------------------------------------------------- worker


HealthState = Literal[
    "starting",
    "healthy",
    "reconnecting",
    "source_failed",
    "decoder_failed",
    "model_unavailable",
    "config_rejected",
    "auth_failed",
    "permission_blocked",
    "stopped",
    "frozen_image",
]


# Bounded, finite numbers only (NaN/inf refused).
def _metric(hi: float) -> Any:
    return Field(default=None, ge=0, le=hi, allow_inf_nan=False)


class HeartbeatIn(Strict):
    """Optional heartbeat body. An empty body keeps the original (pre-0007) behaviour."""

    worker_epoch: str = Field(pattern=EPOCH)
    seq: int = Field(ge=0, le=2**62)
    applied_revision: int | None = Field(default=None, ge=1)
    health: HealthState = "healthy"
    source_fps: float | None = Field(default=None, ge=0, le=1000)
    processing_fps: float | None = Field(default=None, ge=0, le=1000)
    last_frame_at: datetime | None = None
    dropped_frames: int | None = Field(default=None, ge=0, le=2**62)
    queue_depth: int | None = Field(default=None, ge=0, le=1_000_000)
    retries: int | None = Field(default=None, ge=0, le=1_000_000)
    model_id: str | None = Field(default=None, max_length=120, pattern=r"^[A-Za-z0-9._/-]+$")
    frame_width: int | None = Field(default=None, ge=1, le=16384)
    frame_height: int | None = Field(default=None, ge=1, le=16384)
    error_code: str | None = Field(default=None, max_length=40, pattern=r"^[a-z0-9_:.-]+$")
    error_message: str | None = Field(default=None, max_length=1000)
    # 0009 runtime metrics (all optional; older workers omit them).
    inference_p50_ms: float | None = _metric(600_000)
    inference_p95_ms: float | None = _metric(600_000)
    rss_mb: float | None = _metric(1_048_576)
    frozen_signal: float | None = _metric(255)
    frozen_confidence: float | None = _metric(1)
    unchanged_s: float | None = _metric(31_536_000)
    source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _ordered_percentiles(self) -> HeartbeatIn:
        p50, p95 = self.inference_p50_ms, self.inference_p95_ms
        if p50 is not None and p95 is not None and p95 < p50:
            raise ValueError("inference_p95_ms must be >= inference_p50_ms")
        return self

    @field_validator("last_frame_at")
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("must include a UTC offset")
        return v


class HeartbeatOut(BaseModel):
    lease: Literal["holder", "standby"]
    directive: Literal["run", "stop"]
    reason: str | None
    desired_revision: int | None
    desired_fingerprint: str | None
    camera_revision: int
    unmet: list[str]


class AckIn(Strict):
    worker_epoch: str = Field(pattern=EPOCH)
    revision: int = Field(ge=1)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["accepted", "rejected"]
    reason_code: str | None = Field(default=None, max_length=48, pattern=r"^[a-z0-9_:.-]+$")
    message: str | None = Field(default=None, max_length=1000)


class AckOut(BaseModel):
    applied_revision: int | None
    last_ack_status: str | None
    last_ack_revision: int | None


class DesiredConfigOut(BaseModel):
    source_fingerprint: str | None = None
    camera_id: str
    managed: bool
    run: bool
    reason: str | None
    unmet: list[str]
    camera_revision: int
    source_kind: str | None
    revision: int | None
    fingerprint: str | None
    config: dict[str, Any] | None
