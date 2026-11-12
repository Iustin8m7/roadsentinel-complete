"""Process a camera video: detect + track + measure speed, apply rules, store events with evidence.

Usage: python -m roadsentinel.pipeline cameras/demo-highway.yaml [--model models/yolox_s.onnx] [--no-wandb]
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import threading
import time
from collections import Counter, deque
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import yaml

from . import media, sink, tracking, vlm
from .alerts import AlertGate
from .analytics import CountLine, TrafficAnalytics
from .detector import COCO, Detections, YoloXOnnx, create_tracker, to_supervision
from .geometry import Calibration, Zone
from .live import BoundedWorker, LiveReader
from .models import resolve_for_pipeline
from .rates import RateTracker
from .redaction import blur_people, blur_region, blur_vehicle_plate, redact_frame, redaction_mode  # noqa: F401
from .rules import RuleEngine, rule_capabilities  # noqa: F401
from .sources import SourceHealth, SourceSpec, open_capture

# Debris candidates for the object_on_roadway rule (COCO: backpack, handbag, suitcase). Only
# detected when that rule is enabled for the camera; a generic detector misses most road debris.
OBJECT_COCO = {24: "object", 26: "object", 28: "object"}
PRIORITY_COLORS = {"critical": (40, 40, 230), "high": (0, 140, 255), "medium": (0, 210, 255), "info": (230, 180, 60)}
OUT_W = 1280
CLIP_PAD_S = 3.0


def load_camera(path, configuration=None):
    cfg = configuration if configuration is not None else yaml.safe_load(Path(path).read_text())
    cal = cfg.get("calibration")
    if cal is None:
        # Detection/tracking/preview do not require road-plane geometry. Speed rules must remain
        # unavailable until a camera-specific calibration is supplied.
        calib = None
    elif "points" in cal:  # measured reference points: [[px, py, X_m, Y_m], ...] (docs/CALIBRATION.md)
        calib = Calibration.from_points(cal["points"])
    else:  # legacy: 4 pixel corners of a road rectangle of known size
        calib = Calibration(cal["source"], cal["target_width_m"], cal["target_length_m"])
    return cfg, calib, [Zone(z) for z in cfg["zones"]]


def touches_edge(box, w, h):
    x1, _, x2, y2 = box
    margin = 0.02 * h  # boxes start shrinking a little before they hit the edge
    return x1 < margin or x2 > w - margin or y2 > h - margin


def drop_occupants(objs):
    """Drop person boxes in a vehicle cabin while retaining riders exposed at its rear."""
    vehicles = [b for _, c, _, b in objs if c in {"car", "truck", "bus", "motorcycle"}]

    def cabin_occupant(p, v):
        ix = max(0, min(p[2], v[2]) - max(p[0], v[0]))
        iy = max(0, min(p[3], v[3]) - max(p[1], v[1]))
        person_area = max(1e-6, (p[2] - p[0]) * (p[3] - p[1]))
        if ix * iy / person_area <= 0.5:
            return False
        # A human box contained in the upper cabin area is likely a driver/passenger.
        # Exposed riders extend below the body/cabin region and must remain eligible for
        # pedestrian-in-carriageway rules, even when the vehicle detector overlaps them.
        vx1, vy1, vx2, vy2 = v
        vw, vh = max(1.0, vx2 - vx1), max(1.0, vy2 - vy1)
        cy = (p[1] + p[3]) / 2
        contained = p[0] >= vx1 - 0.03 * vw and p[2] <= vx2 + 0.03 * vw
        upper_cabin = vy1 + 0.05 * vh <= cy <= vy1 + 0.62 * vh
        return contained and upper_cabin

    return [o for o in objs if o[1] != "person" or not any(cabin_occupant(o[3], v) for v in vehicles)]


def tracking_detections(prediction, *, allow_person=False):
    """Keep incidental person boxes out of ByteTrack unless an enabled rule needs them.

    The original prediction remains available for redaction before this privacy filter.
    """
    if allow_person or not np.any(prediction.class_id == 0):
        return prediction
    keep = prediction.class_id != 0
    return Detections(
        xyxy=prediction.xyxy[keep],
        confidence=prediction.confidence[keep],
        class_id=prediction.class_id[keep],
        latency_ms=prediction.latency_ms,
    )


def draw(frame, zones, objs, engine, flash, confidence_by_track=None):
    overlay = frame.copy()
    for z in zones:
        color = (60, 60, 230) if z.kind == "emergency_lane" else (200, 160, 40)
        cv2.fillPoly(overlay, [z.polygon], color)
    cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
    # Counting lines are rendered by the caller after analytics has been configured.
    scale = frame.shape[1] / 1920
    th = max(2, int(3 * scale))
    for tid, cls, _, (x1, y1, x2, y2) in objs:
        tr = engine.tracks.get(tid)
        color = flash.get(tid, (90, 220, 90))
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, th)
        confidence = (confidence_by_track or {}).get(tid)
        label = f"#{tid} {cls}" + (f" {confidence:.2f}" if confidence is not None else "")
        if tr and tr.speed_kmh() is not None and cls != "person":
            label += f" {tr.speed_kmh():.0f} km/h"
        cv2.putText(frame, label, (int(x1), int(y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.9 * scale, color, th)


class ClipWriter:
    """Write annotated frames with ffmpeg when present, else the bundled OpenCV video backend."""

    def __init__(self, path, w, h, fps):
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{w}x{h}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ]
        try:
            self.p = subprocess.Popen(command, stdin=subprocess.PIPE)
            self.writer = None
        except FileNotFoundError:
            self.p = None
            self.writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            if not self.writer.isOpened():
                raise RuntimeError("ffmpeg is unavailable and OpenCV could not open an MP4 writer")

    def write(self, frame):
        if self.writer is not None:
            self.writer.write(frame)
        else:
            self.p.stdin.write(frame.tobytes())

    def close(self):
        if self.writer is not None:
            self.writer.release()
        else:
            self.p.stdin.close()
            code = self.p.wait()
            if code:
                raise RuntimeError(f"ffmpeg failed to encode clip (exit {code})")


def open_stream(url):
    """HLS: start at the newest segment instead of three back (less delay behind real time)."""
    os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "live_start_index;-1;rw_timeout;15000000")
    return cv2.VideoCapture(url)


def clip_fps(frames_t, fallback):
    """Playback rate of a clip from the stream times of its frames (live streams drop frames)."""
    span = frames_t[-1] - frames_t[0] if len(frames_t) > 1 else 0
    return (len(frames_t) - 1) / span if span > 0 else fallback


def write_clip(path, frames, fps):
    """Event clip from already-processed frames (people blurred, boxes drawn), never from the raw source."""
    frames = [frame for frame in frames if frame is not None and frame.size]
    if not frames:
        raise RuntimeError("event clip has no decodable source frames")
    w = ClipWriter(path, frames[0].shape[1], frames[0].shape[0], fps)
    for f in frames:
        w.write(f)
    w.close()
    if not path.is_file() or path.stat().st_size < 1024:
        raise RuntimeError("event clip writer produced no usable media")
    check = cv2.VideoCapture(str(path))
    try:
        ok, decoded = check.read()
        if not check.isOpened() or not ok or decoded is None:
            raise RuntimeError("event clip cannot be decoded after writing")
    finally:
        check.release()


def pick_model(cfg, model_name=None):
    """Weights for this camera (see models.resolve_for_pipeline): --model, else the camera's own
    model, else an explicit stock fallback. Returns the path; identity goes into each event."""
    return resolve_for_pipeline(cfg, model_name)[0]


def _peak_rss_mb():
    """Return Linux process high-water RSS in MiB, or None if unavailable."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError):
        return None


def event_idempotency_key(camera_id, event):
    """Stable identity for retries/restarts of the same source-time rule observation.

    Wall-clock filenames are unsuitable for idempotency: a retry after a worker restart would
    otherwise create a second alert for the same recorded event. Use source PTS and the rule's
    camera-scoped identity; do not include transient upload state or generated evidence paths.
    """
    details = event.get("details") or {}
    identity = {
        "camera_id": str(camera_id),
        "source_time_s": round(float(event["video_t"]), 3),
        "type": str(event["type"]),
        "track_id": int(event["track_id"]) if event.get("track_id") is not None else None,
        "object_class": event.get("object_class"),
        "zone": details.get("zone"),
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "evt-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]


def _estimate_capture_fps(cap, reported_fps):
    """Work around malformed high OpenCV FPS metadata when local PTS cadence is usable."""
    if not 240 < reported_fps < float("inf"):
        return reported_fps
    positions = []
    for _ in range(8):
        ok, _ = cap.read()
        if not ok:
            break
        ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if np.isfinite(ms):
            positions.append(ms)
    if len(positions) >= 3 and positions[-1] > positions[0]:
        estimated = (len(positions) - 1) * 1000 / (positions[-1] - positions[0])
        if 0.1 <= estimated <= 240:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return estimated
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    return reported_fps


def run(
    camera_path, model_name=None, imgsz=640, max_seconds=None, use_wandb=None, live=False, loop=False, frame_stride=None
):
    """Batch mode: process the whole video, replace this camera's events.
    Live mode: play at real-time speed, timestamp events with the current time and send each one
    as soon as its clip is complete (append-only, like a real camera feed)."""
    redaction = redaction_mode()
    cfg, calib, zones = load_camera(camera_path)
    out = sink.from_env()
    control = None
    if isinstance(out, sink.RemoteSink):
        from .remote_config import ManagedCamera
        control = ManagedCamera(out, cfg)
        cfg, calib, zones = load_camera(camera_path, control.apply(cfg))
        out.control = control
    source = SourceSpec.from_camera(cfg)
    if source.live_capture and not live:
        raise ValueError("network and optical-device sources may only run in supervised --live mode")
    model_name, model_id, model_sha = resolve_for_pipeline(cfg, model_name)
    if imgsz != 640:
        raise ValueError("the selected YOLOX ONNX artifact has a fixed 640x640 input")
    print(f"model: {model_id} ({model_name})")
    detector = YoloXOnnx(model_name, input_size=imgsz)
    print(f"inference provider: {detector.provider}")
    if detector.provider_fallback_reason:
        print(f"inference provider fallback: {detector.provider_fallback_reason}")
    cam_id = cfg["id"]
    work_dir = Path(os.environ.get("RS_PIPELINE_WORK_DIR", "."))
    folder = work_dir / "data/media" / cam_id
    folder.mkdir(parents=True, exist_ok=True)
    stream = live and source.live_capture
    if not live:
        for old in folder.glob("*"):
            old.unlink()
        out.clear_camera(cam_id)

    cap = open_capture(source)
    fps = float(cfg.get("source_fps", 0)) if source.replay else cap.get(cv2.CAP_PROP_FPS)
    fps = fps or float(cfg.get("source_fps", 1 / source.poll_interval_s if source.mode == "image" else 25))
    if source.kind == "file" and source.mode == "video" and fps > 240:
        fps = _estimate_capture_fps(cap, fps)
    source_fps = fps
    frame_stride = (
        int(cfg.get("frame_stride", 1) if frame_stride is None else frame_stride)
        if source.kind == "file" and source.mode == "video"
        else 1
    )
    if not 1 <= frame_stride <= 60:
        raise ValueError("frame_stride must be between 1 and 60")
    analysis_fps = source_fps / frame_stride
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if W <= 0 or H <= 0:
        # Image endpoints do not expose metadata until their first frame. A conservative fallback
        # is used only for buffer sizing; measured dimensions replace it after the first read.
        W, H = int(cfg.get("width", OUT_W)), int(cfg.get("height", OUT_W * 9 / 16))
    reader = None
    if stream:
        cap.release()
        stall_timeout = float(cfg.get("stall_timeout_s", 45))
        if source.mode == "image":
            stall_timeout = max(stall_timeout, source.poll_interval_s * 2 + source.timeout_s)
        reader = LiveReader(lambda: open_capture(source), fps, stall_timeout_s=stall_timeout)
    out_h = int(H * OUT_W / W) // 2 * 2
    start = datetime.fromisoformat(cfg["start_time"])

    device = detector.provider
    engine = RuleEngine(zones, cfg["thresholds"], cfg.get("rules"))
    count_lines = [CountLine.from_config(v) for v in cfg.get("counting_lines", [])]
    analytics = TrafficAnalytics(count_lines, cfg.get("traffic_window_s", 60))
    source_health = SourceHealth(source.kind, source.transport)
    names = {**COCO, **(OBJECT_COCO if "object_on_roadway" in engine.enabled else {})}
    gate = AlertGate(cfg.get("alerts"))
    rate = RateTracker()
    tracker = create_tracker(analysis_fps)
    conf = float(cfg.get("model_confidence", 0.3))
    iou = float(cfg.get("model_iou_threshold", 0.45))
    if not 0.01 <= conf <= 0.99 or not 0.05 <= iou <= 0.95:
        raise ValueError("model_confidence/model_iou_threshold outside safe bounds")
    inference_ms = deque(maxlen=10000)
    detection_log = None
    log_path = None
    if os.environ.get("RS_SAVE_DETECTIONS") == "1":
        log_path = work_dir / "data/vision" / f"{cam_id}-{int(time.time())}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        detection_log = open(log_path, "w", encoding="utf-8")  # noqa: SIM115 - closed on pipeline shutdown
    stop_requested = threading.Event()
    if live and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, lambda *_: stop_requested.set())
        signal.signal(signal.SIGINT, lambda *_: stop_requested.set())
    writer = None if live else ClipWriter(folder / "annotated.mp4", OUT_W, out_h, analysis_fps)
    run_log = None if live else tracking.start(cfg, model_name, imgsz, enabled=use_wandb)

    # Recent processed frames as JPEG bytes (~100 KB each), enough for a ±3 s clip.
    recent = deque(maxlen=max(2, int(analysis_fps * (2 * CLIP_PAD_S + 1))))

    # Live: uploads run on one worker thread, so a slow network never stalls the frame loop.
    # Bounded queue + retries: memory stays small (JPEG bytes are decoded only inside the worker),
    # a slow network drops the oldest non-critical job (counted) instead of growing without limit.
    uploads = BoundedWorker(maxsize=8, retries=3) if live else None
    preview_uploads = (
        BoundedWorker(maxsize=1, retries=0, log=lambda _message: None)
        if live and callable(getattr(out, "preview", None))
        else None
    )

    def publish(e):
        window = [(ft, b) for ft, b in recent if abs(ft - e["video_t"]) <= CLIP_PAD_S]
        clip_rate = clip_fps([ft for ft, _ in window], fps)
        if uploads:
            queued = uploads.submit(
                lambda: store_event(e, window, clip_rate), critical=e["priority"] == "critical"
            )
            if not queued:
                print(f"  event upload queue rejected {e['event_key']} ({e['type']})")
            return queued
        else:
            store_event(e, window, clip_rate)
            return True

    def store_event(e, window, clip_rate):
        e.setdefault('details', {})['origin'] = 'local_replay' if source.replay or source.kind == 'file' else 'live_camera'
        if control:
            control.check()
            control.stamp(e)
        frames = [cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR) for _, b in window]
        clip = folder / f"{e['stem']}.mp4"
        write_clip(clip, frames, clip_rate)
        e.update(camera_id=cam_id, camera_name=cfg["name"], location=cfg.get("location", ""))
        if source.kind == "file":
            e["occurred_at"] = (start + timedelta(seconds=e["video_t"])).isoformat()
        verdict = vlm.check({**e, "keyframe": media.key_for(e["keyframe_path"]), "clip": media.key_for(clip)})
        if "vlm" in verdict:
            e["details"]["vlm"] = verdict.pop("vlm")
        e.update(verdict)
        e["ingest_id"] = out.add_event(e, e["keyframe_path"], clip)
        published.append(e)
        print(
            f"  event upload accepted id={e['ingest_id']} key={e['event_key']} "
            f"type={e['type']} track={e.get('track_id')} source_t={e['video_t']:.3f}s"
        )

    stop = threading.Event()

    progress = {"at": time.time(), "caps": None}

    def heartbeat():
        """Tells the dashboard this camera is being processed right now. It is only sent while the
        main loop really processed a frame recently, so a hung stream or detector stops showing LIVE."""
        while not stop.wait(5):
            idle = time.time() - progress["at"]
            if idle > cfg.get("heartbeat_max_idle_s", 120):
                print(f"  no frame processed for {idle:.0f} s: heartbeat withheld")
                continue
            try:
                fps_now = rate.fps
                status = (
                    None
                    if progress["caps"] is None
                    else {
                        "fps": round(fps_now or 0.0, 3),
                        "processing_fps": round(n / max(0.001, time.time() - wall0), 3),
                        "rules": progress["caps"],
                        "source": source_health.snapshot(),
                        "traffic": analytics.snapshot(time.monotonic()),
                        "detections": det_total,
                        "unique_tracks": len(engine.tracks),
                        "tracks_by_class": dict(engine.class_counts),
                        "inference_latency_ms_p50": round(float(np.percentile(inference_ms, 50)), 2)
                        if inference_ms
                        else None,
                        "inference_latency_ms_p95": round(float(np.percentile(inference_ms, 95)), 2)
                        if inference_ms
                        else None,
                        "inference_latency_ms_p99": round(float(np.percentile(inference_ms, 99)), 2)
                        if inference_ms
                        else None,
                        "process_peak_rss_mb": _peak_rss_mb(),
                        "model": "YOLOX-S ONNX / Supervision ByteTrack",
                        "model_sha256": model_sha,
                        "inference_provider": detector.provider,
                        "provider_fallback_reason": detector.provider_fallback_reason,
                    }
                )
                status["source"]["replay"] = bool(source.replay or live and source.kind == "file")
                if reader:
                    status["source"]["reconnects"] = reader.reconnects
                    source_health.failures = reader.reconnects
                out.heartbeat(cam_id, status)
            except Exception as err:  # noqa: BLE001
                print(f"  heartbeat failed: {err}")

    if live:
        threading.Thread(target=heartbeat, daemon=True).start()

    waiting, published, flash = [], [], {}
    n, t0, det_total, speeds = 0, time.time(), 0, []
    wall0 = time.time()
    t = 0.0
    previous_media_t = -1.0
    last_managed_frame = 0.0
    control_stopped = False
    while True:
        if control:
            try:
                control.check()
            except Exception as error:  # noqa: BLE001 - capture must stop on any control failure
                # Fail closed on permission/lease changes or control-plane reachability loss.
                print(f'  control stopped capture ({type(error).__name__})')
                control_stopped = True
                break
        if stop_requested.is_set():
            print("  stop requested: finishing")
            break
        if stream:
            frame, t = reader.read(timeout=5)
            if frame is None:  # no new frame (stalled or reconnecting): the watchdog restarts the reader
                continue
            if max_seconds and t >= max_seconds:
                break
        else:
            if frame_stride > 1:
                for _ in range(frame_stride - 1):
                    if not cap.grab():
                        break
            ok, frame = cap.read()
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            media_t = pos_ms / 1000 if np.isfinite(pos_ms) and pos_ms > previous_media_t * 1000 else -1
            t = media_t if media_t >= 0 else n / analysis_fps
            previous_media_t = t
        if not stream and not ok and live and loop:
            # Restart the feed: new tracker state, same rules config.
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            tracker = create_tracker(analysis_fps)
            engine = RuleEngine(zones, cfg["thresholds"], cfg.get("rules"))
            n, wall0, flash = 0, time.time(), {}
            previous_media_t = -1.0
            recent.clear()  # timestamps restart at 0
            continue
        if not stream and (not ok or (max_seconds and t >= max_seconds)):
            break
        source_health.frame(frame)
        if stream and reader:
            source_health.reconnects = reader.reconnects
            source_health.failures = reader.reconnects
        if live and not stream:  # don't run ahead of the real clock (a stream paces itself)
            time.sleep(max(0.0, wall0 + t - time.time()))
        rate.add(t)
        if rate.fps and (n < 5 or n % 10 == 0):
            progress["caps"] = {
                r: {"supported": c["supported"], "min_fps": c["min_fps"], "reason": c["reason"]}
                for r, c in engine.set_rate(rate.fps).items()
            }
        prediction = detector.predict(frame, classes=set(names), confidence_threshold=conf, iou_threshold=iou)
        inference_ms.append(prediction.latency_ms)
        if control and control.managed:
            reference = control.desired['config']['reference_frame']
            if (frame.shape[1], frame.shape[0]) != (reference['width'], reference['height']):
                raise RuntimeError('Source dimensions differ from approved reference frame')
            if not control.acknowledged:
                control.acknowledge(model_id, model_sha)
            now_frame = time.monotonic()
            if now_frame - last_managed_frame < 1 / cfg['managed_target_fps']:
                continue
            last_managed_frame = now_frame
        # Redact all detector candidates, even if ByteTrack does not yet assign an ID.
        redact_detections = [(names[int(c)], tuple(b)) for b, c in zip(prediction.xyxy, prediction.class_id)]
        redact_frame(frame, redact_detections, redaction)
        tracked_prediction = tracking_detections(
            prediction, allow_person="pedestrian_on_road" in engine.enabled
        )
        tracked = tracker.update_with_detections(to_supervision(tracked_prediction))
        if control:
            control.has_frames = True
            control.last_frame_at = time.monotonic()
        objs = []
        confidence_by_track = {}
        if tracked.tracker_id is not None:
            for (x1, y1, x2, y2), tid, c, score in zip(
                tracked.xyxy, tracked.tracker_id, tracked.class_id, tracked.confidence
            ):
                foot = ((x1 + x2) / 2, y2)
                if foot[1] < cfg.get("min_y", 0):
                    continue
                tid = int(tid)
                objs.append((tid, names[int(c)], foot, (float(x1), float(y1), float(x2), float(y2))))
                confidence_by_track[tid] = float(score)
        objs = drop_occupants(objs)
        analytics.update(
            t, [(int(tid), cls, foot) for tid, cls, foot, _ in objs if cls in {"car", "truck", "bus", "motorcycle"}]
        )
        det_total += len(objs)
        if detection_log and tracked.tracker_id is not None:
            for box, score, cls, tid in zip(tracked.xyxy, tracked.confidence, tracked.class_id, tracked.tracker_id):
                detection_log.write(
                    json.dumps(
                        {
                            "timestamp_s": round(float(t), 3),
                            "track_id": int(tid),
                            "class": names[int(cls)],
                            "confidence": round(float(score), 5),
                            "bbox_xyxy": [round(float(v), 2) for v in box],
                        }
                    )
                    + "\n"
                )

        # Boxes cut by the frame edge give a false foot point, so they are drawn but not measured.
        events = gate.filter(t, engine.update(t, [o for o in objs if not touches_edge(o[3], W, H)], calib))
        progress["at"] = time.time()
        for e in events:
            if e["track_id"] is not None:
                flash[e["track_id"]] = PRIORITY_COLORS[e["priority"]]
        draw(frame, zones, objs, engine, flash, confidence_by_track)
        for line in count_lines:
            cv2.line(
                frame,
                tuple(map(int, line.start)),
                tuple(map(int, line.end)),
                (255, 190, 40),
                max(2, int(frame.shape[1] / 800)),
            )
            midpoint = ((int(line.start[0]) + int(line.end[0])) // 2, (int(line.start[1]) + int(line.end[1])) // 2)
            cv2.putText(frame, line.id, midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 190, 40), 2)
        small = cv2.resize(frame, (OUT_W, out_h))
        source_timestamp = reader.source_timestamp if reader is not None else None
        captured_at = source_timestamp or datetime.now(UTC)
        cv2.putText(
            small,
            captured_at.isoformat(timespec="milliseconds"),
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )
        if cfg.get("synthetic_test") is True:
            cv2.putText(
                small, "SYNTHETIC TEST - review only", (12, out_h - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2,
            )
        preview_jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 78])[1].tobytes()
        recent.append((t, preview_jpeg))
        if preview_uploads:
            preview_uploads.submit(
                lambda data=preview_jpeg, ts=captured_at, seq=n: out.preview(cam_id, data, ts, seq)
            )
        if writer:
            writer.write(small)

        for e in events:
            e["redaction"] = redaction  # full | heads_only | off: reported as it is
            e.setdefault("details", {})["redaction"] = e["redaction"]
            if cfg.get("synthetic_test") is True:
                e["details"]["synthetic"] = True
                e["details"]["test_disclosure"] = str(
                    cfg.get("test_disclosure", "Synthetic source or rule geometry; human review only")
                )[:300]
            e["details"]["model_id"] = model_id  # which model raised this alert (audit, rollback)
            if model_sha:
                e["details"]["model_sha256"] = model_sha
            if e.get("track_id") in confidence_by_track:
                e["details"]["detection_confidence"] = round(
                    confidence_by_track[e["track_id"]], 5
                )
            provenance = cfg.get("source_provenance")
            if isinstance(provenance, dict):
                e["details"]["source_provenance"] = {
                    key: provenance[key]
                    for key in ("title", "url", "author", "license", "sha256")
                    if provenance.get(key)
                }
            if e.get("speed_kmh") is not None:  # speeds are indicative until a calibration is validated
                e["details"]["speed_calibration"] = (
                    "validated" if cfg["calibration"].get("validated") else "unvalidated"
                )
            e["video_t"] = round(t, 3)
            e["occurred_at"] = datetime.now().isoformat(timespec="seconds")
            # Stable across upload retries and worker restarts at the same source PTS.
            e["event_key"] = event_idempotency_key(cam_id, e)
            e["stem"] = f"event_{e['event_key'][4:20]}_{e['type']}"
            kf = small.copy()
            if e["bbox"]:
                s = OUT_W / W
                x1, y1, x2, y2 = (int(v * s) for v in e["bbox"])
                cv2.rectangle(kf, (x1 - 6, y1 - 6), (x2 + 6, y2 + 6), PRIORITY_COLORS[e["priority"]], 4)
            cv2.putText(kf, f"{e['label']} | t={t:.1f}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            e["keyframe_path"] = folder / f"{e['stem']}.jpg"
            if not cv2.imwrite(str(e["keyframe_path"]), kf, [cv2.IMWRITE_JPEG_QUALITY, 80]):
                print(f"  event evidence failed: keyframe write rejected for {e['event_key']}")
                continue
            if not e["keyframe_path"].is_file() or e["keyframe_path"].stat().st_size < 256:
                print(f"  event evidence failed: keyframe is empty for {e['event_key']}")
                continue
            waiting.append(e)
            print(f"[{t:6.1f}s] {e['priority'].upper():8} {e['label']}: {e['rule']}")

        # Send events whose clip window (±3 s) is already in the video.
        while waiting and waiting[0]["video_t"] + CLIP_PAD_S <= t:
            publish(waiting.pop(0))
        n += 1
        if n % 100 == 0:
            print(f"  frame {n}  ({n / (time.time() - t0):.1f} fps)")
    cap.release()
    for e in ([] if control_stopped else waiting):
        publish(e)
    stop.set()
    if control_stopped:
        # Permission/revision/lease loss: retain accepted records, cancel unaccepted work.
        # Counting discarded jobs makes this fail-closed transition visible.
        if uploads:
            uploads.shutdown(wait=False, cancel_pending=True)
        if preview_uploads:
            preview_uploads.shutdown(wait=False, cancel_pending=True)
    if reader:
        reader.close()
    if uploads:
        uploads.shutdown(wait=True, timeout=6 if control_stopped else None)
        print(f"  uploads: {uploads.stats()}  suppressed by the alert gate: {gate.stats()}")
    if preview_uploads:
        preview_uploads.shutdown(wait=True, timeout=6)
        print(f"  annotated previews: {preview_uploads.stats()}")
    if control:
        control.release()
    if writer:
        writer.close()
        out.add_camera_video(cam_id, folder / "annotated.mp4")
    if detection_log:
        detection_log.close()

    for tr in engine.tracks.values():
        speeds += [s for _, s in tr.speeds]
    stats = {
        "frames": n,
        "video_seconds": round(t, 1),
        "processing_fps": round(n / (time.time() - t0), 2),
        "detections": det_total,
        "unique_tracks": len(engine.tracks),
        "events": len(published),
        "tracks_by_class": dict(engine.class_counts),
        "events_by_type": dict(Counter(e["type"] for e in published)),
        "median_vehicle_speed_kmh": round(float(np.median(speeds)), 1) if speeds else None,
        "traffic": analytics.snapshot(t),
        "source": source_health.snapshot(),
        "detector": "YOLOX-S ONNX / Supervision ByteTrack",
        "model_sha256": model_sha,
        "device": device,
        "inference_latency_ms_p50": round(float(np.percentile(inference_ms, 50)), 2) if inference_ms else None,
        "inference_latency_ms_p95": round(float(np.percentile(inference_ms, 95)), 2) if inference_ms else None,
        "inference_latency_ms_p99": round(float(np.percentile(inference_ms, 99)), 2) if inference_ms else None,
        "process_peak_rss_mb": _peak_rss_mb(),
        "detection_log": str(log_path) if log_path else None,
    }
    for e in published:
        e["keyframe"] = str(e["keyframe_path"])
    tracking.finish(run_log, stats, published, speeds, folder / "annotated.mp4")
    print("\nRezumat:", stats)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("camera")
    ap.add_argument("--model", help="local ONNX weights (default: camera model or models/yolox_s.onnx)")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument(
        "--frame-stride", type=int, help="local video: analyze every Nth frame; timestamps remain source PTS"
    )
    ap.add_argument("--max-seconds", type=float)
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--live", action="store_true", help="real-time playback, events sent as they happen")
    ap.add_argument("--loop", action="store_true", help="with --live: replay the video forever")
    a = ap.parse_args()
    run(
        a.camera,
        a.model,
        a.imgsz,
        a.max_seconds,
        use_wandb=False if a.no_wandb else None,
        live=a.live,
        loop=a.loop,
        frame_stride=a.frame_stride,
    )


if __name__ == "__main__":
    main()
