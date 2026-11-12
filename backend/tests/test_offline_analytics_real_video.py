"""Opt-in production-path acceptance for an owner-supplied local WebM segment.

Run only against a disposable PostgreSQL test cluster:
RS_OFFLINE_ANALYTICS_REAL_VIDEO=/tmp/segment.webm RS_TEST_ADMIN_DATABASE_URL=... \
  python -m pytest tests/test_offline_analytics_real_video.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

import pytest
from sqlalchemy import select

from app.db import tenant_session
from app.models import AnalysisRun, Recording
from app.services.offline_video_storage import storage_path


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_real_browser_acceptance(actor) -> None:
    root = Path(__file__).resolve().parents[2]
    frontend = root / "frontend"
    evidence = Path("/tmp") / f"roadsentinel-offline-analytics-{uuid.uuid4().hex}"
    evidence.mkdir(mode=0o700)
    api_port, frontend_port = _free_port(), _free_port()
    origin = f"http://127.0.0.1:{frontend_port}"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(root),
            "RS_PUBLIC_ORIGIN": origin,
            "RS_COOKIE_SECURE": "false",
            "RS_API_ORIGIN": f"http://127.0.0.1:{api_port}",
            "VITE_USE_MOCKS": "0",
            "PLAYWRIGHT_BROWSERS_PATH": "/home/justin7m8/.cache/ms-playwright",
            "RS_E2E_URL": origin,
            "RS_E2E_EMAIL": actor.email,
            "RS_E2E_PASSWORD": actor.password,
            "RS_E2E_TOTP": actor.totp(),
            "RS_E2E_SCREENSHOT_DIR": str(evidence),
        }
    )
    node_bin = Path("/home/justin7m8/miniconda3/envs/rs-node22/bin")
    if node_bin.is_dir():
        env["PATH"] = f"{node_bin}:{env.get('PATH', '')}"
    node = shutil.which("node", path=env["PATH"])
    if not node:
        raise RuntimeError("Node is unavailable for browser acceptance")
    logs = [(evidence / "api.log").open("wb"), (evidence / "vite.log").open("wb")]
    processes: list[subprocess.Popen] = []
    try:
        processes.append(
            subprocess.Popen(  # noqa: S603 - fixed Python executable and fixed local app argv
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                cwd=root / "backend",
                env=env,
                stdout=logs[0],
                stderr=subprocess.STDOUT,
            )
        )
        api_ready = False
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if processes[0].poll() is not None:
                raise RuntimeError(f"Uvicorn exited; inspect local log {evidence / 'api.log'}")
            try:
                with urlopen(
                    f"http://127.0.0.1:{api_port}/api/health", timeout=1
                ) as response:
                    api_ready = response.status == 200
                    break
            except Exception:
                time.sleep(0.2)
        if not api_ready:
            raise TimeoutError(f"Uvicorn readiness timed out; inspect {evidence / 'api.log'}")

        processes.append(
            subprocess.Popen(  # noqa: S603 - fixed local Node executable and Vite argv
                [
                    node,
                    "node_modules/vite/bin/vite.js",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(frontend_port),
                    "--strictPort",
                ],
                cwd=frontend,
                env=env,
                stdout=logs[1],
                stderr=subprocess.STDOUT,
            )
        )
        frontend_ready = False
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if processes[1].poll() is not None:
                raise RuntimeError(f"Vite exited; inspect local log {evidence / 'vite.log'}")
            try:
                with urlopen(  # noqa: S310 - generated origin contains only 127.0.0.1 and a port
                    f"{origin}/login", timeout=1
                ) as response:
                    frontend_ready = response.status == 200
                    break
            except Exception:
                time.sleep(0.25)
        if not frontend_ready:
            raise TimeoutError(f"Vite readiness timed out; inspect {evidence / 'vite.log'}")

        result = subprocess.run(  # noqa: S603 - fixed local Node executable and test script
            [node, str(frontend / "e2e/offline-analytics-real.mjs")],
            cwd=frontend,
            env=env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        print(f"browser_evidence_dir={evidence}")
        print(result.stdout)
        if result.returncode:
            raise AssertionError(
                f"Real browser acceptance failed ({result.returncode}): {result.stderr}"
            )
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        for log in logs:
            log.close()


@pytest.mark.skipif(
    not os.environ.get("RS_OFFLINE_ANALYTICS_REAL_VIDEO"),
    reason="set RS_OFFLINE_ANALYTICS_REAL_VIDEO to an authorized local WebM segment",
)
def test_real_video_upload_yolox_tracker_artifact_and_analytics(client, login, world) -> None:
    source = Path(os.environ["RS_OFFLINE_ANALYTICS_REAL_VIDEO"]).resolve(strict=True)
    actor = world.a.operator
    authenticated = login(actor)
    recording_id = run_id = None
    artifact_keys: list[str] = []
    try:
        with source.open("rb") as handle:
            imported = authenticated.post(
                "/api/recordings",
                files={"file": (source.name, handle, "video/webm")},
            )
        assert imported.status_code == 201, imported.text
        recording = imported.json()
        recording_id = recording["id"]
        rights = authenticated.patch(
            f"/api/recordings/{recording_id}/rights",
            json={"expected_revision": 0, "rights": {
                "source_name": "Licensed real-video test fixture",
                "rightsholder": "Test fixture rightsholder",
                "permission_basis": "licensed",
                "authorization_reference": "Local licensed fixture record",
                "scope": "Offline analysis and retained evidence for isolated integration tests",
                "allow_analysis": True,
                "allow_evidence_extraction": True,
                "allow_retention": True,
                "operator_declaration": True,
            }},
        )
        assert rights.status_code == 200, rights.text
        location = authenticated.patch(
            f"/api/locations/recording/{recording_id}",
            json={
                "expected_revision": 0,
                "state": "unknown",
                "explanation": "Real video fixture has no independently verified filming location",
                "source_reference": "licensed-test-fixture",
            },
        )
        assert location.status_code == 200, location.text
        assert recording["codec"] == "vp8"
        assert recording["width"] == 1050 and recording["height"] == 589
        assert recording["source_kind"] == "RECORDED SCREENCAST"

        crop = authenticated.patch(
            f"/api/recordings/{recording_id}/crop",
            json={
                "x": 0,
                "y": 0,
                "width": 1,
                "height": 1,
                "confirmed": True,
                "expected_revision": 0,
            },
        )
        assert crop.status_code == 200, crop.text
        started = authenticated.post(
            f"/api/recordings/{recording_id}/analyses",
            json={"sample_fps": 1, "confidence": 0.3, "crop_revision": 1},
        )
        assert started.status_code == 202, started.text
        run_id = started.json()["id"]

        # Allow full recordings while keeping the outer shell timeout authoritative.
        wait_budget_s = min(1800, max(150, recording["duration_ms"] / 1000 * 2))
        deadline = time.monotonic() + wait_budget_s
        current = started.json()
        while current["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(1)
            response = authenticated.get(f"/api/analyses/{run_id}")
            assert response.status_code == 200, response.text
            current = response.json()
        assert current["status"] == "completed", current
        assert current["processed_frames"] >= 10
        assert current["has_analytics"] is True

        summary_response = authenticated.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/summary"
        )
        assert summary_response.status_code == 200, summary_response.text
        summary = summary_response.json()
        assert summary["processed_samples"] == current["processed_frames"]
        assert summary["model_sha256"] == current["model_sha256"]
        assert summary["inference_fps"] == current["inference_fps"]

        heat_response = authenticated.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/heatmap",
            params={"classes": "car,truck,bus,motorcycle,bicycle", "grid_width": 128},
        )
        assert heat_response.status_code == 200, heat_response.text
        heat = heat_response.json()
        assert heat["processed_samples"] == current["processed_frames"]
        assert heat["included_observations"] > 0
        assert abs(sum(heat["values"]) - heat["total_weight"]) < 1e-3

        car_only = authenticated.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/heatmap",
            params={"classes": "car", "start_s": 0, "end_s": summary["source_duration_s"]},
        )
        assert car_only.status_code == 200, car_only.text
        assert car_only.json()["included_observations"] == heat[
            "observation_totals_by_class"
        ].get("car", 0)

        timeline = authenticated.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/timeline",
            params={"classes": "car", "start_s": 0, "end_s": summary["source_duration_s"]},
        )
        assert timeline.status_code == 200, timeline.text
        assert sum(
            item["observations_by_class"].get("car", 0)
            for item in timeline.json()["bins"]
        ) == car_only.json()["included_observations"]

        frame = authenticated.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/frame",
            params={"pts_seconds": summary["sampled_span_s"][0]},
        )
        assert frame.status_code == 200 and frame.headers["content-type"].startswith("image/jpeg")
        assert "no-store" in frame.headers["cache-control"]
        assert frame.content.startswith(b"\xff\xd8")

        output_range = authenticated.get(
            f"/api/analyses/{run_id}/video", headers={"Range": "bytes=0-63"}
        )
        assert output_range.status_code == 206
        assert len(output_range.content) == 64

        assert client.get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/summary"
        ).status_code == 401
        assert login(world.b.operator).get(
            f"/api/recordings/{recording_id}/analyses/{run_id}/analytics/summary"
        ).status_code == 404
        print(
            json.dumps(
                {
                    "recording_id": recording_id,
                    "analysis_run_id": run_id,
                    "source_duration_s": summary["source_duration_s"],
                    "processed_samples": current["processed_frames"],
                    "observation_count": current["observation_count"],
                    "observation_totals_by_class": heat["observation_totals_by_class"],
                    "estimated_tracker_ids_by_class": summary[
                        "estimated_tracker_id_totals_by_class"
                    ],
                    "heatmap_total_weight": heat["total_weight"],
                    "heatmap_nonzero_cells": sum(value > 0 for value in heat["values"]),
                    "sampled_output_fps": current["output_fps"],
                    "measured_processing_fps": current["inference_fps"],
                    "analysis_started_at": current["started_at"],
                    "analysis_ended_at": current["ended_at"],
                    "source_kind": recording["source_kind"],
                },
                ensure_ascii=False,
            )
        )
        if os.environ.get("RS_OFFLINE_ANALYTICS_BROWSER") == "1":
            _run_real_browser_acceptance(actor)
    finally:
        if recording_id:
            with tenant_session(world.a.id) as db:
                recording = db.scalar(
                    select(Recording).where(Recording.id == recording_id)
                )
                if recording:
                    artifact_keys.append(recording.storage_key)
                if run_id:
                    run = db.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))
                    if run:
                        artifact_keys.extend(
                            key
                            for key in (
                                run.output_storage_key,
                                run.observation_storage_key,
                            )
                            if key
                        )
            for key in artifact_keys:
                storage_path(key).unlink(missing_ok=True)
