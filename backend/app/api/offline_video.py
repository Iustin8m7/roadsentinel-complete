from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import ValidationError
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, require
from app.models import AnalysisRun, Recording
from app.schemas.offline_video import AnalysisCreate, AnalysisOut, CropIn, RecordingOut, RecordingRights, RecordingRightsUpdate
from app.services.offline_analysis import offline_analysis_manager
from app.services.offline_video_storage import (
    MAX_PLAINTEXT_BYTES,
    decrypt_range,
    decrypted_temp,
    encrypt_file,
    stage_plaintext,
    storage_key,
    storage_path,
)

router = APIRouter(tags=["offline-video-analysis"])
MAX_DURATION_S = 2 * 60 * 60
SUPPORTED_CODECS = {"vp8", "vp9", "av1", "h264", "hevc", "mpeg4", "mjpeg"}
ALLOWED_EXTENSIONS = {".webm", ".mp4", ".m4v", ".mov", ".mkv"}


def _recording_out(row: Recording) -> RecordingOut:
    return RecordingOut(
        id=row.id,
        original_filename=row.original_filename,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        codec=row.codec,
        duration_ms=row.duration_ms,
        width=row.width,
        height=row.height,
        fps_num=row.fps_num,
        fps_den=row.fps_den,
        imported_at=row.imported_at,
        provenance_note=row.provenance_note,
        status=row.status,
        crop=row.crop,
        crop_revision=row.crop_revision,
        rights_context=row.rights_context,
        rights_revision=row.rights_revision,
    )


def _analysis_out(row: AnalysisRun) -> AnalysisOut:
    progress = (
        min(1.0, row.decoded_frames / row.total_estimated_frames)
        if row.total_estimated_frames
        else 0.0
    )
    return AnalysisOut(
        id=row.id,
        recording_id=row.recording_id,
        status=row.status,
        configuration=row.configuration,
        model_id=row.model_id,
        model_sha256=row.model_sha256,
        created_at=row.created_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        processed_frames=row.processed_frames,
        decoded_frames=row.decoded_frames,
        skipped_frames=row.skipped_frames,
        total_estimated_frames=row.total_estimated_frames,
        latest_media_pts_ms=row.latest_media_pts_ms,
        progress=progress,
        inference_fps=row.inference_fps,
        counts=row.counts or {},
        warnings=row.warnings or [],
        error_code=row.error_code,
        output_size_bytes=row.output_size_bytes,
        output_duration_ms=row.output_duration_ms,
        output_fps=row.output_fps,
        has_output=bool(row.output_storage_key),
        preview_sequence=row.preview_sequence,
        has_analytics=bool(row.observations_complete and row.observation_storage_key),
        observation_count=row.observation_count,
        observation_schema_version=row.observation_schema_version,
    )


def _safe_filename(value: str | None) -> str:
    raw = (value or "recording.webm").replace("\\", "/").split("/")[-1]
    cleaned = "".join(c for c in raw if c >= " " and c not in "\x7f")[:255].strip()
    if not cleaned or cleaned in {".", ".."}:
        raise HTTPException(400, "Invalid recording filename")
    if Path(cleaned).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Choose a WebM, MP4, M4V, MOV or MKV video")
    return cleaned


def _inspect_media(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise HTTPException(503, "ffprobe is required for offline video import")
    try:
        result = subprocess.run(  # noqa: S603 - fixed ffprobe with a generated local path; no shell
            [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=25,
            # ffprobe path is resolved from PATH; path arg is a server-created, private temp file.
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, "ffprobe is required for offline video import") from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise HTTPException(415, "Video metadata could not be read") from exc
    try:
        info = json.loads(result.stdout)
        videos = [s for s in info["streams"] if s.get("codec_type") == "video"]
        if len(videos) != 1:
            raise ValueError
        stream = videos[0]
        codec = stream["codec_name"].lower()
        width, height = int(stream["width"]), int(stream["height"])
        duration = float(stream.get("duration") or info["format"]["duration"])
        rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
        numerator, denominator = map(int, rate.split("/"))
        fps = numerator / denominator
        if codec not in SUPPORTED_CODECS or not (64 <= width <= 7680 and 64 <= height <= 4320):
            raise ValueError
        if not (0 < duration <= MAX_DURATION_S and 0 < fps <= 120):
            raise ValueError
    except (KeyError, TypeError, ValueError, ZeroDivisionError, IndexError) as exc:
        raise HTTPException(415, "Unsupported, corrupt or out-of-bounds video content") from exc
    return {
        "codec": codec,
        "width": width,
        "height": height,
        "duration_ms": int(duration * 1000),
        "fps_num": numerator,
        "fps_den": denominator,
    }


@router.post("/api/recordings", response_model=RecordingOut, status_code=201)
def import_recording(
    file: UploadFile = File(...),
    rights_json: str | None = Form(default=None),
    principal: Principal = Depends(require(Permission.videos_analyze)),
    content_length: str | None = Header(default=None),
) -> RecordingOut:
    rights = None
    if rights_json is not None:
        try:
            rights = RecordingRights.model_validate_json(rights_json)
        except ValidationError as exc:
            raise HTTPException(422, "Invalid or expired source-rights declaration") from exc
    if content_length:
        try:
            if int(content_length) > MAX_PLAINTEXT_BYTES + 1024 * 1024:
                raise HTTPException(413, "Recording exceeds the 1 GiB import limit")
        except ValueError as exc:
            raise HTTPException(400, "Invalid Content-Length") from exc
    display_name = _safe_filename(file.filename)
    staged, staged_path = stage_plaintext()
    digest = hashlib.sha256()
    size = 0
    encrypted_key = None
    committed = False
    try:
        free = shutil.disk_usage(staged_path.parent).free
        if free < 1024 * 1024 * 1024:
            raise HTTPException(
                507, "At least 1 GiB free space is required for safe video processing"
            )
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_PLAINTEXT_BYTES:
                raise HTTPException(413, "Recording exceeds the 1 GiB import limit")
            digest.update(chunk)
            staged.write(chunk)
        staged.flush()
        os.fsync(staged.fileno())
        staged.close()
        if size == 0:
            raise HTTPException(400, "The selected video is empty")
        sha = digest.hexdigest()
        existing = principal.db.scalar(
            select(Recording).where(
                Recording.tenant_id == principal.tenant_id, Recording.sha256 == sha
            )
        )
        if existing:
            return _recording_out(existing)
        metadata = _inspect_media(staged_path)
        recording_id = uuid.uuid4()
        key = storage_key(principal.tenant_id, recording_id, "source")
        keyring = principal.keyring
        encrypt_file(keyring, recording_id, staged_path, key)
        encrypted_key = key
        row = Recording(
            id=recording_id,
            tenant_id=principal.tenant_id,
            owner_user_id=principal.user_id,
            original_filename=display_name,
            storage_key=key,
            sha256=sha,
            size_bytes=size,
            codec=metadata["codec"],
            duration_ms=metadata["duration_ms"],
            width=metadata["width"],
            height=metadata["height"],
            fps_num=metadata["fps_num"],
            fps_den=metadata["fps_den"],
            imported_at=datetime.now(UTC),
            status="ready",
            provenance_note=(
                "User-imported recorded screen capture; capture wall-clock time unverified."
            ),
            crop={"x": 0, "y": 0, "width": 1, "height": 1, "confirmed": False},
            crop_revision=0,
            rights_context=rights.model_dump(mode="json") if rights else None,
            rights_revision=1 if rights else 0,
        )
        principal.db.add(row)
        try:
            principal.db.flush()
            principal.audit(
                AuditAction.recording_imported,
                resource_type="recordings",
                resource_id=recording_id,
                details={"sha256": sha, "size_bytes": size},
            )
            principal.db.commit()
            committed = True
            if rights:
                principal.audit(
                    "recording.rights.declared",
                    resource_type="recordings",
                    resource_id=recording_id,
                    details={"revision": 1, "basis": rights.permission_basis},
                )
        except IntegrityError:
            principal.db.rollback()
            storage_path(key).unlink(missing_ok=True)
            encrypted_key = None
            existing = principal.db.scalar(
                select(Recording).where(
                    Recording.tenant_id == principal.tenant_id, Recording.sha256 == sha
                )
            )
            if existing:
                return _recording_out(existing)
            raise HTTPException(409, "Recording import conflicted with another update") from None
        return _recording_out(row)
    finally:
        if not staged.closed:
            staged.close()
        staged_path.unlink(missing_ok=True)
        if encrypted_key and not committed:
            storage_path(encrypted_key).unlink(missing_ok=True)
        with suppress(OSError):
            file.file.close()


@router.get("/api/recordings", response_model=list[RecordingOut])
def list_recordings(
    principal: Principal = Depends(require(Permission.videos_read)),
) -> list[RecordingOut]:
    rows = principal.db.scalars(
        select(Recording)
        .where(Recording.tenant_id == principal.tenant_id)
        .order_by(Recording.created_at.desc())
        .limit(200)
    ).all()
    queued = principal.db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.tenant_id == principal.tenant_id, AnalysisRun.status == "queued")
        .order_by(AnalysisRun.created_at)
    ).all()
    for run in queued:
        offline_analysis_manager.enqueue(principal.tenant_id, run.id)
    return [_recording_out(row) for row in rows]


@router.patch("/api/recordings/{recording_id}/rights", response_model=RecordingOut)
def update_recording_rights(
    recording_id: uuid.UUID,
    body: RecordingRightsUpdate,
    principal: Principal = Depends(require(Permission.videos_analyze)),
) -> RecordingOut:
    row = _owned_recording(principal, recording_id)
    principal.db.refresh(row, with_for_update=True)
    if row.rights_revision != body.expected_revision:
        raise HTTPException(409, "Source rights changed; reload the recording")
    row.rights_context = body.rights.model_dump(mode="json")
    row.rights_revision += 1
    principal.db.commit()
    principal.audit(
        "recording.rights.declared",
        resource_type="recordings",
        resource_id=row.id,
        details={"revision": row.rights_revision, "basis": body.rights.permission_basis},
    )
    return _recording_out(row)


@router.get("/api/recordings/{recording_id}", response_model=RecordingOut)
def get_recording(
    recording_id: uuid.UUID, principal: Principal = Depends(require(Permission.videos_read))
) -> RecordingOut:
    row = principal.db.scalar(
        select(Recording).where(
            Recording.id == recording_id, Recording.tenant_id == principal.tenant_id
        )
    )
    if not row:
        raise HTTPException(404, "Recording not found")
    return _recording_out(row)


def _owned_recording(principal: Principal, recording_id: uuid.UUID) -> Recording:
    row = principal.db.scalar(
        select(Recording).where(
            Recording.id == recording_id, Recording.tenant_id == principal.tenant_id
        )
    )
    if not row:
        raise HTTPException(404, "Recording not found")
    return row


@router.get("/api/recordings/{recording_id}/thumbnail")
def recording_thumbnail(
    recording_id: uuid.UUID,
    pts_seconds: float = Query(default=1, ge=0, le=7200),
    principal: Principal = Depends(require(Permission.videos_read)),
) -> Response:
    recording = _owned_recording(principal, recording_id)
    try:
        with decrypted_temp(principal.keyring, recording.id, recording.storage_key) as path:
            cap = cv2.VideoCapture(str(path))
            cap.set(cv2.CAP_PROP_POS_MSEC, pts_seconds * 1000)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                raise HTTPException(422, "Could not decode a representative video frame")
            ok, image = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise HTTPException(500, "Could not encode the frame preview")
            return Response(
                image.tobytes(),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-store, private",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )
    except FileNotFoundError as exc:
        raise HTTPException(410, "Recording media is unavailable") from exc


@router.patch("/api/recordings/{recording_id}/crop", response_model=RecordingOut)
def save_crop(
    recording_id: uuid.UUID,
    body: CropIn,
    principal: Principal = Depends(require(Permission.videos_analyze)),
) -> RecordingOut:
    row = principal.db.scalar(
        select(Recording)
        .where(Recording.id == recording_id, Recording.tenant_id == principal.tenant_id)
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "Recording not found")
    if row.crop_revision != body.expected_revision:
        raise HTTPException(409, "Crop changed in another session; reload before saving")
    px_w, px_h = round(body.width * row.width), round(body.height * row.height)
    if px_w < 64 or px_h < 64:
        raise HTTPException(422, "The crop must be at least 64x64 pixels")
    row.crop = {
        "x": body.x,
        "y": body.y,
        "width": body.width,
        "height": body.height,
        "confirmed": body.confirmed,
        "source_width": row.width,
        "source_height": row.height,
        "coordinate_space": "normalized_original_frame",
    }
    row.crop_revision += 1
    principal.audit(
        AuditAction.recording_crop_updated,
        resource_type="recordings",
        resource_id=row.id,
        details={"revision": row.crop_revision, "crop": row.crop},
    )
    principal.db.commit()
    return _recording_out(row)


@router.post("/api/recordings/{recording_id}/analyses", response_model=AnalysisOut, status_code=202)
def create_analysis(
    recording_id: uuid.UUID,
    body: AnalysisCreate,
    principal: Principal = Depends(require(Permission.videos_analyze)),
) -> AnalysisOut:
    recording = _owned_recording(principal, recording_id)
    try:
        RecordingRights.model_validate(recording.rights_context)
    except ValidationError as exc:
        raise HTTPException(409, "Declare valid source rights before starting analysis") from exc
    from app.services.geolocation import head
    location = head(principal.db, "recording", recording.id)
    if location is None or location.state not in {"confirmed", "unknown"}:
        raise HTTPException(409, "Save the recording location or explicitly choose unknown before analysis")
    crop = recording.crop or {}
    if not crop.get("confirmed") or body.crop_revision != recording.crop_revision:
        raise HTTPException(
            409, "Confirm the crop on the current recording version before analysis"
        )
    active_count = (
        principal.db.scalar(
            select(func.count())
            .select_from(AnalysisRun)
            .where(
                AnalysisRun.tenant_id == principal.tenant_id,
                AnalysisRun.status.in_(["queued", "running"]),
            )
        )
        or 0
    )
    if active_count >= 3:
        raise HTTPException(429, "At most three analyses may be queued or running for this tenant")
    config = {
        "source_kind": "RECORDED SCREENCAST",
        "recording_sha256": recording.sha256,
        "crop": crop,
        "crop_revision": recording.crop_revision,
        "source_dimensions": [recording.width, recording.height],
        "sample_fps": body.sample_fps,
        "confidence": body.confidence,
        "counting_line": [p.model_dump() for p in body.counting_line]
        if body.counting_line
        else None,
        "rules": {
            "stationary_enabled": body.stationary_enabled,
            "stationary_duration_s": body.stationary_duration_s,
            "queue_enabled": body.queue_enabled,
            "queue_min_vehicles": body.queue_min_vehicles,
            "queue_duration_s": body.queue_duration_s,
            "monitored_region": "confirmed_crop",
        },
        "ruleset": "recorded-fixed-camera-v1",
        "ruleset_status": "configured",
        "output_mode": body.output_mode,
        "output_audio": False,
        "media_time_source": "container PTS; not capture wall-clock time",
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    model_path = Path(
        os.environ.get(
            "RS_YOLOX_MODEL_PATH", str(Path(__file__).resolve().parents[3] / "models/yolox_s.onnx")
        )
    )
    model_path = model_path.resolve()
    if not model_path.is_file():
        raise HTTPException(503, "Configured YOLOX-S ONNX model is unavailable")
    run = AnalysisRun(
        tenant_id=principal.tenant_id,
        recording_id=recording.id,
        actor_id=principal.user_id,
        status="queued",
        configuration=config,
        config_sha256=config_hash,
        model_id="stock-yolox-s-onnx",
        model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        counts={},
        warnings=[
            "Rules and physical speed calibration are not configured for this screen recording."
        ],
    )
    principal.db.add(run)
    principal.db.flush()
    principal.audit(
        AuditAction.analysis_started,
        resource_type="analysis_runs",
        resource_id=run.id,
        details={"recording_id": str(recording.id), "config_sha256": config_hash},
    )
    principal.db.commit()
    if not offline_analysis_manager.enqueue(principal.tenant_id, run.id):
        # Durable queued state remains recoverable from the recording list. It is truthful to return
        # QUEUED; it has not been started in a competing unbounded thread.
        run.warnings = [
            *list(run.warnings or []),
            "Local analysis queue is full; this run remains queued.",
        ]
        principal.db.commit()
    return _analysis_out(run)


def _owned_run(principal: Principal, run_id: uuid.UUID) -> AnalysisRun:
    run = principal.db.scalar(
        select(AnalysisRun).where(
            AnalysisRun.id == run_id, AnalysisRun.tenant_id == principal.tenant_id
        )
    )
    if not run:
        raise HTTPException(404, "Analysis not found")
    if run.status == "running" and run.worker_instance != offline_analysis_manager.instance_id:
        run.status, run.error_code, run.ended_at = (
            "interrupted",
            "backend_restarted",
            datetime.now(UTC),
        )
        principal.db.commit()
    return run


@router.get("/api/analyses/{run_id}", response_model=AnalysisOut)
def get_analysis(
    run_id: uuid.UUID, principal: Principal = Depends(require(Permission.videos_read))
) -> AnalysisOut:
    run = _owned_run(principal, run_id)
    if run.status == "queued":
        offline_analysis_manager.enqueue(principal.tenant_id, run.id)
    return _analysis_out(run)


@router.get("/api/recordings/{recording_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(
    recording_id: uuid.UUID, principal: Principal = Depends(require(Permission.videos_read))
) -> list[AnalysisOut]:
    _owned_recording(principal, recording_id)
    rows = principal.db.scalars(
        select(AnalysisRun)
        .where(
            AnalysisRun.recording_id == recording_id, AnalysisRun.tenant_id == principal.tenant_id
        )
        .order_by(AnalysisRun.created_at.desc())
        .limit(100)
    ).all()
    results = []
    for row in rows:
        owned = _owned_run(principal, row.id)
        if owned.status == "queued":
            offline_analysis_manager.enqueue(principal.tenant_id, owned.id)
        results.append(_analysis_out(owned))
    return results


@router.get("/api/analyses/{run_id}/preview")
def analysis_preview(
    run_id: uuid.UUID, principal: Principal = Depends(require(Permission.videos_read))
) -> Response:
    _owned_run(principal, run_id)
    result = offline_analysis_manager.preview(run_id)
    if not result:
        raise HTTPException(404, "No fresh analysis preview is available")
    data, sequence, pts_ms = result
    return Response(
        data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-Analysis-Sequence": str(sequence),
            "X-Media-PTS-Ms": str(pts_ms),
        },
    )


def _video_response(
    run: AnalysisRun, principal: Principal, range_header: str | None, attachment: bool
) -> Response:
    if not run.output_storage_key or not run.output_size_bytes:
        raise HTTPException(409, "This analysis has no completed output")
    size = run.output_size_bytes
    start, end, status_code = 0, size - 1, 200
    if range_header:
        if not range_header.startswith("bytes=") or "," in range_header:
            raise HTTPException(
                416,
                "Only one byte range is supported",
                headers={"Content-Range": f"bytes */{size}"},
            )
        spec = range_header[6:]
        left, sep, right = spec.partition("-")
        if not sep:
            raise HTTPException(
                416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"}
            )
        try:
            if left:
                start = int(left)
                end = min(size - 1, int(right) if right else size - 1)
            else:
                suffix = int(right)
                start = max(0, size - suffix)
                end = size - 1
        except ValueError as exc:
            raise HTTPException(
                416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"}
            ) from exc
        if start >= size or end < start:
            raise HTTPException(
                416, "Unsatisfiable byte range", headers={"Content-Range": f"bytes */{size}"}
            )
        status_code = 206
    length = end - start + 1
    keyring = principal.keyring
    body: Iterator[bytes] = decrypt_range(
        keyring, run.id, run.output_storage_key, start=start, end=end, plaintext_size=size
    )
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Cache-Control": "no-store, private",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Disposition": "attachment" if attachment else "inline",
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(body, status_code=status_code, media_type="video/mp4", headers=headers)


@router.get("/api/analyses/{run_id}/video")
def analysis_video(
    run_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require(Permission.videos_read)),
) -> Response:
    run = _owned_run(principal, run_id)
    principal.audit(
        "recorded_analysis.video_viewed", resource_type="analysis_runs", resource_id=run.id
    )
    return _video_response(run, principal, request.headers.get("range"), False)


@router.get("/api/analyses/{run_id}/export")
def export_analysis(
    run_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require(Permission.videos_analyze)),
) -> Response:
    run = _owned_run(principal, run_id)
    principal.audit(
        AuditAction.evidence_exported,
        resource_type="analysis_runs",
        resource_id=run.id,
        details={"kind": "recorded_analysis_output"},
    )
    return _video_response(run, principal, request.headers.get("range"), True)


@router.post("/api/analyses/{run_id}/cancel", response_model=AnalysisOut)
def cancel_analysis(
    run_id: uuid.UUID, principal: Principal = Depends(require(Permission.videos_analyze))
) -> AnalysisOut:
    run = _owned_run(principal, run_id)
    if run.status == "queued":
        run.status, run.ended_at = "cancelled", datetime.now(UTC)
    elif run.status == "running":
        run.cancel_requested = True
        offline_analysis_manager.cancel(principal.tenant_id, run.id)
    principal.audit(
        AuditAction.analysis_cancelled,
        resource_type="analysis_runs",
        resource_id=run.id,
        details={"previous_status": run.status},
    )
    principal.db.commit()
    return _analysis_out(run)
