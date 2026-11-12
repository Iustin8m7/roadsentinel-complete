"""WGS84 location attribution and bounded, private POST map queries."""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def non_sentinel(self):
        if self.latitude == self.longitude == 0:
            raise ValueError("0,0 is not a location placeholder")
        return self


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    expected_revision: int = Field(ge=0)
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    point: GeoPoint | None = None
    accuracy_m: float | None = Field(default=None, ge=1, le=1_000_000)
    explanation: str = Field(min_length=10, max_length=500)
    source_reference: str = Field(min_length=3, max_length=300)
    city_label: str | None = Field(default=None, max_length=100)
    motion: Literal["fixed", "moving", "composite", "unknown"] = "fixed"
    state: Literal["confirmed", "pending", "unknown"] = "confirmed"
    anchor_kind: Literal["source_anchor", "event_position"] = "source_anchor"
    source_location_id: uuid.UUID | None = None
    camera_valid_at_capture: bool = False
    confirmed: bool = False
    captured_at: datetime | None = None
    is_demo: bool = False

    @field_validator("captured_at")
    @classmethod
    def aware(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("captured_at requires an explicit UTC offset")
        return value

    @model_validator(mode="after")
    def confirmation(self):
        if self.state == "confirmed":
            if not self.confirmed or self.motion != "fixed":
                raise ValueError("Only explicitly confirmed fixed-view locations may be placed")
            if self.source_location_id is None and (self.point is None or self.accuracy_m is None):
                raise ValueError(
                    "Confirmed location needs point and accuracy or an approved camera revision"
                )
        if self.state == "unknown" and (self.point is not None or self.source_location_id):
            raise ValueError("Unknown location must have NULL coordinates")
        return self


class LocationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=10, max_length=500)


class MapQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    bbox: tuple[float, float, float, float] | None = None  # west,south,east,north
    date_from: datetime | None = None
    date_to: datetime | None = None
    types: list[str] = Field(default_factory=list, max_length=20)
    statuses: list[Literal["new", "confirmed", "rejected"]] = Field(
        default_factory=lambda: ["new", "confirmed"], max_length=3
    )
    severities: list[Literal["critical", "high", "medium", "info"]] = Field(
        default_factory=list, max_length=4
    )
    source_kind: Literal["recorded_upload", "live_camera", "local_replay", "unknown"] | None = None
    camera_id: uuid.UUID | None = None
    recording_id: uuid.UUID | None = None
    county_code: str | None = Field(default=None, max_length=12)
    city_label: str | None = Field(default=None, max_length=100)
    location_state: Literal["located", "unknown", "outside", "all"] = "all"
    location_source: Literal["manual_map_pin", "registered_camera", "unknown"] | None = None
    include_demo: bool = False
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1000)
    zoom: int = Field(default=6, ge=3, le=19)

    @model_validator(mode="after")
    def bounds(self):
        if self.bbox:
            w, s, e, n = self.bbox
            if (
                not all(math.isfinite(v) for v in self.bbox)
                or not (-180 <= w < e <= 180 and -90 <= s < n <= 90)
                or e - w > 30
                or n - s > 20
            ):
                raise ValueError("bbox must be ordered W,S,E,N with extent <=30×20 degrees")
        for value in (self.date_from, self.date_to):
            if value is not None and value.utcoffset() is None:
                raise ValueError("Dates require explicit timezone")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("Time interval is reversed")
        return self


class MapIncidentSummary(BaseModel):
    id: uuid.UUID
    number: int
    incident_type: str
    severity: str
    status: str
    detected_at: datetime
    occurred_at: datetime | None
    timestamp_basis: str
    video_t: float | None
    source: dict
    location: dict | None
    location_reason: str | None
    is_demo: bool
    can_view_evidence: bool
    can_open_recording: bool
    evidence_state: str
    detail_href: str


class MapPage(BaseModel):
    items: list[MapIncidentSummary]
    clusters: list[dict]
    counts: dict[str, int]
    next_cursor: str | None
    count_scope: str
    time_filter_basis: str
    generated_at: datetime
    refresh_after_seconds: int


class CameraGeoInput(GeoPoint):
    accuracy_m: float = Field(ge=1, le=1_000_000)
    explanation: str = Field(min_length=10, max_length=500)
    source_reference: str = Field(min_length=3, max_length=300)
    city_label: str | None = Field(default=None, max_length=100)
    is_demo: bool = False
