"""Machine endpoints used by the detection pipeline. Authentication is the HMAC signature
(see ``app.services.ingest_auth``); session cookies are never accepted here.

The multipart shapes are the API.md ingestion contract. Everything is validated before anything
is stored; media is encrypted at rest as evidence of the alert (or camera)."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config import get_settings
from app.core.audit import AuditAction
from app.core.catalog import priority_for
from app.core.metrics import metrics
from app.deps import get_service_principal
from app.models import Alert, AlertStatus, Camera
from app.schemas.contract import CAMERA_ID, Created, IngestEvent
from app.services import evidence as evidence_service
from app.services.ingest_auth import ServicePrincipal
from app.services.live_preview import MAX_FRAME_BYTES, live_previews
from app.services.push import notify_new_alert

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

CameraSlug = Path(pattern=CAMERA_ID)

# What the pipeline blurred, as it reports in details.redaction ("full" | "heads_only" | "off").
# When the field is missing nothing is assumed: the evidence is recorded as "unknown".
# The pipeline sends one (already processed) file, so no distinct original is stored.
DEFAULT_REDACTION = "unknown"
VLM_MODEL = "claude-opus-5-5"

MAX_KEYFRAME = 5 * 1024 * 1024
MAX_CLIP = 50 * 1024 * 1024


class Pong(BaseModel):
    ok: bool
    account: str


@router.post("/ping", response_model=Pong)
def ping(principal: ServicePrincipal = Depends(get_service_principal)) -> Pong:
    """Connectivity and credential check for pipeline operators."""
    return Pong(ok=True, account=principal.account.name)


def _is_jpeg(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff"


def _is_mp4(data: bytes) -> bool:
    return len(data) >= 12 and data[4:8] == b"ftyp"


async def _read(part: object, name: str, limit: int) -> bytes:
    if not isinstance(part, UploadFile):
        raise HTTPException(422, f"{name}: file required")
    data = await part.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"{name}: file too large")
    return data


def _camera(principal: ServicePrincipal, slug: str) -> Camera:
    camera = principal.db.scalar(select(Camera).where(Camera.slug == slug))
    if camera is None or not camera.is_active:
        raise HTTPException(422, "Unknown camera")
    if not principal.allows_camera(camera.id):
        principal.audit(
            AuditAction.access_denied,
            resource_type="cameras",
            resource_id=camera.id,
            details={"reason": "camera_out_of_scope"},
        )
        raise HTTPException(403, "Camera not in this service account's scope")
    return camera


def _managed_fence(principal, camera, epoch, revision):
    """Fence stale/disabled/revoked managed producers on evidence and preview writes."""
    if camera.lifecycle_state == "legacy":
        return
    from app.models.camera_control import CameraWorkerStatus
    from app.services.camera_control import active_version, runnable

    ok, _, _ = runnable(principal.db, camera)
    row = principal.db.scalar(
        select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == camera.id)
    )
    version = active_version(principal.db, camera)
    if not ok:
        raise HTTPException(403, "Camera processing permission is not active")
    if (
        not row
        or not version
        or row.lease_epoch != epoch
        or not row.lease_expires_at
        or row.lease_expires_at <= datetime.now(UTC)
        or revision != version.revision
        or row.applied_revision != revision
    ):
        raise HTTPException(409, "Active camera lease and acknowledged revision required")


@router.post("/events", response_model=Created)
async def ingest_event(
    request: Request, principal: ServicePrincipal = Depends(get_service_principal)
) -> Created:
    """API.md ``POST /api/ingest/events``: multipart ``event`` (JSON), ``keyframe`` (JPEG),
    ``clip`` (MP4). 422 on any invalid part; nothing is stored in that case."""
    form = await request.form(max_files=2, max_fields=1)
    raw = form.get("event")
    if not isinstance(raw, str):
        raise HTTPException(422, "event: JSON field required")
    try:
        event = IngestEvent.model_validate_json(raw)
    except ValidationError as exc:
        errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
        raise HTTPException(422, errors) from None
    keyframe = await _read(form.get("keyframe"), "keyframe", MAX_KEYFRAME)
    clip = await _read(form.get("clip"), "clip", MAX_CLIP)
    if not _is_jpeg(keyframe):
        raise HTTPException(422, "keyframe: not a JPEG image")
    if not _is_mp4(clip):
        raise HTTPException(422, "clip: not an MP4 video")
    started = time.perf_counter()
    created = await run_in_threadpool(_store_event, principal, event, keyframe, clip)
    metrics.observe("rs_ingest_store_seconds", time.perf_counter() - started)
    return created


def _existing_by_key(db: Session, camera_id: uuid.UUID, key: str) -> int | None:
    return db.scalar(
        select(Alert.number).where(Alert.camera_id == camera_id, Alert.event_key == key)
    )


def _store_event(
    principal: ServicePrincipal, event: IngestEvent, keyframe: bytes, clip: bytes
) -> Created:
    db = principal.db
    camera = _camera(principal, event.camera_id)
    _managed_fence(
        principal, camera, event.details.get("worker_epoch"), event.details.get("config_revision")
    )
    camera.last_seen_at = datetime.now(UTC)
    if event.event_key:
        existing = _existing_by_key(db, camera.id, event.event_key)
        if existing is not None:  # retry of an event that already arrived: idempotent
            db.commit()
            metrics.inc("rs_ingest_events_total", result="duplicate")
            return Created(id=existing)
    detected_at = event.occurred_at.replace(tzinfo=ZoneInfo(camera.timezone)).astimezone(UTC)
    priority = priority_for(event.type)
    alert = Alert(
        tenant_id=principal.tenant_id,
        camera_id=camera.id,
        priority=priority,
        event_type=event.type,
        description=event.rule[:500],
        detected_at=detected_at,
        video_t=event.video_t,
        track_id=event.track_id,
        object_class=event.object_class,
        speed_kmh=event.speed_kmh,
        rule=event.rule,
        details=json.loads(json.dumps(event.details, default=str)),
        event_key=event.event_key,
        vlm_status=event.vlm_status,
        vlm_text=event.vlm_text,
    )
    try:
        with db.begin_nested():  # savepoint: a lost race must not drop the tenant context
            db.add(alert)
            db.flush()
    except IntegrityError:
        existing = _existing_by_key(db, camera.id, event.event_key) if event.event_key else None
        if existing is None:
            raise
        db.commit()
        return Created(id=existing)
    from app.services.geolocation import link_camera
    link_camera(db, alert, camera, event.details.get("config_revision"))
    for kind, data, content_type in (
        ("keyframe", keyframe, "image/jpeg"),
        ("clip", clip, "video/mp4"),
    ):
        evidence_service.ingest(
            db,
            principal.keyring,
            alert,
            original=None,
            redacted=data,
            content_type=content_type,
            kind=kind,
            redaction=event.details.get("redaction") or DEFAULT_REDACTION,
        )
    from app.services.notifications import record as record_notification
    record_notification(db, alert, "candidate_created")
    db.commit()
    principal.audit(
        AuditAction.alert_created,
        resource_type="alerts",
        resource_id=alert.id,
        details={
            "event_no": alert.number,
            "type": alert.event_type,
            "priority": priority.value,
            "rule": event.rule,
        },
    )
    if event.vlm_status in ("confirmed", "rejected", "uncertain"):
        raw_verdict = event.details.get("vlm")
        verdict: dict[str, object] = raw_verdict if isinstance(raw_verdict, dict) else {}
        principal.audit(
            AuditAction.alert_vlm_verdict,
            resource_type="alerts",
            resource_id=alert.id,
            details={
                "event_no": alert.number,
                "verdict": event.vlm_status,
                "provider": "anthropic",
                "model": VLM_MODEL,
                "note": str(verdict.get("reason", ""))[:300] or None,
            },
        )
    notify_new_alert(principal.tenant_id, priority, None)
    metrics.inc("rs_ingest_events_total", result="accepted")
    return Created(id=alert.number)


class RuleStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    min_fps: float = Field(ge=0, le=1000)
    reason: str | None = Field(default=None, max_length=200)


class SourceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["file", "network", "device"]
    transport: Literal["auto", "file", "hls", "rtsp", "http_video", "snapshot", "uvc"] = "auto"
    state: Literal["waiting", "healthy", "stale"]
    last_frame_age_s: float | None = Field(default=None, ge=0, le=10_000_000)
    width: int | None = Field(default=None, ge=1, le=20_000)
    height: int | None = Field(default=None, ge=1, le=20_000)
    frames: int = Field(default=0, ge=0, le=2**63 - 1)
    failures: int = Field(default=0, ge=0, le=2**31 - 1)
    reconnects: int = Field(default=0, ge=0, le=2**31 - 1)
    replay: bool = False


class TrafficLineCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line: str = Field(min_length=1, max_length=64)
    lane: str = Field(min_length=1, max_length=64)
    object_class: Literal["car", "truck", "bus", "motorcycle"]
    count: int = Field(ge=0, le=2**63 - 1)


class TrafficFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_seconds: float = Field(ge=1, le=3600)
    total: float = Field(ge=0, le=1_000_000)
    by_class: dict[str, int] = Field(default_factory=dict, max_length=8)
    by_direction: dict[str, int] = Field(default_factory=dict, max_length=4)
    by_line: dict[str, int] = Field(default_factory=dict, max_length=32)

    @field_validator("by_class", "by_direction", "by_line")
    @classmethod
    def validate_counts(cls, values: dict[str, int]) -> dict[str, int]:
        invalid = any(
            not key or len(key) > 64 or not 0 <= value <= 2**63 - 1 for key, value in values.items()
        )
        if invalid:
            raise ValueError("traffic summary keys and counts must be bounded")
        return values


class TrafficStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_crossings: int = Field(ge=0, le=2**63 - 1)
    counts_by_line_lane_class: list[TrafficLineCount] = Field(default_factory=list, max_length=32)
    rolling_flow_per_minute: TrafficFlow


class Heartbeat(BaseModel):
    """Optional body: what the pipeline measures about this camera, so the UI can say honestly
    which alert types the camera can produce at its real frame rate."""

    model_config = ConfigDict(extra="forbid")

    fps: float | None = Field(default=None, ge=0, le=1000)
    rules: dict[str, RuleStatus] = Field(default_factory=dict, max_length=32)
    source: SourceStatus | None = None
    traffic: TrafficStatus | None = None
    processing_fps: float | None = Field(default=None, ge=0, le=1000)
    inference_latency_ms_p50: float | None = Field(default=None, ge=0, le=600_000)
    inference_latency_ms_p95: float | None = Field(default=None, ge=0, le=600_000)
    inference_latency_ms_p99: float | None = Field(default=None, ge=0, le=600_000)
    process_peak_rss_mb: float | None = Field(default=None, ge=0, le=1_000_000)
    detections: int = Field(default=0, ge=0, le=2**63 - 1)
    unique_tracks: int = Field(default=0, ge=0, le=2**63 - 1)
    tracks_by_class: dict[str, int] = Field(default_factory=dict, max_length=8)
    model: str | None = Field(default=None, max_length=100)
    model_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    inference_provider: (
        Literal["CPUExecutionProvider", "CUDAExecutionProvider", "UNKNOWN"] | None
    ) = None
    provider_fallback_reason: str | None = Field(default=None, max_length=240)

    @field_validator("tracks_by_class")
    @classmethod
    def validate_track_counts(cls, values: dict[str, int]) -> dict[str, int]:
        if any(
            not key or len(key) > 32 or not 0 <= value <= 2**63 - 1 for key, value in values.items()
        ):
            raise ValueError("track counts must be bounded")
        return values


@router.post("/cameras/{camera_id}/heartbeat", status_code=204)
async def ingest_heartbeat(
    request: Request,
    camera_id: str = CameraSlug,
    principal: ServicePrincipal = Depends(get_service_principal),
) -> None:
    """The live pipeline is processing this camera right now (sent every ~30 s)."""
    body = await request.body()
    try:
        parsed = json.loads(body) if body.strip() else {}
    except ValueError:
        raise HTTPException(422, "heartbeat: invalid JSON") from None
    if isinstance(parsed, dict) and "worker_epoch" in parsed:
        from app.schemas.camera_control import HeartbeatIn
        from app.services.camera_control import record_heartbeat

        try:
            telemetry = parsed.pop("telemetry", None)
            hb = HeartbeatIn.model_validate(parsed)
            measured = (
                Heartbeat.model_validate(telemetry).model_dump() if telemetry is not None else None
            )
        except ValidationError:
            raise HTTPException(422, "heartbeat: invalid managed status") from None
        camera = _camera(principal, camera_id)
        result = record_heartbeat(principal.db, camera, hb.model_dump())
        if measured is not None and result.lease == "holder" and result.reason != "stale_sequence":
            camera.status_info = {**measured, "reported_at": datetime.now(UTC).isoformat()}
        principal.db.commit()
        return JSONResponse(result.as_dict())
    status_info: dict[str, Any] | None = None
    if body.strip():
        try:
            status_info = Heartbeat.model_validate_json(body).model_dump()
        except ValidationError:
            raise HTTPException(422, "heartbeat: invalid status body") from None
    await run_in_threadpool(_store_heartbeat, principal, camera_id, status_info)


@router.post("/cameras/{camera_id}/preview", status_code=204)
async def ingest_camera_preview(
    request: Request,
    camera_id: str = CameraSlug,
    captured_at: datetime = ...,  # ISO-8601 UTC source timestamp, covered by the signed URL.
    sequence: int = ...,  # monotonic per-worker frame sequence, covered by the signed URL.
    principal: ServicePrincipal = Depends(get_service_principal),
) -> None:
    """Publish one redacted/annotated JPEG into a bounded in-memory display slot."""
    if captured_at.tzinfo is None or sequence < 0:
        raise HTTPException(
            422, "preview timestamp must be timezone-aware and sequence nonnegative"
        )
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "image/jpeg":
        raise HTTPException(415, "preview must be image/jpeg")
    frame = await request.body()
    if len(frame) > MAX_FRAME_BYTES:
        raise HTTPException(413, "preview frame too large")
    if not _is_jpeg(frame):
        raise HTTPException(422, "preview is not a JPEG image")
    camera = _camera(principal, camera_id)
    try:
        revision = int(request.query_params.get("revision", "0"))
    except ValueError:
        raise HTTPException(422, "Invalid revision") from None
    _managed_fence(principal, camera, request.query_params.get("worker_epoch"), revision)
    source = (camera.status_info or {}).get("source") or {}
    ttl_s = (
        120.0 if camera.slug == "ilisesti-dn17" or source.get("transport") == "snapshot" else None
    )
    live_previews.publish(
        principal.tenant_id, camera.slug, frame, captured_at, sequence, ttl_s=ttl_s
    )


def _store_heartbeat(
    principal: ServicePrincipal, camera_id: str, status_info: dict[str, Any] | None
) -> None:
    camera = _camera(principal, camera_id)
    camera.last_seen_at = datetime.now(UTC)
    if status_info is not None:
        prior_worker = (camera.status_info or {}).get("worker")
        camera.status_info = {**status_info, "reported_at": datetime.now(UTC).isoformat()}
        if prior_worker is not None:
            camera.status_info["worker"] = prior_worker
    principal.db.commit()


@router.put("/cameras/{camera_id}/video", status_code=204)
async def ingest_camera_video(
    request: Request,
    camera_id: str = CameraSlug,
    worker_epoch: str | None = Query(default=None, max_length=64),
    revision: int | None = Query(default=None, ge=1),
    principal: ServicePrincipal = Depends(get_service_principal),
) -> None:
    """Annotated recording of a camera (shown in the dashboard's camera view)."""
    form = await request.form(max_files=1, max_fields=0)
    video = await _read(form.get("video"), "video", get_settings().ingest_max_body_bytes)
    if not _is_mp4(video):
        raise HTTPException(422, "video: not an MP4 video")
    await run_in_threadpool(
        _store_camera_video, principal, camera_id, video, worker_epoch, revision
    )


def _store_camera_video(
    principal: ServicePrincipal, slug: str, video: bytes, epoch=None, revision=None
) -> None:
    camera = _camera(principal, slug)
    _managed_fence(principal, camera, epoch, revision)
    if camera.lifecycle_state != "legacy":
        from app.services.camera_control import grant_allows_recordings, grants_for

        if not grant_allows_recordings(
            camera, grants_for(principal.db, camera.id), datetime.now(UTC)
        ):
            raise HTTPException(403, "Recording storage is not authorized")
    ev = evidence_service.ingest(
        principal.db,
        principal.keyring,
        None,
        camera=camera,
        original=None,
        redacted=video,
        content_type="video/mp4",
        kind="camera_video",
        redaction=DEFAULT_REDACTION,
    )
    principal.db.commit()
    principal.audit(
        AuditAction.ingest_camera_video,
        resource_type="evidence",
        resource_id=ev.id,
        details={"camera": camera.slug, "size": len(video)},
    )


@router.delete("/cameras/{camera_id}", status_code=204)
def reset_camera(
    camera_id: str = CameraSlug, principal: ServicePrincipal = Depends(get_service_principal)
) -> None:
    """Demo reprocessing. Never deletes anything: in production it is refused; elsewhere the
    camera's undecided alerts are hidden (superseded). Decisions and evidence are kept."""
    camera = _camera(principal, camera_id)
    if get_settings().is_production:
        principal.audit(
            AuditAction.ingest_camera_clear_denied,
            resource_type="cameras",
            resource_id=camera.id,
            details={"camera": camera.slug},
        )
        raise HTTPException(403, "Camera reset is disabled in production; use live mode")
    result = principal.db.execute(
        update(Alert)
        .where(
            Alert.camera_id == camera.id,
            Alert.status == AlertStatus.new,
            Alert.superseded_at.is_(None),
        )
        .values(superseded_at=datetime.now(UTC))
    )
    principal.db.commit()
    principal.audit(
        AuditAction.ingest_camera_superseded,
        resource_type="cameras",
        resource_id=camera.id,
        details={"camera": camera.slug, "count": result.rowcount},  # type: ignore[attr-defined]
    )
