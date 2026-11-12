from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api import offline_analytics
from fastapi import HTTPException


def _artifact(tenant_id: uuid.UUID, video_id: uuid.UUID, run_id: uuid.UUID) -> bytes:
    manifest = {
        "record_type": "manifest",
        "schema_version": 1,
        "source_video_id": str(video_id),
        "analysis_run_id": str(run_id),
        "tenant_id": str(tenant_id),
        "source_width": 1050,
        "source_height": 589,
        "coordinate_reference": "normalized_full_source_frame",
        "crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8, "confirmed": True},
    }
    sample = {
        "record_type": "sample",
        "schema_version": 1,
        "source_video_id": str(video_id),
        "analysis_run_id": str(run_id),
        "tenant_id": str(tenant_id),
        "source_frame_index": 30,
        "sample_sequence": 1,
        "pts_seconds": 1.0,
        "observations": [
            {
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.9,
                "bbox_normalized": [0.3, 0.3, 0.4, 0.5],
                "anchor_normalized": [0.35, 0.5],
                "track_id": 7,
            }
        ],
    }
    return (
        json.dumps(manifest, separators=(",", ":"))
        + "\n"
        + json.dumps(sample, separators=(",", ":"))
        + "\n"
    ).encode()


def test_protected_artifact_is_scope_checked_and_streamed_as_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id, video_id, run_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    payload = _artifact(tenant_id, video_id, run_id)
    path = tmp_path / "observations.jsonl"
    path.write_bytes(payload)
    monkeypatch.setattr(
        offline_analytics,
        "decrypted_temp",
        lambda *_: _temporary(path),
    )
    principal = SimpleNamespace(tenant_id=tenant_id, keyring=object())
    recording = SimpleNamespace(id=video_id, width=1050, height=589, duration_ms=20_000)
    run = SimpleNamespace(
        id=run_id,
        observation_size_bytes=len(payload),
        observation_sha256=hashlib.sha256(payload).hexdigest(),
        observation_schema_version=1,
        observation_storage_key="offline-analysis/generated/observations.rse",
        configuration={"crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8, "confirmed": True}},
        observation_count=1,
        processed_frames=1,
    )
    with offline_analytics._frames(principal, recording, run) as (manifest, rows):
        values = list(rows)
    assert manifest["coordinate_reference"] == "normalized_full_source_frame"
    assert values[0]["observations"][0]["track_id"] == 7


@contextmanager
def _temporary(path: Path):
    yield path


def test_artifact_digest_and_row_scope_are_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id, video_id, run_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    payload = _artifact(tenant_id, video_id, run_id)
    path = tmp_path / "observations.jsonl"
    path.write_bytes(payload)
    monkeypatch.setattr(offline_analytics, "decrypted_temp", lambda *_: _temporary(path))
    principal = SimpleNamespace(tenant_id=tenant_id, keyring=object())
    recording = SimpleNamespace(id=video_id, width=1050, height=589, duration_ms=20_000)
    run = SimpleNamespace(
        id=run_id,
        observation_size_bytes=len(payload),
        observation_sha256="0" * 64,
        observation_schema_version=1,
        observation_storage_key="offline-analysis/generated/observations.rse",
        configuration={"crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8, "confirmed": True}},
        observation_count=1,
        processed_frames=1,
    )
    with pytest.raises(HTTPException, match="integrity"), offline_analytics._frames(principal, recording, run):
        pass


def test_artifact_rows_cannot_cross_tenant_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id, video_id, run_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    lines = _artifact(tenant_id, video_id, run_id).decode().splitlines()
    sample = json.loads(lines[1])
    sample["tenant_id"] = str(uuid.uuid4())
    lines[1] = json.dumps(sample, separators=(",", ":"))
    payload = ("\n".join(lines) + "\n").encode()
    path = tmp_path / "observations.jsonl"
    path.write_bytes(payload)
    monkeypatch.setattr(offline_analytics, "decrypted_temp", lambda *_: _temporary(path))
    principal = SimpleNamespace(tenant_id=tenant_id, keyring=object())
    recording = SimpleNamespace(id=video_id, width=1050, height=589, duration_ms=20_000)
    run = SimpleNamespace(
        id=run_id,
        observation_size_bytes=len(payload),
        observation_sha256=hashlib.sha256(payload).hexdigest(),
        observation_schema_version=1,
        observation_storage_key="offline-analysis/generated/observations.rse",
        configuration={
            "crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8, "confirmed": True}
        },
        observation_count=1,
        processed_frames=1,
    )
    with offline_analytics._frames(principal, recording, run) as (_, rows), pytest.raises(
        HTTPException, match="invalid row"
    ):
        list(rows)
