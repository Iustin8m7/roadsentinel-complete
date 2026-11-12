"""Explicit recorded-candidate submission to the canonical, human-reviewed alert queue."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import cv2
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.audit import AuditAction
from app.core.catalog import priority_for
from app.models import Alert, Camera
from app.services import evidence
from app.services.keys import load_keyring
from app.services.offline_video_storage import decrypted_temp

ELIGIBLE = {"possible_obstruction": "stopped_on_road", "traffic_queue": "congestion"}


def promote(
    principal, recording, run, index: int, reason: str, *, synthetic_test: bool = False
) -> dict:
    db = principal.db
    items = (run.counts or {}).get("candidate_events", [])
    if index < 0 or index >= len(items) or not isinstance(items[index], dict):
        raise HTTPException(404, "Candidate not found")
    item = items[index]
    kind = ELIGIBLE.get(item.get("type"))
    if kind is None:
        raise HTTPException(422, "This observation is analytics only, not eligible for review")
    if not run.output_storage_key:
        raise HTTPException(409, "Redacted analysis output is required")
    t = float(item.get("output_time_s", -1))
    if not math.isfinite(t) or t < 0 or t > (run.output_duration_ms or 0) / 1000:
        raise HTTPException(409, "Candidate output timestamp is invalid")
    # Serialize per recording, including camera creation and duplicate submissions.
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"offline:{principal.tenant_id}:{recording.id}"},
    )
    key = f"offline:{run.id}:{index}"
    existing = db.scalar(select(Alert).where(Alert.event_key == key))
    if existing:
        return {"id": existing.number, "origin": "recorded_upload", "duplicate": True}
    slug = f"recorded-{recording.id.hex}"
    camera = db.scalar(select(Camera).where(Camera.slug == slug))
    if camera is None:
        camera = Camera(
            tenant_id=principal.tenant_id,
            slug=slug,
            name="RECORDED · uploaded evidence",
            location="Recorded upload; capture time unverified",
            source_kind="recorded_replay",
            lifecycle_state="disabled",
            desired_enabled=False,
            is_active=False,
        )
        db.add(camera)
        db.flush()
    keyring = load_keyring(db, principal.tenant_id)
    start = max(0, t - 3)
    duration = min(6, (run.output_duration_ms or 0) / 1000 - start)
    if duration <= 0:
        raise HTTPException(409, "Empty evidence interval")
    with decrypted_temp(keyring, run.id, run.output_storage_key) as source:
        cap = cv2.VideoCapture(str(source))
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                raise HTTPException(409, "Candidate evidence frame is unavailable")
            cv2.putText(
                frame,
                "RECORDED - REVIEW CANDIDATE",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )
            ok, jpeg = cv2.imencode(".jpg", frame)
            if not ok:
                raise HTTPException(409, "Cannot encode evidence frame")
        finally:
            cap.release()
        with tempfile.TemporaryDirectory(prefix="promotion-") as folder:
            clip = Path(folder) / "clip.mp4"
            try:
                encoder = shutil.which("ffmpeg")
                if encoder is None:
                    raise OSError("ffmpeg unavailable")
                subprocess.run(  # noqa: S603 - fixed encoder, generated local paths, no shell
                    [
                        encoder,
                        "-nostdin",
                        "-loglevel",
                        "error",
                        "-ss",
                        str(start),
                        "-i",
                        str(source),
                        "-t",
                        str(duration),
                        "-an",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        str(clip),
                    ],
                    check=True,
                    timeout=30,
                    capture_output=True,
                )
            except (OSError, subprocess.SubprocessError):
                raise HTTPException(503, "Bounded evidence encoder unavailable") from None
            if clip.stat().st_size > 50 * 1024 * 1024:
                raise HTTPException(413, "Evidence clip exceeds policy limit")
            clip_bytes = clip.read_bytes()
    alert = Alert(
        tenant_id=principal.tenant_id,
        camera_id=camera.id,
        priority=priority_for(kind),
        event_type=kind,
        event_key=key,
        description=str(item.get("reason", "Recorded candidate"))[:500],
        detected_at=datetime.now(UTC),
        video_t=t,
        track_id=item.get("track_id"),
        rule=str(item.get("reason", "Recorded candidate"))[:500],
        details={
            "origin": "recorded_upload",
            "synthetic": synthetic_test,
            "source_note": recording.provenance_note[:300],
            "recording_id": str(recording.id),
            "analysis_run_id": str(run.id),
            "candidate_index": index,
            "source_pts_ms": item.get("pts_ms"),
            "capture_time_verified": False,
            "model_id": run.model_id,
            "model_sha256": run.model_sha256,
            "rule_version": "offline-rules-v1",
            "redaction": "full",
            "review_only": True,
            "limitations": str(item.get("limitations", ""))[:500],
            "clip_start_output_s": start,
            "clip_duration_s": duration,
            "clip_encoded_fps": run.output_fps,
        },
    )
    db.add(alert)
    db.flush()
    for data, mime, variant in (
        (jpeg.tobytes(), "image/jpeg", "keyframe"),
        (clip_bytes, "video/mp4", "clip"),
    ):
        evidence.ingest(
            db,
            keyring,
            alert,
            original=None,
            redacted=data,
            content_type=mime,
            kind=variant,
            redaction="full",
        )
    db.commit()
    principal.audit(
        AuditAction.alert_created,
        resource_type="alerts",
        resource_id=alert.id,
        details={
            "source": "offline_candidate_promotion",
            "reason": reason,
            "analysis_run_id": str(run.id),
            "candidate_index": index,
            "event_no": alert.number,
        },
    )
    return {"id": alert.number, "origin": "recorded_upload", "duplicate": False}
