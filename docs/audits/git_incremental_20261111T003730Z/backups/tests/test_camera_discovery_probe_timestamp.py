"""The discovery catalog accepts date-only and RFC3339 probe values (no PostgreSQL needed)."""

import json
from pathlib import Path

import pytest
from app.services.camera_discovery import REGISTRY, CameraDiscoveryEntry
from pydantic import ValidationError


def _candidate() -> dict:
    document = json.loads(Path(REGISTRY).read_text(encoding="utf-8"))
    return document["sources"][0]


@pytest.mark.parametrize("value", ["2026-11-07", "2026-11-07T22:09:29Z", None])
def test_last_probe_accepts_iso_dates_and_timestamps(value: str | None) -> None:
    candidate = _candidate()
    candidate["last_probe"] = value
    assert CameraDiscoveryEntry.model_validate(candidate).last_probe == value


def test_last_probe_rejects_non_iso_timestamp() -> None:
    candidate = _candidate()
    candidate["last_probe"] = "yesterday-ish"
    with pytest.raises(ValidationError):
        CameraDiscoveryEntry.model_validate(candidate)

