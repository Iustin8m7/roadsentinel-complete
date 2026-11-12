from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as ApiPath
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from roadsentinel.detector import COCO, YoloXOnnx
from roadsentinel.redaction import redact_frame, redaction_mode
from sqlalchemy import select

from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, require
from app.models import AnalysisRun, Recording
from app.schemas.offline_video import (
    AnalyticsSummary,
    HeatmapResponse,
    OfflineCandidateProvenance,
    OfflineCandidateResponse,
    TimelineResponse,
)
from app.services.offline_heatmap import (
    MAX_ARTIFACT_BYTES,
    VEHICLE_CLASSES,
    heatmap,
    timeline,
    validate_frame_record,
    weighted_frames,
)
from app.services.offline_video_storage import decrypted_temp

router = APIRouter(tags=["offline-video-analytics"])
MAX_RECORD_BYTES = 1024 * 1024
MODEL_PATH = Path(
    os.environ.get(
        "RS_YOLOX_MODEL_PATH", str(Path(__file__).resolve().parents[3] / "models" / "yolox_s.onnx")
    )
)
_frame_detector: YoloXOnnx | None = None
_frame_detector_lock = threading.Lock()
_analytics_slots = threading.BoundedSemaphore(2)


@contextmanager
def _analytics_slot():
    if not _analytics_slots.acquire(blocking=False):
        raise HTTPException(429, "Two analytics calculations are already running; retry shortly")
    try:
        yield
    finally:
        _analytics_slots.release()


def _scoped_run(
    principal: Principal, recording_id: UUID, run_id: UUID
) -> tuple[Recording, AnalysisRun]:
    recording = principal.db.scalar(
        select(Recording).where(
            Recording.id == recording_id, Recording.tenant_id == principal.tenant_id
        )
    )
    run = principal.db.scalar(
        select(AnalysisRun).where(
            AnalysisRun.id == run_id,
            AnalysisRun.recording_id == recording_id,
            AnalysisRun.tenant_id == principal.tenant_id,
        )
    )
    if not recording or not run:
        raise HTTPException(404, "Analysis not found")
    if run.status != "completed":
        raise HTTPException(409, "Analytics are available only after a completed recorded analysis")
    if not run.observations_complete or not run.observation_storage_key:
        raise HTTPException(
            409, "Analytics are unavailable for this run; reanalyze to create trace data"
        )
    return recording, run


@contextmanager
def _frames(principal: Principal, recording: Recording, run: AnalysisRun):
    """Decrypt and validate an immutable completed artifact before any aggregate is returned."""
    if (
        not run.observation_size_bytes
        or run.observation_size_bytes > MAX_ARTIFACT_BYTES
        or not run.observation_sha256
        or run.observation_schema_version != 1
    ):
        raise HTTPException(422, "The analytics artifact metadata is invalid")
    with decrypted_temp(principal.keyring, run.id, run.observation_storage_key) as path:
        if path.stat().st_size != run.observation_size_bytes:
            raise HTTPException(422, "The analytics artifact size does not match its manifest")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != run.observation_sha256:
            raise HTTPException(422, "The analytics artifact integrity check failed")

        handle = path.open("r", encoding="utf-8")
        try:
            raw_manifest = handle.readline(MAX_RECORD_BYTES + 1)
            if len(raw_manifest) > MAX_RECORD_BYTES:
                raise HTTPException(422, "The analytics manifest is too large")
            manifest = json.loads(raw_manifest)
            if not isinstance(manifest, dict):
                raise HTTPException(422, "The analytics manifest is malformed")
            expected = {
                "record_type": "manifest",
                "schema_version": 1,
                "source_video_id": str(recording.id),
                "analysis_run_id": str(run.id),
                "tenant_id": str(principal.tenant_id),
                "source_width": recording.width,
                "source_height": recording.height,
            }
            if any(manifest.get(key) != value for key, value in expected.items()):
                raise HTTPException(422, "The analytics manifest does not match this run")
            config_crop = run.configuration.get("crop")
            if manifest.get("crop") != config_crop:
                raise HTTPException(422, "The analytics crop does not match the run configuration")

            def records():
                previous_sequence = 0
                previous_pts = -1.0
                observations_read = 0
                frames_read = 0
                while True:
                    line = handle.readline(MAX_RECORD_BYTES + 1)
                    if not line:
                        break
                    if len(line) > MAX_RECORD_BYTES:
                        raise HTTPException(422, "An analytics sample row is too large")
                    try:
                        item = json.loads(line)
                        if not isinstance(item, dict):
                            raise ValueError("invalid_record")
                        if item.get("record_type") != "sample" or item.get("schema_version") != 1:
                            raise ValueError("invalid_record_type")
                        if (
                            item.get("analysis_run_id") != str(run.id)
                            or item.get("source_video_id") != str(recording.id)
                            or item.get("tenant_id") != str(principal.tenant_id)
                        ):
                            raise ValueError("record_scope_mismatch")
                        item = validate_frame_record(item, duration_s=recording.duration_ms / 1000)
                        if item["sample_sequence"] <= previous_sequence:
                            raise ValueError("observation_sequence_not_monotonic")
                        if item["pts_seconds"] < previous_pts:
                            raise ValueError("observation_pts_not_monotonic")
                        previous_sequence = item["sample_sequence"]
                        previous_pts = item["pts_seconds"]
                        observations_read += len(item["observations"])
                        frames_read += 1
                        yield item
                    except (json.JSONDecodeError, ValueError) as exc:
                        raise HTTPException(
                            422, "The analytics artifact contains an invalid row"
                        ) from exc
                if (
                    observations_read != run.observation_count
                    or frames_read != run.processed_frames
                ):
                    raise HTTPException(
                        422, "The analytics artifact counts do not match the database"
                    )

            yield manifest, records()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(422, "The analytics manifest is malformed") from exc
        finally:
            handle.close()


def _class_filter(value: str) -> set[str]:
    classes = {item.strip() for item in value.split(",") if item.strip()}
    if not classes or not classes.issubset(VEHICLE_CLASSES):
        raise HTTPException(422, "Choose one or more supported vehicle classes")
    return classes


def _range(start_s: float, end_s: float | None, recording: Recording) -> tuple[float, float]:
    duration = recording.duration_ms / 1000
    end = duration if end_s is None else end_s
    if not math.isfinite(start_s) or not math.isfinite(end) or not (0 <= start_s < end <= duration):
        raise HTTPException(422, "The source-time interval must be within the recording duration")
    return start_s, end


@router.get(
    "/api/recordings/{recording_id}/analyses/{run_id}/analytics/summary",
    response_model=AnalyticsSummary,
)
def analytics_summary(
    recording_id: UUID,
    run_id: UUID,
    principal: Principal = Depends(require(Permission.videos_read)),
) -> AnalyticsSummary:
    recording, run = _scoped_run(principal, recording_id, run_id)
    observation_totals: dict[str, int] = {}
    tracker_sets: dict[str, set[int]] = {}
    pts_min, pts_max, samples = None, None, 0
    sample_coverage_s = 0.0
    with _analytics_slot(), _frames(principal, recording, run) as (_, frames):
        for frame, coverage_s in weighted_frames(
            frames, sample_fps=float(run.configuration["sample_fps"])
        ):
            samples += 1
            sample_coverage_s += coverage_s
            pts = frame["pts_seconds"]
            pts_min = pts if pts_min is None else min(pts_min, pts)
            pts_max = pts if pts_max is None else max(pts_max, pts)
            for obs in frame["observations"]:
                name = obs["class_name"]
                observation_totals[name] = observation_totals.get(name, 0) + 1
                if obs.get("track_id") is not None:
                    tracker_sets.setdefault(name, set()).add(int(obs["track_id"]))
    principal.audit(
        AuditAction.analysis_analytics_viewed, resource_type="analysis_runs", resource_id=run.id
    )
    crop = run.configuration["crop"]
    warnings = [
        "Detector observation totals are not manually validated unique-vehicle counts.",
        "Tracker ID totals are approximate and may split one vehicle into multiple tracks.",
        "Source PTS is recording position; screencast FPS is not optical camera FPS.",
        "Analytics are available only after a completed run with finalized samples.",
    ]
    if run.counts.get("line_crossing_status") == "not_configured":
        line_crossings = None
    else:
        line_crossings = run.counts.get("line_crossings")
    return AnalyticsSummary(
        analysis_run_id=run.id,
        source_video_id=recording.id,
        status=run.status,
        partial=False,
        source_width=recording.width,
        source_height=recording.height,
        source_duration_s=recording.duration_ms / 1000,
        crop=crop,
        sample_fps=float(run.configuration["sample_fps"]),
        inference_fps=float(run.inference_fps),
        processed_samples=samples,
        sampled_span_s=[pts_min, pts_max] if pts_min is not None else None,
        sample_coverage_seconds=min(recording.duration_ms / 1000, sample_coverage_s),
        sample_coverage_ratio=min(
            1.0, sample_coverage_s / max(0.001, recording.duration_ms / 1000)
        ),
        model_name=run.model_id,
        model_sha256=run.model_sha256,
        confidence=float(run.configuration["confidence"]),
        observation_totals_by_class=observation_totals,
        estimated_tracker_id_totals_by_class={name: len(ids) for name, ids in tracker_sets.items()},
        line_crossings=line_crossings,
        available_metrics=["observations", "presence_seconds"],
        warnings=warnings,
        artifact_version=run.observation_schema_version or 1,
    )


@router.get(
    "/api/recordings/{recording_id}/analyses/{run_id}/analytics/heatmap",
    response_model=HeatmapResponse,
)
def analytics_heatmap(
    recording_id: UUID,
    run_id: UUID,
    start_s: float = Query(default=0, ge=0, le=7200),
    end_s: float | None = Query(default=None, ge=0, le=7200),
    classes: str = Query(default="bicycle,car,motorcycle,bus,truck", max_length=80),
    mode: str = Query(default="observations", pattern="^(observations|presence_seconds)$"),
    grid_width: int = Query(default=128, ge=16, le=256),
    radius: float = Query(default=0.03, ge=0.005, le=0.12),
    principal: Principal = Depends(require(Permission.videos_read)),
) -> HeatmapResponse:
    recording, run = _scoped_run(principal, recording_id, run_id)
    start, end = _range(start_s, end_s, recording)
    selected = _class_filter(classes)
    with _analytics_slot(), _frames(principal, recording, run) as (_, frames):
        result = heatmap(
            frames,
            width=recording.width,
            height=recording.height,
            crop=run.configuration["crop"],
            duration_s=recording.duration_ms / 1000,
            sample_fps=float(run.configuration["sample_fps"]),
            start_s=start,
            end_s=end,
            classes=selected,
            mode=mode,
            grid_width=grid_width,
            radius=radius,
        )
    principal.audit(
        AuditAction.analysis_analytics_viewed, resource_type="analysis_runs", resource_id=run.id
    )
    return HeatmapResponse(**result)


@router.get(
    "/api/recordings/{recording_id}/analyses/{run_id}/analytics/timeline",
    response_model=TimelineResponse,
)
def analytics_timeline(
    recording_id: UUID,
    run_id: UUID,
    start_s: float = Query(default=0, ge=0, le=7200),
    end_s: float | None = Query(default=None, ge=0, le=7200),
    classes: str = Query(default="bicycle,car,motorcycle,bus,truck", max_length=80),
    bin_seconds: float = Query(default=5, ge=1, le=300),
    principal: Principal = Depends(require(Permission.videos_read)),
) -> TimelineResponse:
    recording, run = _scoped_run(principal, recording_id, run_id)
    start, end = _range(start_s, end_s, recording)
    selected = _class_filter(classes)
    with _analytics_slot(), _frames(principal, recording, run) as (_, frames):
        result = timeline(
            frames,
            duration_s=recording.duration_ms / 1000,
            sample_fps=float(run.configuration["sample_fps"]),
            start_s=start,
            end_s=end,
            classes=selected,
            bin_seconds=bin_seconds,
        )
    principal.audit(
        AuditAction.analysis_analytics_viewed, resource_type="analysis_runs", resource_id=run.id
    )
    return TimelineResponse(**result)


@router.get("/api/recordings/{recording_id}/analyses/{run_id}/analytics/frame")
def analytics_reference_frame(
    recording_id: UUID,
    run_id: UUID,
    pts_seconds: float = Query(default=2, ge=0, le=7200),
    principal: Principal = Depends(require(Permission.videos_read)),
) -> Response:
    recording, run = _scoped_run(principal, recording_id, run_id)
    if not math.isfinite(pts_seconds) or pts_seconds > recording.duration_ms / 1000:
        raise HTTPException(422, "Frame time is outside the recording")

    global _frame_detector
    detector = _frame_detector
    if detector is None:
        with _frame_detector_lock:
            detector = _frame_detector
            if detector is None:
                if not MODEL_PATH.is_file():
                    raise HTTPException(503, "The configured local YOLOX-S model is unavailable")
                detector = YoloXOnnx(MODEL_PATH, input_size=640)
                _frame_detector = detector
    with decrypted_temp(principal.keyring, recording.id, recording.storage_key) as path:
        capture = cv2.VideoCapture(str(path))
        try:
            capture.set(cv2.CAP_PROP_POS_MSEC, pts_seconds * 1000)
            ok, frame = capture.read()
            actual_pts = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
        finally:
            capture.release()
    if not ok or frame is None:
        raise HTTPException(422, "The representative source frame could not be decoded")
    predictions = detector.predict(frame, confidence_threshold=0.2)
    redact_frame(
        frame,
        [
            (COCO.get(int(cls), "object"), box)
            for box, cls in zip(predictions.xyxy, predictions.class_id, strict=True)
        ],
        mode=redaction_mode(),
    )
    encoded_ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 86])
    if not encoded_ok:
        raise HTTPException(500, "The representative frame could not be encoded")
    principal.audit(
        AuditAction.analysis_analytics_viewed, resource_type="analysis_runs", resource_id=run.id
    )
    return Response(
        encoded.tobytes(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-Media-PTS-S": f"{actual_pts:.3f}",
            "X-Frame-Redaction": redaction_mode(),
        },
    )


@router.get(
    "/api/recordings/{recording_id}/analyses/{run_id}/candidates",
    response_model=OfflineCandidateResponse,
)
def offline_candidates(
    recording_id: UUID,
    run_id: UUID,
    principal: Principal = Depends(require(Permission.videos_read)),
) -> OfflineCandidateResponse:
    recording, run = _scoped_run(principal, recording_id, run_id)
    raw = (run.counts or {}).get("candidate_events", [])
    rules = (run.configuration or {}).get("rules", {})
    candidates = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "observation"))
        thresholds = {
            "rule_configuration": rules,
            "observed_reason": item.get("reason"),
            "output_time_s": item.get("output_time_s"),
        }
        candidates.append(
            OfflineCandidateProvenance(
                tenant_id=principal.tenant_id,
                source_video_id=recording.id,
                analysis_run_id=run.id,
                source_pts_ms=max(0, int(item.get("pts_ms", 0))),
                end_pts_ms=item.get("end_pts_ms"),
                rule_id=kind,
                rule_version="offline-rules-v1",
                threshold_evidence=thresholds,
                track_id=item.get("track_id"),
                class_ref=item.get("class"),
                confidence=item.get("confidence"),
                evidence_ref=f"/api/recordings/{recording.id}/analyses/{run.id}/video"
                if run.output_storage_key
                else None,
                label=str(item.get("label", kind))[:160],
                limitations=str(
                    item.get(
                        "limitations",
                        "Candidate observation; requires human verification "
                        "and does not establish an enforcement violation.",
                    )
                )[:500],
            )
        )
    principal.audit(
        AuditAction.analysis_analytics_viewed, resource_type="analysis_runs", resource_id=run.id
    )
    return OfflineCandidateResponse(
        source_video_id=recording.id,
        analysis_run_id=run.id,
        tenant_id=principal.tenant_id,
        candidates=candidates,
        flow_analytics=(run.counts or {}).get("flow_events", []),
    )


class PromotionIn(BaseModel):
    synthetic_test: bool = False
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=10, max_length=500)


@router.post("/api/recordings/{recording_id}/analyses/{run_id}/candidates/{index}/promote")
def promote_candidate(
    recording_id: UUID,
    run_id: UUID,
    index: int = ApiPath(ge=0),
    body: PromotionIn = ...,
    principal: Principal = Depends(require(Permission.alerts_create)),
):
    from app.core.policy import has_permission
    from app.services.offline_promotion import promote

    if not has_permission(principal.role, Permission.videos_analyze):
        raise HTTPException(403, "Recorded analysis permission required")
    recording, run = _scoped_run(principal, recording_id, run_id)
    return promote(
        principal, recording, run, index, body.reason, synthetic_test=body.synthetic_test
    )
