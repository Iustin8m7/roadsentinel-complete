from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecordingRights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_name: str = Field(min_length=3, max_length=200)
    rightsholder: str = Field(min_length=3, max_length=200)
    permission_basis: Literal["owned", "licensed", "written_permission", "public_domain"]
    authorization_reference: str = Field(min_length=5, max_length=300)
    scope: str = Field(min_length=10, max_length=500)
    allow_analysis: bool
    allow_evidence_extraction: bool
    allow_retention: bool
    expires_at: datetime | None = None
    operator_declaration: bool

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Expiration requires a timezone offset")
        return value

    @model_validator(mode="after")
    def permitted(self):
        if not (self.allow_analysis and self.allow_evidence_extraction and self.allow_retention and self.operator_declaration):
            raise ValueError("Analysis, evidence extraction, retention and operator declaration are required")
        if self.expires_at is not None and self.expires_at <= datetime.now(UTC):
            raise ValueError("Source authorization has expired")
        return self


class RecordingRightsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    rights: RecordingRights


class CropIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    confirmed: bool
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def bounds(self):
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("crop rectangle must remain inside the source frame")
        if self.width * self.height < 0.002:
            raise ValueError("crop must retain at least 0.2% of the source frame")
        return self


class LinePoint(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_fps: float = Field(default=1, ge=0.5, le=5)
    confidence: float = Field(default=0.3, ge=0.05, le=0.95)
    counting_line: tuple[LinePoint, LinePoint] | None = None
    stationary_duration_s: int = Field(default=120, ge=30, le=1800)
    stationary_enabled: bool = True
    queue_enabled: bool = True
    queue_min_vehicles: int = Field(default=5, ge=3, le=30)
    queue_duration_s: int = Field(default=60, ge=20, le=900)
    output_mode: str = Field(default="sampled_timeline", pattern="^sampled_timeline$")
    crop_revision: int = Field(ge=1)

    @model_validator(mode="after")
    def line_must_have_extent(self):
        if self.counting_line:
            a, b = self.counting_line
            if abs(a.x - b.x) + abs(a.y - b.y) < 0.02:
                raise ValueError("counting line endpoints must be distinct")
        return self


class RecordingOut(BaseModel):
    id: UUID
    original_filename: str
    sha256: str
    size_bytes: int
    codec: str
    duration_ms: int
    width: int
    height: int
    fps_num: int
    fps_den: int
    source_kind: str = "RECORDED SCREENCAST"
    imported_at: datetime
    provenance_note: str
    status: str
    crop: dict[str, Any] | None
    crop_revision: int
    rights_context: dict[str, Any] | None = None
    rights_revision: int = 0


class AnalysisOut(BaseModel):
    id: UUID
    recording_id: UUID
    status: str
    configuration: dict[str, Any]
    model_id: str
    model_sha256: str
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    processed_frames: int
    decoded_frames: int
    skipped_frames: int
    total_estimated_frames: int
    latest_media_pts_ms: int
    progress: float
    inference_fps: float
    counts: dict[str, Any]
    warnings: list[str]
    error_code: str | None
    output_size_bytes: int | None
    output_duration_ms: int | None
    output_fps: float | None
    has_output: bool
    preview_sequence: int
    has_analytics: bool = False
    observation_count: int = 0
    observation_schema_version: int | None = None


class AnalyticsSummary(BaseModel):
    analysis_run_id: UUID
    source_video_id: UUID
    status: str
    partial: bool
    source_width: int
    source_height: int
    source_duration_s: float
    crop: dict[str, Any]
    sample_fps: float
    inference_fps: float
    processed_samples: int
    sampled_span_s: list[float] | None
    sample_coverage_seconds: float
    sample_coverage_ratio: float
    model_name: str
    model_sha256: str
    confidence: float
    observation_totals_by_class: dict[str, int]
    estimated_tracker_id_totals_by_class: dict[str, int]
    line_crossings: dict[str, int] | None
    available_metrics: list[str]
    warnings: list[str]
    artifact_version: int


class HeatmapResponse(BaseModel):
    mode: str
    grid_width: int
    grid_height: int
    values: list[float]
    min_value: float
    max_value: float
    total_weight: float
    normalization: str
    coordinate_reference: str
    image_width: int
    image_height: int
    crop: dict[str, Any]
    filter_start_s: float
    filter_end_s: float
    included_classes: list[str]
    included_observations: int
    processed_samples: int
    partial: bool
    missing_data: bool
    observation_totals_by_class: dict[str, int]
    warnings: list[str]
    algorithm_version: int


class TimelineBin(BaseModel):
    start_s: float
    end_s: float
    observations_by_class: dict[str, int]
    vehicle_seconds_by_class: dict[str, float]
    sampled_frames: int
    coverage_flag: str


class TimelineResponse(BaseModel):
    source_duration_s: float
    filter_start_s: float
    filter_end_s: float
    bin_seconds: float
    included_classes: list[str]
    bins: list[TimelineBin]
    partial: bool
    warnings: list[str]
    algorithm_version: int


class OfflineCandidateProvenance(BaseModel):
    origin: Literal["offline_recording"] = "offline_recording"
    review_state: Literal["pending_review"] = "pending_review"
    tenant_id: UUID
    source_video_id: UUID
    analysis_run_id: UUID
    source_pts_ms: int = Field(ge=0)
    end_pts_ms: int | None = Field(default=None, ge=0)
    rule_id: str
    rule_version: str
    threshold_evidence: dict[str, Any]
    track_id: int | None = None
    class_ref: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ref: str | None = None
    label: str
    limitations: str

class OfflineCandidateResponse(BaseModel):
    source_video_id: UUID
    analysis_run_id: UUID
    tenant_id: UUID
    candidates: list[OfflineCandidateProvenance]
    flow_analytics: list[dict[str, Any]]
    note: str = "Recorded-source observations require human review; they are not live enforcement incidents."
