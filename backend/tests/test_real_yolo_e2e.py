"""Opt-in live model -> signed HTTP API -> PostgreSQL proof.

Run only when the locally downloaded, licensed model and clip are present:
RS_RUN_REAL_YOLO_E2E=1 pytest tests/test_real_yolo_e2e.py -q
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest
import yaml
from roadsentinel.pipeline import ClipWriter

from app.db import tenant_session
from app.models import Alert, AuditLog, Camera
from app.services import ingest_auth
from app.services.ingest_auth import sign, signing_message
from app.services.keys import load_keyring
from tests.conftest import World
from tests.test_contract_ingest import add_camera

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models/yolox_s.onnx"
VIDEO = Path("/tmp/Street_traffic.webm")


@pytest.mark.skipif(
    os.getenv("RS_RUN_REAL_YOLO_E2E") != "1" or not MODEL.is_file() or not VIDEO.is_file(),
    reason="requires explicit opt-in plus local licensed clip and verified YOLOX weights",
)
def test_real_model_live_replay_posts_signed_telemetry_to_tenant_api(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    camera_uuid = add_camera(world.a.id, "demo-highway")
    with tenant_session(world.a.id) as db:
        account = ingest_auth.create_account(
            db, world.a.id, "real-yolo-e2e", camera_ids=[camera_uuid]
        )
        issued = ingest_auth.issue_key(db, load_keyring(db, world.a.id), account)
        db.commit()

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        replay_port = sock.getsockname()[1]
    cfg = yaml.safe_load((ROOT / "cameras/demo-highway.yaml").read_text())
    cfg.update(
        {
            "video": f"http://127.0.0.1:{replay_port}/stream.mjpg",
            "enabled": True,
            "source_replay": True,
            "source_fps": 10,
            "min_y": 250,
            "source_consent": {
                "granted": True,
                "by": "CC BY 3.0 license / Wikimedia Commons",
                "date": "2026-11-06",
                "scope": "Local non-commercial real-time replay and vehicle inference",
                "evidence": "https://commons.wikimedia.org/wiki/File:Street_traffic.webm",
                "licence": "CC BY 3.0",
            },
        }
    )
    cfg["counting_lines"] = [{"id": "midline", "lane": "all", "points": [[200, 650], [1720, 650]]}]
    cfg["rules"] = ["wrong_way"]
    camera_file = tmp_path / "authorized-replay.yaml"
    camera_file.write_text(yaml.safe_dump(cfg))

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.setenv("RS_PUBLIC_ORIGIN", "http://127.0.0.1:5173")
    monkeypatch.setenv("RS_COOKIE_SECURE", "false")  # local test stack; production stays secure
    from app.config import get_settings

    get_settings.cache_clear()
    import uvicorn

    from app.main import create_app

    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "local FastAPI did not start within 10 seconds"
        replay = subprocess.Popen(  # noqa: S603 - fixed module invocation and local video path
            [
                sys.executable,
                "-m",
                "roadsentinel.replay",
                "--video",
                str(VIDEO),
                "--host",
                "127.0.0.1",
                "--port",
                str(replay_port),
                "--fps",
                "10",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        replay_ready = time.monotonic() + 10
        while time.monotonic() < replay_ready:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{replay_port}/health", timeout=1).close()
                break
            except OSError:
                if replay.poll() is not None:
                    pytest.fail("local MJPEG replay server exited before readiness")
                time.sleep(0.1)
        else:
            replay.terminate()
            pytest.fail("local MJPEG replay server did not become ready")
        env = os.environ.copy()
        env.update(
            {
                "RS_API_URL": f"http://127.0.0.1:{port}",
                "RS_INGEST_KEY_ID": issued.key_id,
                "RS_INGEST_SECRET": issued.secret,
                "RS_SAVE_DETECTIONS": "0",
            }
        )
        proc = subprocess.Popen(  # noqa: S603 - fixed interpreter/module and validated local config paths
            [
                sys.executable,
                "-m",
                "roadsentinel.pipeline",
                str(camera_file),
                "--model",
                str(MODEL),
                "--no-wandb",
                "--live",
                "--loop",
                "--imgsz",
                "640",
                "--frame-stride",
                "10",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        heartbeat_deadline = time.monotonic() + 20
        pipeline_info = None
        while time.monotonic() < heartbeat_deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                current = db.get(Camera, camera_uuid)
                pipeline_info = current.status_info if current else None
            if pipeline_info and pipeline_info.get("source", {}).get("frames", 0) > 0:
                break
            time.sleep(0.25)
        if not pipeline_info or pipeline_info.get("source", {}).get("frames", 0) == 0:
            proc.terminate()
            output, _ = proc.communicate(timeout=8)
            replay.terminate()
            replay.communicate(timeout=5)
            pytest.fail("real pipeline did not persist an API heartbeat: " + output[-3000:])

        # A separate deterministic alert exercises the real UI review path. It is deliberately
        # labeled synthetic and is not attributed to the YOLO replay (which emits no incident).
        keyframe = tmp_path / "synthetic-keyframe.jpg"
        clip = tmp_path / "synthetic-clip.mp4"
        fixture_frame = np.full((360, 640, 3), (38, 42, 50), dtype=np.uint8)
        cv2.rectangle(fixture_frame, (12, 12), (628, 348), (0, 180, 255), 3)
        cv2.putText(
            fixture_frame,
            "SYNTHETIC TEST - NOT MODEL EVIDENCE",
            (34, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        encoded, keyframe_bytes = cv2.imencode(".jpg", fixture_frame)
        assert encoded
        keyframe.write_bytes(keyframe_bytes.tobytes())
        clip_writer = ClipWriter(clip, 640, 360, 8)
        for sample in range(16):
            frame = fixture_frame.copy()
            cv2.putText(
                frame,
                f"SYNTHETIC TEST FRAME {sample + 1:02d}/16",
                (34, 235),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (40, 240, 140),
                2,
                cv2.LINE_AA,
            )
            clip_writer.write(frame)
        clip_writer.close()
        assert clip.is_file() and clip.stat().st_size > 1000
        synthetic_event = {
                "camera_id": "demo-highway",
                "type": "wrong_way",
                "occurred_at": "2026-11-06T12:00:00",
                "video_t": 1.0,
                "track_id": 999,
                "object_class": "car",
                "rule": "SYNTHETIC TEST: deterministic wrong-way scenario",
                "details": {"scenario_type": "synthetic_test", "test_only": True},
                "event_key": "synthetic-live-ui-review-001",
                "vlm_status": "skipped",
            }
        request = httpx.Request(
            "POST",
            f"http://127.0.0.1:{port}/api/ingest/events",
            data={"event": json.dumps(synthetic_event)},
            files={
                "keyframe": (keyframe.name, keyframe.read_bytes(), "image/jpeg"),
                "clip": (clip.name, clip.read_bytes(), "video/mp4"),
            },
        )
        body = request.read()
        timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(18)
        target = request.url.raw_path.decode()
        request.headers.update(
            {
                "X-RS-Key-Id": issued.key_id,
                "X-RS-Timestamp": timestamp,
                "X-RS-Nonce": nonce,
                "X-RS-Signature": sign(
                    issued.secret,
                    signing_message(request.method, target, timestamp, nonce, body),
                ),
            }
        )
        with httpx.Client(timeout=5) as client:
            synthetic_alert_number = client.send(request).raise_for_status().json()["id"]
        frontend = subprocess.Popen(
            [
                "/home/justin7m8/miniconda3/envs/rs-node22/bin/node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--strictPort",
            ],
            cwd=ROOT / "frontend",
            env={
                **os.environ,
                "RS_UI_ORIGIN": "http://127.0.0.1:5173",
                "RS_API_ORIGIN": f"http://127.0.0.1:{port}",
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            ui_deadline = time.monotonic() + 15
            while time.monotonic() < ui_deadline:
                try:
                    urllib.request.urlopen("http://127.0.0.1:5173", timeout=1).close()
                    break
                except OSError:
                    if frontend.poll() is not None:
                        pytest.fail("Vite stopped before readiness")
                    time.sleep(0.1)
            else:
                pytest.fail("Vite did not become ready within 15 seconds")
            ui_env = os.environ.copy()
            ui_env.update(
                {
                    "RS_UI_USER": world.a.operator.email,
                    "RS_UI_PASSWORD": world.a.operator.password,
                    "RS_UI_TOTP": world.a.operator.totp(),
                    "RS_SYNTHETIC_ALERT_ID": str(synthetic_alert_number),
                        "RS_E2E_SCREENSHOT": str(tmp_path / "camera-live-overlay.png"),
                    "PLAYWRIGHT_BROWSERS_PATH": "/home/justin7m8/.cache/ms-playwright",
                }
            )
            browser = subprocess.run(
                ["/home/justin7m8/miniconda3/envs/rs-node22/bin/node", "e2e/yolo-live.mjs"],
                cwd=ROOT / "frontend",
                env=ui_env,
                capture_output=True,
                text=True,
                timeout=75,
            )
            assert browser.returncode == 0, browser.stdout[-2000:] + browser.stderr[-2000:]
            assert "REAL_API_CAMERA_DETAIL_OK" in browser.stdout
            print(browser.stdout.strip())
        finally:
            frontend.terminate()
            try:
                frontend.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                frontend.kill()
                frontend.communicate(timeout=2)
            # Close the capture source first so OpenCV's network read can unblock before SIGTERM.
            replay.terminate()
            try:
                replay.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                replay.kill()
                replay.communicate(timeout=2)
            proc.terminate()
            try:
                output, _ = proc.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                output, _ = proc.communicate(timeout=3)
                pytest.fail("YOLO pipeline did not stop within the bounded shutdown window")
            print("REAL_YOLO_PIPELINE_LOG=" + output[-1000:].replace("\n", " | "))
        assert "heartbeat failed" not in output, output[-2000:]
        with tenant_session(world.a.id) as db:
            alert = db.query(Alert).filter(Alert.number == synthetic_alert_number).one()
            assert alert.status.value == "rejected"
            assert alert.details["scenario_type"] == "synthetic_test"
            assert any(
                row.action == "alert.rejected" and row.resource_id == str(alert.id)
                for row in db.query(AuditLog).all()
            )
            camera = db.get(Camera, camera_uuid)
            assert camera is not None and camera.status_info
            info = camera.status_info
            assert info["source"]["replay"] is True
            assert info["detections"] > 0
            assert info["unique_tracks"] > 0
            assert info["traffic"]["total_crossings"] > 0
            assert info["processing_fps"] > 0
            assert info["inference_latency_ms_p95"] > 0
            assert info["process_peak_rss_mb"] > 0
            assert (
                info["model_sha256"]
                == "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
            )
            result = {
                "reported_at": info["reported_at"],
                "source": info["source"],
                "processing_fps": info["processing_fps"],
                "inference_latency_ms_p50": info["inference_latency_ms_p50"],
                "inference_latency_ms_p95": info["inference_latency_ms_p95"],
                "inference_latency_ms_p99": info["inference_latency_ms_p99"],
                "process_peak_rss_mb": info["process_peak_rss_mb"],
                "detections": info["detections"],
                "unique_tracks": info["unique_tracks"],
                "tracks_by_class": info["tracks_by_class"],
                "traffic": info["traffic"],
                "model": info["model"],
                "model_sha256": info["model_sha256"],
            }
            print("REAL_YOLO_API_PERSISTED=" + json.dumps(result, sort_keys=True))
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
