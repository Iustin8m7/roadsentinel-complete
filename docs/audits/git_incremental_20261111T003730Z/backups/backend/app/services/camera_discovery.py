"""Read-only Romanian public presentation catalog with independent ingestion policy."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

REGISTRY = Path(__file__).resolve().parents[3] / "cameras" / "romanian-source-registry.json"


class CameraDiscoveryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)

    id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    road: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=120)
    source_page: AnyHttpUrl
    listing: str = Field(max_length=500)
    reason: str = Field(max_length=500)
    status: Literal["unverified", "offline", "replay-only"]
    transport: Literal["hls", "browser_embed", "timelapse", "directory", "unknown"]
    adapter: str = Field(min_length=1, max_length=80)
    source_config_ref: str | None = Field(default=None, max_length=160)
    camera_or_directory: Literal["camera", "directory"]
    live_status: Literal["unknown", "publisher_offline", "timelapse"]
    actual_vehicle_visibility: Literal["unverified", "yes", "no"]
    last_metadata_reviewed_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    processing_authorization: Literal["not-established", "authorized"]
    ingestion_enabled: bool
    detector_profile: str | None = Field(default=None, max_length=100)
    geometry: str = Field(max_length=100)
    counting_lines: list[dict] = Field(max_length=8)
    zones: list[dict] = Field(max_length=16)
    title: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    roadway: str = Field(min_length=1, max_length=200)
    owner_provider: str = Field(min_length=1, max_length=120)
    canonical_page_url: AnyHttpUrl
    can_view: bool
    can_embed: bool | None
    can_analyze: bool
    can_record: bool
    can_export: bool
    viewing_result: Literal[
        "provider_page_only",
        "hls_manifest_only",
        "publisher_offline",
        "timelapse_page",
        "directory_page",
    ]
    endpoint_state: Literal[
        "not_probed",
        "master_manifest_reachable",
        "snapshot_image_reachable",
        "publisher_offline",
        "unavailable",
    ]
    last_probe: str | None = Field(default=None, max_length=40)
    verified_frames: int = Field(ge=0)
    source_label: str = Field(min_length=1, max_length=80)
    concrete_blocker: str = Field(max_length=500)
    # Presentation is independent of analytics/ingestion policy. These fields describe
    # only a publisher-supported way to show or open the public source.
    player_kind: Literal[
        "official_iframe",
        "official_hosted_player",
        "supported_hls",
        "snapshot",
        "unavailable",
        "external_link",
    ] = "external_link"
    player_url: AnyHttpUrl | None = None
    source_kind: Literal[
        "continuous_live", "refreshed_snapshot", "recorded_timelapse", "unknown"
    ] = "unknown"
    embedding_policy: Literal["supported", "unsupported", "unknown", "not_applicable"] = "unknown"
    presentation_result: Literal["documented", "unavailable", "unknown"] = "unknown"
    presentation_failure_reason: str = Field(default="", max_length=500)

    @field_validator("source_page")
    @classmethod
    def require_https_source_page(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("candidate source page must use HTTPS")
        return value

    @field_validator("last_probe")
    @classmethod
    def validate_last_probe(cls, value: str | None) -> str | None:
        """Accept the registry's date-only and RFC3339 probe timestamps without rewriting them."""
        if value is None:
            return None
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("last_probe must be an ISO date or datetime") from exc
        return value


@lru_cache(maxsize=1)
def load_camera_discovery() -> tuple[CameraDiscoveryEntry, ...]:
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("sources"), list):
        raise ValueError("unsupported Romanian camera registry schema")
    entries = tuple(CameraDiscoveryEntry.model_validate(row) for row in document["sources"])
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Romanian camera registry contains duplicate stable IDs")
    for entry in entries:
        if (entry.title, entry.roadway, entry.owner_provider, str(entry.canonical_page_url)) != (
            entry.name, entry.road, entry.source, str(entry.source_page)
        ):
            raise ValueError(f"presentation descriptor conflicts with catalog identity: {entry.id}")
        if entry.ingestion_enabled:
            raise ValueError(f"catalog candidate must remain disabled: {entry.id}")
        if entry.can_analyze or entry.can_record or entry.can_export:
            raise ValueError(
                f"catalog candidate claims unestablished processing permissions: {entry.id}"
            )
        if entry.camera_or_directory == "directory" and entry.transport != "directory":
            raise ValueError(f"directory record has camera transport: {entry.id}")
        supported = {
            "supported_hls",
            "official_iframe",
            "official_hosted_player",
            "snapshot",
        }
        if entry.player_url and entry.player_kind not in supported:
            raise ValueError(f"player URL conflicts with presentation kind: {entry.id}")
    return entries
