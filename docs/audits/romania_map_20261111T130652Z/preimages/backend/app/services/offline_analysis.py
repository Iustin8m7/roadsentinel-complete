"""Single-worker, durable-queue executor for tenant-scoped recorded video runs.

One FastAPI process owns this bounded local worker. Run metadata is durable in PostgreSQL;
progressive JPEG previews are transient in memory and expire after two minutes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from collections import Counter, deque
from contextlib import suppress
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np
from roadsentinel.detector import COCO, Detections, YoloXOnnx, create_tracker, to_supervision
from roadsentinel.redaction import redact_frame
from sqlalchemy import select

from app.db import get_sessionmaker, set_tenant
from app.models import AnalysisRun, Recording
from app.services.keys import load_keyring
from app.services.offline_heatmap import MAX_ARTIFACT_BYTES, observation_from_roi
from app.services.offline_video_storage import (
    decrypted_temp,
    encrypt_file,
    storage_key,
    storage_path,
)

MAX_WORK_QUEUE = 4
PREVIEW_TTL_S = 120
MODEL_PATH = Path(
    os.environ.get(
        "RS_YOLOX_MODEL_PATH", str(Path(__file__).resolve().parents[3] / "models" / "yolox_s.onnx")
    )
)
VEHICLE_CLASSES = {2, 3, 5, 7}  # COCO motor vehicles; exclude bicycle class 1


def _now() -> datetime:
    return datetime.now(UTC)


def _point(box: np.ndarray) -> tuple[float, float]:
    return (float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2))


def _side(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _segment_intersection(p, q, a, b) -> bool:
    s1, s2 = _side(p, a, b), _side(q, a, b)
    return s1 * s2 < 0


def _match_track_ids(pred: Detections, tracked: Detections) -> list[int | None]:
    """Attach IDs only for near-identical tracker boxes; keep unmatched detector rows untracked."""
    ids = tracked.tracker_id
    if ids is None or not len(tracked.xyxy):
        return [None] * len(pred.xyxy)
    result: list[int | None] = []
    for box, cls in zip(pred.xyxy, pred.class_id, strict=True):
        candidates = np.flatnonzero(tracked.class_id == cls)
        best_id, best_iou = None, 0.0
        for candidate in candidates:
            other = tracked.xyxy[candidate]
            intersection = max(0.0, min(box[2], other[2]) - max(box[0], other[0])) * max(
                0.0, min(box[3], other[3]) - max(box[1], other[1])
            )
            area_a = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
            area_b = max(0.0, other[2] - other[0]) * max(0.0, other[3] - other[1])
            iou = intersection / max(1e-9, area_a + area_b - intersection)
            if iou > best_iou:
                best_iou = iou
                value = ids[candidate]
                try:
                    best_id = int(value) if value is not None and np.isfinite(value) else None
                except (TypeError, ValueError, OverflowError):
                    best_id = None
        result.append(best_id if best_iou >= 0.9 else None)
    return result


class OfflineAnalysisManager:
    def __init__(self) -> None:
        self.instance_id = str(uuid.uuid4())
        self._queue: queue.Queue[tuple[uuid.UUID, uuid.UUID] | None] = queue.Queue(MAX_WORK_QUEUE)
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._cancel: dict[str, threading.Event] = {}
        self._active_ids: set[str] = set()
        self._previews: dict[str, tuple[bytes, int, int, float]] = {}
        self._detector: YoloXOnnx | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run, name="rs-offline-analysis", daemon=True
            )
            self._thread.start()

    def enqueue(self, tenant_id: uuid.UUID, run_id: uuid.UUID) -> bool:
        self.start()
        key = str(run_id)
        with self._lock:
            if key in self._active_ids:
                return True
            self._active_ids.add(key)
        try:
            self._queue.put_nowait((tenant_id, run_id))
            return True
        except queue.Full:
            with self._lock:
                self._active_ids.discard(key)
            return False

    def is_active(self, run_id: uuid.UUID) -> bool:
        with self._lock:
            return str(run_id) in self._active_ids

    def cancel(self, tenant_id: uuid.UUID, run_id: uuid.UUID) -> None:
        del tenant_id
        with self._lock:
            event = self._cancel.get(str(run_id))
            if event:
                event.set()
            # A queued id may remain in the queue; the worker rechecks durable state before work.

    def shutdown(self, timeout_s: float = 30) -> None:
        with self._lock:
            for event in self._cancel.values():
                event.set()
            thread = self._thread
        if thread and thread.is_alive():
            with suppress(queue.Full):
                self._queue.put(None, timeout=1)
            thread.join(timeout_s)

    def preview(self, run_id: uuid.UUID) -> tuple[bytes, int, int] | None:
        with self._lock:
            item = self._previews.get(str(run_id))
            if not item:
                return None
            data, seq, pts_ms, observed = item
            if time.monotonic() - observed > PREVIEW_TTL_S:
                self._previews.pop(str(run_id), None)
                return None
            return data, seq, pts_ms

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                self._queue.task_done()
                return
            tenant_id, run_id = job
            try:
                self._process(tenant_id, run_id)
            finally:
                with self._lock:
                    self._active_ids.discard(str(run_id))
                    self._cancel.pop(str(run_id), None)
                self._queue.task_done()

    def _session(self, tenant_id: uuid.UUID):
        db = get_sessionmaker()()
        set_tenant(db, tenant_id)
        return db

    def _process(self, tenant_id: uuid.UUID, run_id: uuid.UUID) -> None:
        db = self._session(tenant_id)
        temp_context = None
        temp_entered = False
        capture = None
        encoder = None
        output_key = None
        output_committed = False
        observation_key = None
        observation_committed = False
        observation_writer = None
        cancel = threading.Event()
        key = str(run_id)
        try:
            run = db.scalar(
                select(AnalysisRun)
                .where(AnalysisRun.id == run_id, AnalysisRun.tenant_id == tenant_id)
                .with_for_update()
            )
            if run is None or run.status != "queued":
                return
            recording = db.scalar(
                select(Recording).where(
                    Recording.id == run.recording_id, Recording.tenant_id == tenant_id
                )
            )
            if recording is None:
                run.status, run.error_code, run.ended_at = "failed", "recording_missing", _now()
                db.commit()
                return
            if run.cancel_requested:
                run.status, run.ended_at = "cancelled", _now()
                db.commit()
                return
            run.status, run.started_at, run.worker_instance = "running", _now(), self.instance_id
            run.warnings = list(run.warnings or [])
            with self._lock:
                self._cancel[key] = cancel
            db.commit()
            keyring = load_keyring(db, tenant_id)
            temp_context = decrypted_temp(keyring, recording.id, recording.storage_key)
            source_path = temp_context.__enter__()
            temp_entered = True
            capture = cv2.VideoCapture(str(source_path))
            if not capture.isOpened():
                raise ValueError("decoder_open_failed")

            conf = float(run.configuration["confidence"])
            sample_fps = float(run.configuration["sample_fps"])
            crop = run.configuration["crop"]
            x0 = max(0, min(recording.width - 2, round(crop["x"] * recording.width)))
            y0 = max(0, min(recording.height - 2, round(crop["y"] * recording.height)))
            crop_w = min(recording.width - x0, round(crop["width"] * recording.width))
            crop_h = min(recording.height - y0, round(crop["height"] * recording.height))
            crop_w -= crop_w % 2
            crop_h -= crop_h % 2
            if crop_w < 64 or crop_h < 64:
                raise ValueError("crop_too_small")
            nominal_fps = recording.fps_num / recording.fps_den
            total_estimated = max(1, round(recording.duration_ms / 1000 * nominal_fps))
            run.total_estimated_frames = total_estimated
            model = MODEL_PATH.resolve()
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            if digest != run.model_sha256:
                raise ValueError("model_hash_mismatch")
            if self._detector is None or getattr(self, "_detector_sha256", None) != digest:
                self._detector = YoloXOnnx(model, input_size=640)
                self._detector_sha256 = digest
            detector = self._detector
            ffmpeg_bin, ffprobe_bin = shutil.which("ffmpeg"), shutil.which("ffprobe")
            if not ffmpeg_bin or not ffprobe_bin:
                raise ValueError("media_tools_unavailable")
            tracker = create_tracker(sample_fps)
            line_config = run.configuration.get("counting_line")
            line = None
            if line_config:
                a_raw, b_raw = line_config
                line = (
                    (a_raw["x"] * crop_w, a_raw["y"] * crop_h),
                    (b_raw["x"] * crop_w, b_raw["y"] * crop_h),
                )
            previous_centers: dict[int, tuple[float, float]] = {}
            previous_center_pts: dict[int, float] = {}
            track_history: dict[int, deque[tuple[float, float, float, int]]] = {}
            event_candidates: list[dict] = []
            flow_events: list[dict] = []
            emitted_stops: set[int] = set()
            queue_samples: deque[tuple[float, set[int], int]] = deque()
            queue_episode_start: float | None = None
            queue_emitted = False
            rules = run.configuration.get("rules") or {}
            stationary_enabled = bool(rules.get("stationary_enabled", True))
            stationary_duration = float(rules.get("stationary_duration_s", 120))
            queue_enabled = bool(rules.get("queue_enabled", True)) and sample_fps >= 1
            queue_min = int(rules.get("queue_min_vehicles", 5))
            queue_duration = float(rules.get("queue_duration_s", 60))
            counted_tracks: set[int] = set()
            class_detections: Counter[str] = Counter()
            track_classes: dict[int, str] = {}
            tracks_by_class: Counter[str] = Counter()
            crossings = Counter()
            crossings_by_class = Counter()
            inference_ms: deque[float] = deque(maxlen=10000)
            last_sample = None
            next_pts = 0.0
            sample_origin = None
            sample_slot = 0
            decoded = processed = skipped = sequence = 0
            output_pts = 0.0
            output_fps = sample_fps
            start_wall = time.perf_counter()
            last_db_update = start_wall
            preview_lock = self._lock

            root = storage_path(recording.storage_key).parents[2]
            work_dir = Path(tempfile.mkdtemp(prefix=f"job-{run_id}-", dir=root))
            os.chmod(work_dir, 0o700)
            output_path = work_dir / "annotated.mp4"
            observation_path = work_dir / "observations.jsonl"
            observation_writer = observation_path.open("x", encoding="utf-8")
            os.chmod(observation_path, 0o600)
            observation_writer.write(
                json.dumps(
                    {
                        "record_type": "manifest",
                        "schema_version": 1,
                        "source_video_id": str(recording.id),
                        "analysis_run_id": str(run.id),
                        "tenant_id": str(tenant_id),
                        "coordinate_reference": "normalized_full_source_frame",
                        "source_width": recording.width,
                        "source_height": recording.height,
                        "crop": crop,
                        "crop_px": [x0, y0, crop_w, crop_h],
                        "model_id": run.model_id,
                        "model_sha256": run.model_sha256,
                        "sample_fps": sample_fps,
                        "confidence": conf,
                    },
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
            observation_count = 0
            while True:
                if cancel.is_set():
                    raise InterruptedError("cancelled")
                ok, frame = capture.read()
                if not ok:
                    break
                decoded += 1
                pos_s = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if (
                    not math.isfinite(pos_s)
                    or pos_s < 0
                    or (decoded > 2 and pos_s <= output_pts - 2)
                ):
                    pos_s = (decoded - 1) / nominal_fps
                if sample_origin is None:
                    sample_origin = pos_s
                    next_pts = pos_s
                if pos_s + 0.025 < next_pts:
                    skipped += 1
                else:
                    roi = frame[y0 : y0 + crop_h, x0 : x0 + crop_w].copy()
                    infer_started = time.perf_counter()
                    all_pred = detector.predict(roi, confidence_threshold=conf)
                    infer_s = time.perf_counter() - infer_started
                    inference_ms.append(infer_s * 1000)
                    redact_frame(
                        roi,
                        [
                            (COCO.get(int(cls), "object"), box)
                            for box, cls in zip(all_pred.xyxy, all_pred.class_id, strict=True)
                        ],
                        mode="full",
                    )
                    vehicle_mask = np.isin(all_pred.class_id, tuple(VEHICLE_CLASSES))
                    pred = Detections(
                        all_pred.xyxy[vehicle_mask],
                        all_pred.confidence[vehicle_mask],
                        all_pred.class_id[vehicle_mask],
                        all_pred.latency_ms,
                    )
                    for class_id in pred.class_id:
                        class_detections[COCO.get(int(class_id), str(int(class_id)))] += 1
                    tracked = tracker.update_with_detections(to_supervision(pred))
                    track_ids = _match_track_ids(pred, tracked)
                    observation_rows = []
                    for box, score, cls, track_id in zip(
                        pred.xyxy, pred.confidence, pred.class_id, track_ids, strict=True
                    ):
                        row = observation_from_roi(
                            box=box,
                            class_id=int(cls),
                            class_name=COCO.get(int(cls), "other"),
                            confidence=float(score),
                            track_id=track_id,
                            crop_px=(x0, y0, crop_w, crop_h),
                            source_width=recording.width,
                            source_height=recording.height,
                        )
                        if row is not None:
                            observation_rows.append(row)
                    observation_count += len(observation_rows)
                    frame_vehicle_ids: set[int] = set()
                    tids = tracked.tracker_id
                    if tids is not None:
                        for box, score, cls, tid in zip(
                            tracked.xyxy, tracked.confidence, tracked.class_id, tids, strict=True
                        ):
                            if tid is None:
                                continue
                            tid = int(tid)
                            cls_name = COCO.get(int(cls), str(int(cls)))
                            track_classes[tid] = cls_name
                            x1, y1, x2, y2 = (round(float(v)) for v in box)
                            label = f"{cls_name} {float(score):.2f} · #{tid}"
                            cv2.rectangle(roi, (x1, y1), (x2, y2), (40, 220, 125), 2)
                            cv2.putText(
                                roi,
                                label,
                                (x1, max(16, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.46,
                                (40, 220, 125),
                                1,
                                cv2.LINE_AA,
                            )
                            center = _point(box)
                            frame_vehicle_ids.add(tid)
                            history = track_history.setdefault(tid, deque())
                            history.append((pos_s, center[0], center[1], sequence))
                            while history and pos_s - history[0][0] > max(
                                stationary_duration + 5, 900
                            ):
                                history.popleft()
                            recent_motion = [p for p in history if pos_s - p[0] <= 5.0]
                            if len(recent_motion) >= 2 and math.hypot(
                                recent_motion[-1][1] - recent_motion[0][1],
                                recent_motion[-1][2] - recent_motion[0][2],
                            ) > max(18.0, math.hypot(x2 - x1, y2 - y1) * 0.25):
                                emitted_stops.discard(
                                    tid
                                )  # re-arm after observed movement for a new stop episode
                            if stationary_enabled and tid not in emitted_stops:
                                recent = [p for p in history if pos_s - p[0] <= stationary_duration]
                                need = max(4, math.ceil(stationary_duration * sample_fps * 0.65))
                                if (
                                    len(recent) >= need
                                    and recent[-1][0] - recent[0][0] >= stationary_duration * 0.9
                                    and all(
                                        b[0] - a[0] <= max(2.5 / sample_fps, 2.0)
                                        for a, b in pairwise(recent)
                                    )
                                ):
                                    dx = max(p[1] for p in recent) - min(p[1] for p in recent)
                                    dy = max(p[2] for p in recent) - min(p[2] for p in recent)
                                    if math.hypot(dx, dy) <= max(
                                        12.0, math.hypot(x2 - x1, y2 - y1) * 0.18
                                    ):
                                        event_candidates.append(
                                            {
                                                "type": "possible_obstruction",
                                                "label": "Possible obstruction — human review",
                                                "pts_ms": int(recent[0][0] * 1000),
                                                "end_pts_ms": int(pos_s * 1000),
                                                "output_time_s": recent[0][3] / sample_fps,
                                                "track_id": tid,
                                                "class": cls_name,
                                                "confidence": round(float(score), 3),
                                                "reason": (
                                                    "Nearly stationary in confirmed "
                                                    "monitored crop for "
                                                    f"{int(recent[-1][0] - recent[0][0])} s; "
                                                    "image displacement "
                                                    f"{math.hypot(dx, dy):.1f}px."
                                                ),
                                                "limitations": (
                                                    "Fixed-camera assumption; crop may include a "
                                                    "signal queue or parking. Requires operator "
                                                    "review."
                                                ),
                                            }
                                        )
                                        emitted_stops.add(tid)
                            if line:
                                old = previous_centers.get(tid)
                                if (
                                    old
                                    and tid not in counted_tracks
                                    and len(history) >= 2
                                    and pos_s - previous_center_pts.get(tid, -1e9)
                                    <= max(2.5 / sample_fps, 2.0)
                                    and _segment_intersection(old, center, *line)
                                ):
                                    direction = (
                                        "a_to_b"
                                        if _side(old, *line) < _side(center, *line)
                                        else "b_to_a"
                                    )
                                    crossings[direction] += 1
                                    crossings_by_class[f"{cls_name}:{direction}"] += 1
                                    counted_tracks.add(tid)
                                    flow_events.append(
                                        {
                                            "type": "line_crossing",
                                            "pts_ms": int(pos_s * 1000),
                                            "output_time_s": sequence / sample_fps,
                                            "track_id": tid,
                                            "class": cls_name,
                                            "direction": direction,
                                            "confidence": round(float(score), 3),
                                            "reason": (
                                                "ByteTrack center crossed the operator-drawn "
                                                "counting line."
                                            ),
                                        }
                                    )
                                previous_centers[tid] = center
                                previous_center_pts[tid] = pos_s
                    if queue_enabled:
                        queue_samples.append((pos_s, frame_vehicle_ids, sequence))
                        while queue_samples and pos_s - queue_samples[0][0] > queue_duration:
                            queue_samples.popleft()
                        occupancy = [len(ids) for _, ids, _ in queue_samples]
                        span = (
                            queue_samples[-1][0] - queue_samples[0][0]
                            if len(queue_samples) > 1
                            else 0
                        )
                        if (
                            len(occupancy) >= max(4, math.ceil(queue_duration * sample_fps * 0.65))
                            and span >= queue_duration * 0.9
                            and min(occupancy) >= queue_min
                            and not queue_emitted
                        ):
                            event_candidates.append(
                                {
                                    "type": "traffic_queue",
                                    "label": "Traffic queue / congestion candidate",
                                    "pts_ms": int(queue_samples[0][0] * 1000),
                                    "end_pts_ms": int(pos_s * 1000),
                                    "output_time_s": queue_samples[0][2] / sample_fps,
                                    "track_id": None,
                                    "class": "vehicles",
                                    "confidence": 0.65,
                                    "reason": (
                                        f"At least {queue_min} tracked vehicles persisted in the "
                                        f"crop for {int(span)} s; minimum simultaneous occupancy "
                                        f"{min(occupancy)}."
                                    ),
                                    "limitations": (
                                        "Vehicle presence does not prove congestion; fixed scene "
                                        "and operator crop required."
                                    ),
                                }
                            )
                            queue_emitted = True
                        if len(occupancy) < queue_min:
                            queue_emitted = False
                    for cls_name in set(track_classes.values()):
                        tracks_by_class[cls_name] = sum(
                            v == cls_name for v in track_classes.values()
                        )
                    if line:
                        la, lb = line
                        cv2.line(roi, tuple(map(int, la)), tuple(map(int, lb)), (255, 190, 40), 2)
                    pts_label = f"{int(pos_s // 60):02d}:{pos_s % 60:05.2f}"
                    cv2.rectangle(roi, (0, 0), (crop_w, 25), (12, 12, 12), -1)
                    cv2.putText(
                        roi,
                        f"RECORDED ANALYSIS · PTS {pts_label} · SAMPLED {sample_fps:g} FPS",
                        (8, 18),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (245, 245, 245),
                        1,
                        cv2.LINE_AA,
                    )
                    if encoder is None:
                        encoder_args = [
                            ffmpeg_bin,
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-y",
                            "-f",
                            "rawvideo",
                            "-pix_fmt",
                            "bgr24",
                            "-video_size",
                            f"{crop_w}x{crop_h}",
                            "-framerate",
                            f"{sample_fps:.3f}",
                            "-i",
                            "pipe:0",
                            "-an",
                            "-c:v",
                            "libx264",
                            "-preset",
                            "veryfast",
                            "-crf",
                            "27",
                            "-pix_fmt",
                            "yuv420p",
                            "-movflags",
                            "+faststart",
                            str(output_path),
                        ]
                        encoder = subprocess.Popen(  # noqa: S603 - allowlisted ffmpeg, argv only, generated local paths
                            encoder_args,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    assert encoder.stdin is not None
                    encoder.stdin.write(np.ascontiguousarray(roi).tobytes())
                    processed += 1
                    sequence += 1
                    output_pts = pos_s
                    # Anchor to the source timebase. Advancing from each rounded decoded
                    # frame accumulates drift (e.g.3fps over10fps became2.5fps).
                    sample_slot = max(
                        sample_slot + 1, math.floor((pos_s - sample_origin) * sample_fps) + 1
                    )
                    next_pts = sample_origin + sample_slot / sample_fps
                    observation_writer.write(
                        json.dumps(
                            {
                                "record_type": "sample",
                                "schema_version": 1,
                                "source_video_id": str(recording.id),
                                "analysis_run_id": str(run.id),
                                "tenant_id": str(tenant_id),
                                "source_frame_index": decoded - 1,
                                "sample_sequence": sequence,
                                "pts_seconds": float(pos_s),
                                "observations": observation_rows,
                            },
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        + "\n"
                    )
                    if sequence % 100 == 0:
                        observation_writer.flush()
                    if observation_writer.tell() > MAX_ARTIFACT_BYTES:
                        raise ValueError("observation_artifact_size_limit")
                    if (
                        processed % 10 == 0
                        and output_path.exists()
                        and output_path.stat().st_size > 1024**3
                    ):
                        raise ValueError("output_size_limit")
                    ok_jpeg, encoded = cv2.imencode(".jpg", roi, [cv2.IMWRITE_JPEG_QUALITY, 78])
                    if ok_jpeg:
                        with preview_lock:
                            self._previews[key] = (
                                encoded.tobytes(),
                                sequence,
                                int(pos_s * 1000),
                                time.monotonic(),
                            )
                    now_wall = time.perf_counter()
                    if now_wall - last_db_update >= 0.8:
                        run.processed_frames = processed
                        run.decoded_frames = decoded
                        run.skipped_frames = skipped
                        run.latest_media_pts_ms = int(pos_s * 1000)
                        run.inference_fps = processed / max(0.001, now_wall - start_wall)
                        run.preview_sequence = sequence
                        run.counts = {
                            "detection_observations_by_class": dict(class_detections),
                            "unique_track_ids_by_class": dict(tracks_by_class),
                            "line_crossings": dict(crossings) if line else None,
                            "line_crossing_status": "configured_unvalidated_geometry"
                            if line
                            else "not_configured",
                            "source_nominal_fps": nominal_fps,
                            "output_mode": "sampled_timeline",
                            "output_fps": sample_fps,
                            "model_provider": detector.provider,
                            "model_provider_fallback": detector.provider_fallback_reason,
                            "mean_model_latency_ms": float(np.mean(inference_ms))
                            if inference_ms
                            else 0,
                        }
                        db.commit()
                        last_db_update = now_wall
            capture.release()
            capture = None
            if encoder:
                if encoder.stdin:
                    encoder.stdin.close()
                encoder.wait(timeout=30)
                if encoder.returncode != 0:
                    raise ValueError("video_encode_failed")
            if processed == 0 or not output_path.exists() or output_path.stat().st_size == 0:
                raise ValueError("no_output_frames")
            if output_path.stat().st_size > 1024 * 1024 * 1024:
                raise ValueError("output_size_limit")
            probe = subprocess.run(  # noqa: S603 - allowlisted ffprobe and generated local path
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,width,height,avg_frame_rate,duration",
                    "-of",
                    "json",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            out_info = json.loads(probe.stdout)["streams"][0]
            if out_info.get("codec_name") != "h264":
                raise ValueError("output_codec_invalid")
            if cancel.is_set():
                raise InterruptedError("cancelled")
            observation_writer.flush()
            os.fsync(observation_writer.fileno())
            observation_writer.close()
            observation_writer = None
            observation_digest = hashlib.sha256()
            with observation_path.open("rb") as observation_source:
                for block in iter(lambda: observation_source.read(1024 * 1024), b""):
                    observation_digest.update(block)
            observation_key = storage_key(tenant_id, run_id, "observations")
            observation_size = encrypt_file(keyring, run_id, observation_path, observation_key)
            output_key = storage_key(tenant_id, run_id, "output")
            output_size = encrypt_file(keyring, run_id, output_path, output_key)
            if cancel.is_set():
                raise InterruptedError("cancelled")
            elapsed = time.perf_counter() - start_wall
            run.status, run.ended_at = "completed", _now()
            run.processed_frames, run.decoded_frames, run.skipped_frames = (
                processed,
                decoded,
                skipped,
            )
            run.latest_media_pts_ms = int(output_pts * 1000)
            run.inference_fps = processed / max(0.001, elapsed)
            run.preview_sequence = sequence
            run.output_storage_key = output_key
            run.observation_storage_key = observation_key
            run.observation_sha256 = observation_digest.hexdigest()
            run.observation_size_bytes = observation_size
            run.observation_count = observation_count
            run.observation_schema_version = 1
            run.observations_complete = True
            run.output_size_bytes = output_size
            run.output_duration_ms = int(float(out_info["duration"]) * 1000)
            run.output_fps = sample_fps
            run.counts = {
                "detection_observations_by_class": dict(class_detections),
                "unique_track_ids_by_class": dict(tracks_by_class),
                "line_crossings": dict(crossings) if line else None,
                "line_crossings_by_class_direction": dict(crossings_by_class) if line else None,
                "flow_events": flow_events,
                "candidate_events": event_candidates,
                "event_rule_summary": {
                    "stationary": {
                        "enabled": stationary_enabled,
                        "threshold_s": stationary_duration,
                        "count": sum(e["type"] == "possible_obstruction" for e in event_candidates),
                        "status": "evaluated" if stationary_enabled else "disabled",
                    },
                    "queue": {
                        "enabled": bool(rules.get("queue_enabled", True)),
                        "threshold_s": queue_duration,
                        "minimum_vehicles": queue_min,
                        "count": sum(e["type"] == "traffic_queue" for e in event_candidates),
                        "status": "evaluated"
                        if queue_enabled
                        else (
                            "disabled"
                            if not rules.get("queue_enabled", True)
                            else "unsupported_sampling_below_1fps"
                        ),
                    },
                    "crossing": {
                        "enabled": bool(line),
                        "count": len(flow_events),
                        "priority": "flow_analytics_only",
                    },
                    "unsupported": {
                        "speed_distance_ttc_signal": (
                            "Requires calibrated scene geometry and validated signal/source timing."
                        )
                    },
                },
                "line_crossing_status": "configured_unvalidated_geometry"
                if line
                else "not_configured",
                "source_nominal_fps": nominal_fps,
                "output_mode": "sampled_timeline",
                "output_fps": sample_fps,
                "output_audio": "not_preserved",
                "model_provider": detector.provider,
                "model_provider_fallback": detector.provider_fallback_reason,
                "mean_model_latency_ms": float(np.mean(inference_ms)) if inference_ms else 0,
                "p95_model_latency_ms": float(np.percentile(inference_ms, 95))
                if inference_ms
                else 0,
                "track_count_note": (
                    "Unique tracker IDs are observed tracks, not ground-truth unique vehicles."
                ),
            }
            run.warnings = [
                *(run.warnings or []),
                "No counting line configured; line crossings are not measured."
                if not line
                else (
                    "Line placement uses screen pixels; crossing counts require operator review "
                    "and are not field-calibrated."
                ),
                ("Privacy redaction is heuristic; missed faces/plates may remain visible."),
            ]
            db.commit()
            output_committed = True
            observation_committed = True
            with self._lock:
                self._previews.pop(key, None)
        except InterruptedError:
            db.rollback()
            current = db.get(AnalysisRun, run_id)
            if current:
                current.status, current.ended_at = "cancelled", _now()
                db.commit()
        except Exception as exc:
            db.rollback()
            current = db.get(AnalysisRun, run_id)
            if current:
                current.status = "failed"
                current.error_code = (
                    str(exc)
                    if isinstance(exc, ValueError) and str(exc).isidentifier()
                    else type(exc).__name__.lower()
                )
                current.ended_at = _now()
                db.commit()
            with self._lock:
                self._previews.pop(key, None)
        finally:
            with self._lock:
                self._previews.pop(key, None)
            if capture:
                capture.release()
            if encoder:
                try:
                    if encoder.stdin and not encoder.stdin.closed:
                        encoder.stdin.close()
                    if encoder.poll() is None:
                        encoder.terminate()
                        encoder.wait(timeout=3)
                except Exception:
                    encoder.kill()
            if observation_writer:
                observation_writer.close()
            if temp_context and temp_entered:
                temp_context.__exit__(None, None, None)
            if output_key and not output_committed:
                storage_path(output_key).unlink(missing_ok=True)
            if observation_key and not observation_committed:
                storage_path(observation_key).unlink(missing_ok=True)
            try:
                if "work_dir" in locals():
                    shutil.rmtree(work_dir, ignore_errors=True)
            except OSError:
                pass
            db.close()


offline_analysis_manager = OfflineAnalysisManager()
