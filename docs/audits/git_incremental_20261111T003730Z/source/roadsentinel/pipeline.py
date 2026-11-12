"""Process a camera video: detect + track + measure speed, apply rules, store events with evidence.

Usage: python -m roadsentinel.pipeline cameras/demo-highway.yaml [--model yolo11s.pt] [--no-wandb]
"""
import argparse
import os
import subprocess
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from . import media, remote_config, runtime, sink, tracking, vlm
from .geometry import Calibration, Zone
from .rules import RuleEngine

COCO = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
PRIORITY_COLORS = {"critical": (40, 40, 230), "high": (0, 140, 255), "medium": (0, 210, 255), "info": (230, 180, 60)}
OUT_W = 1280
CLIP_PAD_S = 3.0


def build_geometry(cfg):
    cal = cfg["calibration"]
    return Calibration(cal["source"], cal["target_width_m"], cal["target_length_m"]), [Zone(z) for z in cfg["zones"]]


def load_camera(path):
    cfg = yaml.safe_load(Path(path).read_text())
    return (cfg, *build_geometry(cfg))


def touches_edge(box, w, h):
    x1, _, x2, y2 = box
    margin = 0.02 * h  # boxes start shrinking a little before they hit the edge
    return x1 < margin or x2 > w - margin or y2 > h - margin


def keep_detector_boxes(model):
    """Remember each frame's boxes as the detector found them, before the tracker replaces them."""
    seen = {"boxes": np.empty((0, 4))}
    model.add_callback("on_predict_postprocess_end",
                       lambda predictor: seen.update(boxes=predictor.results[0].boxes.xyxy.cpu().numpy()))
    return seen


def detector_box(box, detected, min_iou=0.3):
    """The detector's box on the same vehicle as a tracker box; the tracker box when none overlaps enough.

    The tracker reports a smoothed box that trails a moving vehicle and swells in dense traffic
    (underpass clip: one tracker box in eight overlaps a detection by less than half). Rules keep
    the tracker's box, so the alerts do not change; the picture shows the detector's.
    """
    if len(detected) == 0:
        return tuple(box)
    x1, y1, x2, y2 = box
    iw = np.clip(np.minimum(x2, detected[:, 2]) - np.maximum(x1, detected[:, 0]), 0, None)
    ih = np.clip(np.minimum(y2, detected[:, 3]) - np.maximum(y1, detected[:, 1]), 0, None)
    areas = (detected[:, 2] - detected[:, 0]) * (detected[:, 3] - detected[:, 1])
    iou = iw * ih / ((x2 - x1) * (y2 - y1) + areas - iw * ih + 1e-9)
    best = int(iou.argmax())
    return tuple(float(v) for v in detected[best]) if iou[best] >= min_iou else tuple(box)


def drop_occupants(objs):
    """Drop 'person' detections that sit inside a vehicle box (drivers, passengers)."""
    vehicles = [b for _, c, _, b in objs if c != "person"]

    def inside(p, v):
        ix = max(0, min(p[2], v[2]) - max(p[0], v[0]))
        iy = max(0, min(p[3], v[3]) - max(p[1], v[1]))
        return ix * iy / max(1e-6, (p[2] - p[0]) * (p[3] - p[1])) > 0.5

    return [o for o in objs if o[1] != "person" or not any(inside(o[3], v) for v in vehicles)]


def redaction_mode():
    mode = os.environ.get("RS_REDACTION", "full")
    if mode not in {"full", "heads_only", "off"}:
        raise ValueError("RS_REDACTION must be full, heads_only or off")
    return mode


def blur_region(frame, box):
    """Blur a clipped region; reject inverted or wholly off-frame boxes."""
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(np.ceil(x2))), min(h, int(np.ceil(y2)))
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    kernel = max(3, int(max(roi.shape[:2]) * 0.3) | 1)
    frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (kernel, kernel), 0)


def blur_people(frame, boxes):
    """Blur every detected person's head, including vehicle occupants."""
    for x1, y1, x2, y2 in boxes:
        if x2 > x1 and y2 > y1:
            blur_region(frame, (x1, y1, x2, min(y2, y1 + max(4, (y2 - y1) / 3))))


def blur_vehicle_plate(frame, box):
    """Conservative bumper band, replaceable with a plate detector later."""
    x1, y1, x2, y2 = box
    if x2 > x1 and y2 > y1:
        blur_region(frame, (x1, y1 + 0.65 * (y2 - y1), x2, y2))


def redact_frame(frame, detections, mode=None):
    """Redact all detections before tracking filters or any evidence output.

    A vehicle at least 10% of the frame height is considered close enough
    for windshield redaction. Plate bands apply at every distance.
    This heuristic cannot cover missed detections or unusual plate positions.
    """
    mode = redaction_mode() if mode is None else mode
    if mode not in {"full", "heads_only", "off"}:
        raise ValueError("RS_REDACTION must be full, heads_only or off")
    if mode == "off":  # demo: no blurring at all
        return
    blur_people(frame, [box for cls, box in detections if cls == "person"])
    if mode == "full":
        for cls, box in detections:
            if cls in {"car", "truck", "bus", "motorcycle"}:
                blur_vehicle_plate(frame, box)
            x1, y1, x2, y2 = box
            if cls in {"car", "truck", "bus"} and y2 - y1 >= 0.1 * frame.shape[0]:
                blur_region(frame, (x1, y1, x2, y1 + 0.5 * (y2 - y1)))
    return frame


def draw(frame, zones, objs, engine, flash, shown=None):
    """Outline each tracked object; ``shown`` maps a track to the box to outline instead of its own.

    A vehicle an alert is about gets a heavy outline and a full label on a plate in the alert's
    colour. The others get a thin outline and only their speed, so dense traffic stays readable.
    """
    overlay = frame.copy()
    for z in zones:
        color = (60, 60, 230) if z.kind == "emergency_lane" else (200, 160, 40)
        cv2.fillPoly(overlay, [z.polygon], color)
    cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
    scale = frame.shape[1] / 1920
    th = max(2, int(3 * scale))
    font, dark = cv2.FONT_HERSHEY_SIMPLEX, (20, 20, 20)
    # Flagged vehicles last, so their outline and label sit on top of their neighbours'.
    for tid, cls, _, box in sorted(objs, key=lambda o: o[0] in flash):
        x1, y1, x2, y2 = (int(v) for v in (shown or {}).get(tid, box))
        tr = engine.tracks.get(tid)
        speed = f"{tr.speed_kmh():.0f} km/h" if tr and tr.speed_kmh() is not None and cls != "person" else ""
        if tid not in flash:
            color = (90, 220, 90)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, th, cv2.LINE_AA)
            if speed:  # dark edge under the text keeps it readable over road markings and headlights
                at = (x1, max(int(22 * scale), y1 - int(8 * scale)))
                cv2.putText(frame, speed, at, font, 0.75 * scale, dark, th + 3, cv2.LINE_AA)
                cv2.putText(frame, speed, at, font, 0.75 * scale, color, th, cv2.LINE_AA)
            continue
        color, label, size = flash[tid], f"#{tid} {cls} {speed}".rstrip(), 1.1 * scale
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, th * 2, cv2.LINE_AA)
        (tw, text_h), _ = cv2.getTextSize(label, font, size, th)
        pad = max(3, int(8 * scale))
        top = max(0, y1 - text_h - 2 * pad)
        cv2.rectangle(frame, (x1 - th, top), (x1 + tw + 2 * pad, top + text_h + 2 * pad), color, -1)
        cv2.putText(frame, label, (x1 + pad, top + pad + text_h), font, size, dark, th, cv2.LINE_AA)


class ClipWriter:
    """Pipes annotated frames into ffmpeg (H.264, browser-playable)."""

    def __init__(self, path, w, h, fps):
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)

    def write(self, frame):
        self.p.stdin.write(frame.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


class LiveReader:
    """Reads a network stream (HLS/RTSP) on its own thread and keeps only the newest frame,
    so slow processing drops frames instead of falling behind the feed. Reconnects on loss.

    ``acq`` (runtime.Acquisition) sets the reconnect pause, attempt limit and open/read timeouts;
    the default is the original fixed 2 s pause, forever. ``cadence`` caps the offered frame rate.
    ``dropped`` counts offered frames overwritten before the pipeline took them (frames skipped
    by the cadence are not drops); ``reconnects`` counts reconnect attempts; ``failed`` is set
    once the attempts are exhausted."""

    def __init__(self, url, fps, acq=None, cadence=None):
        self.url, self.fps = url, fps
        self.acq = acq or runtime.Acquisition()
        self.cadence = cadence or runtime.Cadence()
        self.cond = threading.Condition()
        self.frame, self.count, self.taken, self.offered = None, 0, 0, 0
        self.t = self.ts = None
        self.dropped = self.reconnects = 0
        self.failed = None
        threading.Thread(target=self._run, daemon=True).start()

    def _open(self):
        # HLS: start at the newest segment instead of three back (less delay behind real time).
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "live_start_index;-1")
        params = self.acq.capture_params()
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG, params) if params else cv2.VideoCapture(self.url)
        return cap, time.time(), self.count

    def _run(self):
        cap, t0, n0 = self._open()
        failures = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                cap.release()
                failures += 1
                limit = self.acq.max_reconnect_attempts
                if limit is not None and failures > limit:
                    print("  stream lost, reconnect attempts exhausted")
                    with self.cond:
                        self.failed = "reconnect_exhausted"
                        self.cond.notify_all()
                    return
                print("  stream lost, reconnecting...")
                self.reconnects += 1
                time.sleep(self.acq.delay(failures))
                cap, t0, n0 = self._open()
                continue
            failures = 0
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            with self.cond:
                self.count += 1
                if self.cadence.due(self.count / self.fps):
                    if self.offered > self.taken:
                        self.dropped += 1  # the previous offered frame was never processed
                    self.frame, self.t = frame, self.count / self.fps
                    self.ts = pos_ms / 1000 if pos_ms and pos_ms > 0 else None
                    self.offered += 1
                    self.cond.notify()
            # Segments arrive in bursts; decoding them at full speed would starve the detector,
            # so decode at the stream's own frame rate.
            time.sleep(max(0.0, (self.count - n0) / self.fps - (time.time() - t0)))

    def read(self, timeout=None):
        """Newest offered frame, its stream time in seconds and the decoder timestamp (frames
        offered since the last read are dropped). (None, None, None) on timeout or failure."""
        with self.cond:
            if not self.cond.wait_for(lambda: self.offered > self.taken or self.failed, timeout):
                return None, None, None
            if self.offered <= self.taken:
                return None, None, None
            self.taken = self.offered
            return self.frame, self.t, self.ts


def clip_fps(frames_t, fallback):
    """Playback rate of a clip from the stream times of its frames (live streams drop frames)."""
    span = frames_t[-1] - frames_t[0] if len(frames_t) > 1 else 0
    return (len(frames_t) - 1) / span if span > 0 else fallback


def write_clip(path, frames, fps):
    """Event clip from already-processed frames (people blurred, boxes drawn), never from the raw source."""
    w = ClipWriter(path, frames[0].shape[1], frames[0].shape[0], fps)
    for f in frames:
        w.write(f)
    w.close()


def pick_model(cfg, model_name=None):
    """--model wins; else the camera's own fine-tuned weights if present here; else stock."""
    if model_name:
        return model_name
    own = cfg.get("model")
    if own and Path(own).exists():
        return own
    if own:
        print(f"Model {own} lipsește pe acest calculator; folosesc yolo11s.pt.")
    return "yolo11s.pt"


def run(camera_path, model_name=None, imgsz=1280, max_seconds=None, use_wandb=None, live=False, loop=False):
    """Batch mode: process the whole video, replace this camera's events.
    Live mode: play at real-time speed, timestamp events with the current time and send each one
    as soon as its clip is complete (append-only, like a real camera feed)."""
    redaction = redaction_mode()
    cfg, calib, zones = load_camera(camera_path)
    model_arg, model_name = model_name, pick_model(cfg, model_name)
    cam_id = cfg["id"]
    folder = Path("data/media") / cam_id
    folder.mkdir(parents=True, exist_ok=True)
    out = sink.from_env()
    stream = live and "://" in str(cfg["video"])

    cap = cv2.VideoCapture(cfg["video"])
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # Opt-in (RS_REMOTE_CONFIG=1): the backend's ACTIVE, approved config replaces the YAML's
    # geometry/rules/thresholds; a camera the backend does not authorize is never started.
    remote = remote_config.from_env(out, cam_id, frame_size=(W, H), source_fps=fps,
                                    source_is_stream="://" in str(cfg["video"]), source=cfg["video"])
    if remote:
        try:
            cfg = remote.initial(cfg)
        except remote_config.RemoteConfigError as err:
            cap.release()
            raise SystemExit(f"Camera {cam_id} not started: {err}") from None
        calib, zones = build_geometry(cfg)
        model_name = pick_model(cfg, model_arg)
    if not live:
        for old in folder.glob("*"):
            old.unlink()
        out.clear_camera(cam_id)
    # acquisition (remote config only; without it the original behaviour is kept): the cadence
    # cap applies at the next frame, reconnect/timeout settings at the next (re)open.
    cadence = runtime.Cadence()

    def apply_acquisition(c):
        if remote and c.get("acquisition"):
            acq = runtime.Acquisition.from_config(c["acquisition"])
            cadence.set(acq.target_fps)
            if reader:
                reader.acq = acq

    reader = None
    if stream:
        cap.release()
        reader = LiveReader(cfg["video"], fps, cadence=cadence)
    apply_acquisition(cfg)
    out_h = int(H * OUT_W / W) // 2 * 2
    start = datetime.fromisoformat(cfg["start_time"])

    model = YOLO(model_name)
    detected = keep_detector_boxes(model)
    torch = __import__("torch")
    device = "mps" if torch.backends.mps.is_available() else 0 if torch.cuda.is_available() else "cpu"
    engine = RuleEngine(zones, cfg["thresholds"], cfg.get("rules"))
    out_fps = remote_config.effective_fps(fps, cfg) if remote and cfg.get("acquisition") else fps
    writer = None if live else ClipWriter(folder / "annotated.mp4", OUT_W, out_h, out_fps)
    run_log = None if live else tracking.start(cfg, model_name, imgsz, enabled=use_wandb)

    # Recent processed frames as JPEG bytes (~100 KB each), enough for a ±3 s clip.
    recent = deque(maxlen=int(fps * (2 * CLIP_PAD_S + 1)))

    # Live: uploads run on one worker thread, so a slow network never stalls the frame loop.
    uploads = ThreadPoolExecutor(max_workers=1) if live else None

    def publish(e):
        window = [(ft, b) for ft, b in recent if abs(ft - e["video_t"]) <= CLIP_PAD_S]
        frames = [cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR) for _, b in window]
        rate = clip_fps([ft for ft, _ in window], fps)
        if uploads:
            pending_uploads[0] += 1
            uploads.submit(send_event, e, frames, rate)
        else:
            send_event(e, frames, rate)

    pending_uploads = [0]  # events handed to the upload thread and not finished yet
    last_error = [None]  # newest error code for heartbeats (no message: it could quote a URL)

    def send_event(e, frames, rate):
        try:
            store_event(e, frames, rate)
        except Exception as err:  # noqa: BLE001 - a lost upload must not stop a live camera
            if not live:
                raise
            last_error[0] = "upload_failed"
            print(f"  could not send {e['type']} event: {err}")
        finally:
            if uploads:
                pending_uploads[0] -= 1

    def store_event(e, frames, rate):
        clip = folder / f"{e['stem']}.mp4"
        write_clip(clip, frames, rate)
        e.update(camera_id=cam_id, camera_name=cfg["name"], location=cfg.get("location", ""))
        if not live:
            e["occurred_at"] = (start + timedelta(seconds=e["video_t"])).isoformat()
        verdict = vlm.check({**e, "keyframe": media.key_for(e["keyframe_path"]), "clip": media.key_for(clip)})
        if "vlm" in verdict:
            e["details"]["vlm"] = verdict.pop("vlm")
        e.update(verdict)
        out.add_event(e, e["keyframe_path"], clip)

    waiting, published, flash = [], [], {}  # before the heartbeat thread starts (it reads waiting)
    stop = threading.Event()
    # Fixed keys (read by the heartbeat thread). processing_fps is the END-TO-END rate of the whole
    # loop over the last frames; inference_p50/p95_ms time the model.track call (pre/post-processing
    # and tracker included). Neither is relabelled as the other.
    telemetry = {"source_fps": round(float(fps), 2), "model_id": Path(str(model_name)).name, "frame_width": W,
                 "frame_height": H, "processing_fps": None, "last_frame_at": None,
                 "inference_p50_ms": None, "inference_p95_ms": None}
    last_frame = [None]  # wall-clock time of the newest processed frame
    latency, loop_rate, frozen = runtime.LatencyWindow(), runtime.RateWindow(), runtime.FrozenDetector()
    hb_interval = min(300.0, max(2.0, float(os.environ.get("RS_HEARTBEAT_INTERVAL_S", "30"))))

    def live_metrics():
        st = frozen.state()
        return {"rss_mb": runtime.rss_mb(), "dropped_frames": reader.dropped if reader else 0,
                "retries": reader.reconnects if reader else 0, "queue_depth": len(waiting) + max(0, pending_uploads[0]),
                "frozen_signal": st["signal"], "frozen_confidence": st["confidence"], "unchanged_s": st["unchanged_s"],
                "error_code": (reader.failed if reader else None) or last_error[0]}, st["frozen"]

    def heartbeat():  # tells the dashboard this camera is being processed right now
        while True:
            try:
                if remote:
                    metrics, is_frozen = live_metrics()
                    health = remote_config.frame_health(last_frame[0], time.time(), frozen=is_frozen)
                    remote.heartbeat(health=health, **telemetry, **metrics)
                else:
                    out.heartbeat(cam_id)
            except Exception as err:  # noqa: BLE001
                print(f"  heartbeat failed: {err}")
            if stop.wait(hb_interval):
                return

    if live or remote:
        threading.Thread(target=heartbeat, daemon=True).start()

    n, t0, det_total, speeds = 0, time.time(), 0, []
    frame_no, t = 0, 0.0  # decoded frames of a file source (the cadence may skip some)
    wall0 = time.time()
    while True:
        if remote:  # safe boundary: a new approved revision is applied between two frames
            new_cfg = remote.poll_update(cfg)
            if remote.stop_requested:
                print(f"  backend asked to stop ({remote.stop_reason})")
                break
            if new_cfg:
                cfg = new_cfg
                calib, zones = build_geometry(cfg)
                engine = RuleEngine(zones, cfg["thresholds"], cfg.get("rules"))
                apply_acquisition(cfg)
                print(f"  applied config revision {remote.applied[0]}")
        if stream:
            frame, t_new, ts = reader.read(timeout=1.0)
            if frame is None:
                if reader.failed:
                    break
                continue  # nothing new yet: lets the loop see stop requests and updates
            t = t_new
            if max_seconds and t >= max_seconds:
                break
        else:
            ok, frame = cap.read()
            t = frame_no / fps
            ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 if ok else None
            frame_no += 1
        if not stream and not ok and live and loop:
            # Restart the feed: new tracker state, same rules config.
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            model = YOLO(model_name)
            detected = keep_detector_boxes(model)
            engine = RuleEngine(zones, cfg["thresholds"], cfg.get("rules"))
            n, frame_no, wall0, flash = 0, 0, time.time(), {}
            cadence.set(None)
            apply_acquisition(cfg)
            frozen = runtime.FrozenDetector()  # decoder timestamps restart too
            recent.clear()  # timestamps restart at 0
            continue
        if not stream and (not ok or (max_seconds and t >= max_seconds)):
            break
        if not stream and not cadence.due(t):
            continue  # above acquisition.target_fps: skipped on purpose, not a dropped frame
        frozen.update(frame, ts)
        if live and not stream:  # don't run ahead of the real clock (a stream paces itself)
            time.sleep(max(0.0, wall0 + t - time.time()))
        t_inf = time.perf_counter()
        res = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=list(COCO), imgsz=imgsz,
                          device=device, verbose=False, conf=0.3)[0]
        latency.add((time.perf_counter() - t_inf) * 1000)
        # Include untracked, distant and occupant detections in privacy redaction.
        detections = [(COCO[int(c)], tuple(b)) for b, c in
                      zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.int().cpu().tolist())]
        redact_frame(frame, detections, redaction)
        objs = []
        if res.boxes.id is not None:
            for (x1, y1, x2, y2), tid, c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.id.int().cpu().tolist(),
                                                 res.boxes.cls.int().cpu().tolist()):
                foot = ((x1 + x2) / 2, y2)
                if foot[1] < cfg.get("min_y", 0):
                    continue
                objs.append((tid, COCO[c], foot, (float(x1), float(y1), float(x2), float(y2))))
        objs = drop_occupants(objs)
        det_total += len(objs)

        # Boxes cut by the frame edge give a false foot point, so they are drawn but not measured.
        events = engine.update(t, [o for o in objs if not touches_edge(o[3], W, H)], calib)
        for e in events:
            if e["track_id"] is not None:
                flash[e["track_id"]] = PRIORITY_COLORS[e["priority"]]
        shown = {o[0]: detector_box(o[3], detected["boxes"]) for o in objs}
        draw(frame, zones, objs, engine, flash, shown)
        small = cv2.resize(frame, (OUT_W, out_h))
        recent.append((t, cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()))
        if writer:
            writer.write(small)

        for e in events:
            e["redaction"] = "heads_only" if redaction == "off" else redaction  # DB accepts full|heads_only
            e.setdefault("details", {})["redaction"] = e["redaction"]
            e["video_t"] = round(t, 2)
            e["occurred_at"] = datetime.now().isoformat(timespec="seconds")
            e["stem"] = f"event_{int(time.time() * 1000)}_{e['type']}"
            kf = small.copy()
            if e["bbox"]:
                s = OUT_W / W
                x1, y1, x2, y2 = (int(v * s) for v in shown.get(e["track_id"], e["bbox"]))
                cv2.rectangle(kf, (x1 - 6, y1 - 6), (x2 + 6, y2 + 6), PRIORITY_COLORS[e["priority"]], 4)
            cv2.putText(kf, f"{e['label']} | t={t:.1f}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            e["keyframe_path"] = folder / f"{e['stem']}.jpg"
            cv2.imwrite(str(e["keyframe_path"]), kf, [cv2.IMWRITE_JPEG_QUALITY, 80])
            waiting.append(e)
            print(f"[{t:6.1f}s] {e['priority'].upper():8} {e['label']}: {e['rule']}")

        # Send events whose clip window (±3 s) is already in the video.
        while waiting and waiting[0]["video_t"] + CLIP_PAD_S <= t:
            publish(waiting[0])
            published.append(waiting.pop(0))
        n += 1
        last_frame[0] = time.time()
        loop_rate.tick(last_frame[0])
        telemetry.update(processing_fps=loop_rate.rate(), last_frame_at=remote_config.utc_iso(last_frame[0]),
                         inference_p50_ms=latency.percentile(50), inference_p95_ms=latency.percentile(95))
        if n % 100 == 0:
            print(f"  frame {n}  ({n / (time.time() - t0):.1f} fps)")
    cap.release()
    for e in waiting:
        publish(e)
        published.append(e)
    stop.set()
    if remote:
        try:
            metrics, _ = live_metrics()
            if reader and reader.failed:  # visible (and notified) before the lease is released
                remote.heartbeat(health="source_failed", **telemetry, **metrics)
            remote.heartbeat(health="stopped", **telemetry, **metrics)  # releases the processing lease
        except Exception as err:  # noqa: BLE001
            print(f"  final heartbeat failed: {err}")
    if uploads:
        uploads.shutdown(wait=True)
    if writer:
        writer.close()
        out.add_camera_video(cam_id, folder / "annotated.mp4")

    for tr in engine.tracks.values():
        speeds += [s for _, s in tr.speeds]
    stats = {
        "frames": n, "video_seconds": round(t if stream else frame_no / fps, 1), "processing_fps": round(n / (time.time() - t0), 2),
        "detections": det_total, "unique_tracks": len(engine.tracks), "events": len(published),
        "tracks_by_class": dict(engine.class_counts),
        "events_by_type": dict(Counter(e["type"] for e in published)),
        "median_vehicle_speed_kmh": round(float(np.median(speeds)), 1) if speeds else None,
    }
    for e in published:
        e["keyframe"] = str(e["keyframe_path"])
    tracking.finish(run_log, stats, published, speeds, folder / "annotated.mp4")
    print("\nRezumat:", stats)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("camera")
    ap.add_argument("--model", help="weights (default: the camera's 'model', else yolo11s.pt)")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--max-seconds", type=float)
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--live", action="store_true", help="real-time playback, events sent as they happen")
    ap.add_argument("--loop", action="store_true", help="with --live: replay the video forever")
    a = ap.parse_args()
    run(a.camera, a.model, a.imgsz, a.max_seconds, use_wandb=False if a.no_wandb else None, live=a.live, loop=a.loop)


if __name__ == "__main__":
    main()
