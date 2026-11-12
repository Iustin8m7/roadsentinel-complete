"""Actual Chromium upload-to-package and OS-process restart on owned disposable resources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import cv2
import httpx
import pytest
from sqlalchemy import select


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(
    os.getenv("RS_MISSION_REAL") != "1", reason="licensed actual model/browser opt-in"
)
def test_browser_upload_review_export_and_process_restart(world, tmp_path):
    from app.db import tenant_session
    from app.models import Alert, Evidence, Role
    from app.services.evidence import file_path
    from app.services.package_verify import verify_package
    from tests.conftest import make_user

    actor = make_user(world.a.id, Role.operator, "browser-enrollment@mission.local", mfa=False)
    root = Path(__file__).resolve().parents[2]
    output = Path(
        os.environ.get("RS_MISSION_EVIDENCE_DIR", root / "docs/audits/runtime_verification")
    )
    assert output.resolve().is_relative_to(root)
    (output / "screenshots").mkdir(parents=True, exist_ok=True)
    with_capture = cv2.VideoCapture("/tmp/Street_traffic.webm")
    ok, frame = with_capture.read()
    with_capture.release()
    assert ok
    frame = cv2.resize(frame, (640, 360))
    video = tmp_path / "SYNTHETIC_TEST_frozen_licensed_frame.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 5, (640, 360))
    assert writer.isOpened()
    for _ in range(180):
        writer.write(frame)
    writer.release()
    moving = tmp_path / "LICENSED_MOVING_TRAFFIC.mp4"
    subprocess.run(  # noqa: S603 - fixed encoder and new licensed test derivative
        [
            shutil.which("ffmpeg"),
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            "/tmp/Street_traffic.webm",
            "-t",
            "30",
            "-vf",
            "fps=10,scale=960:540",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(moving),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    api_port, ui_port = free_port(), free_port()
    assert api_port != ui_port
    api = f"http://127.0.0.1:{api_port}"
    origin = f"http://127.0.0.1:{ui_port}"
    env = {
        **os.environ,
        "RS_PUBLIC_ORIGIN": origin,
        "RS_COOKIE_SECURE": "false",
        "PYTHONPATH": os.pathsep.join((str(root / "backend"), str(root))),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("RS_ADMIN_DATABASE_URL", "RS_MIGRATOR_DATABASE_URL"):
        env.pop(key, None)
    api_process = frontend = None
    handles = []

    def start_backend():
        log = (tmp_path / f"api-{len(handles)}.log").open("ab")
        handles.append(log)
        process = subprocess.Popen(  # noqa: S603 - fixed local executable, owned ports, no shell
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
                "--no-access-log",
                "--log-level",
                "error",
            ],
            cwd=root / "backend",
            env=env,
            stdout=log,
            stderr=log,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and process.poll() is None:
            try:
                if httpx.get(api + "/api/health/live", timeout=1).status_code == 200:
                    return process
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        process.terminate()
        process.wait(timeout=10)
        raise AssertionError("Test-owned API process did not start")

    def browser(stage):
        completed = subprocess.run(
            ["/home/justin7m8/miniconda3/envs/rs-node22/bin/node", "e2e/complete-recorded.mjs"],
            cwd=root / "frontend",
            env={
                **env,
                "RS_COMPLETE_ORIGIN": origin,
                "RS_COMPLETE_PRIVATE": str(tmp_path),
                "RS_COMPLETE_PYTHON": sys.executable,
                "RS_COMPLETE_VIDEO": str(video),
                "RS_COMPLETE_MOVING_VIDEO": str(moving),
                "RS_COMPLETE_OPERATOR": actor.email,
                "RS_COMPLETE_OPERATOR_SECRET": actor.totp_secret or "",
                "RS_COMPLETE_ADMIN": world.a.admin.email,
                "RS_COMPLETE_ADMIN_SECRET": world.a.admin.totp_secret,
                "RS_COMPLETE_PASSWORD": world.a.operator.password,
                "RS_COMPLETE_STAGE": stage,
                "RS_COMPLETE_SCREENSHOT": str(output / f"screenshots/complete-{stage}.png"),
            },
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        failure = completed.stderr
        for value in (
            world.a.operator.password,
            world.a.operator.totp_secret,
            world.a.admin.totp_secret,
        ):
            failure = failure.replace(value, "<redacted>")
        assert completed.returncode == 0, failure[-3000:]
        print(completed.stdout.strip())

    try:
        api_process = start_backend()
        log = (tmp_path / "vite.log").open("ab")
        handles.append(log)
        ui_env = {k: v for k, v in os.environ.items() if not k.startswith(("RS_", "VITE_"))}
        ui_env.update(RS_API_ORIGIN=api, VITE_USE_MOCKS="0")
        frontend = subprocess.Popen(  # noqa: S603 - fixed local fixture executable, no shell
            [
                "/home/justin7m8/miniconda3/envs/rs-node22/bin/node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                str(ui_port),
                "--strictPort",
            ],
            cwd=root / "frontend",
            env=ui_env,
            stdout=log,
            stderr=log,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if httpx.get(origin, timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        browser("create")
        report = json.loads((tmp_path / "browser-result.json").read_text())
        package = tmp_path / "browser-package.zip"
        verified = verify_package(
            package, report["manifestSha256"], max_uncompressed=100 * 1024 * 1024
        )
        assert verified.ok, verified.errors
        pdf = (output / "screenshots/activity-report.pdf").read_bytes()
        assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 1, "Activity report must fit one page"
        assert verified.files_checked >= 2
        # Tamper a member while preserving valid ZIP structure/CRC and the original manifest.
        tampered = tmp_path / "tampered-package.zip"
        with zipfile.ZipFile(package) as original, zipfile.ZipFile(tampered, "w") as changed:
            names = original.namelist()
            target = next(n for n in names if n != "manifest.json" and not n.endswith("/"))
            for name in names:
                content = original.read(name)
                changed.writestr(name, content + b"tampered" if name == target else content)
        assert not verify_package(tampered, report["manifestSha256"]).ok
        with tenant_session(world.a.id) as db:
            alert = db.scalar(select(Alert).where(Alert.number == report["number"]))
            assert alert.status.value == "rejected" and alert.details["synthetic"] is True
            media = db.scalars(select(Evidence).where(Evidence.alert_id == alert.id)).all()
            assert len(media) == 2
            before = {
                str(e.id): hashlib.sha256(file_path(e, "redacted").read_bytes()).hexdigest()
                for e in media
            }
        # Genuine new OS process with the same DB/keys/storage; no fixture resets or cache reuse.
        old_pid = api_process.pid
        api_process.terminate()
        api_process.wait(timeout=20)
        api_process = start_backend()
        assert api_process.pid != old_pid
        browser("persist")
        with tenant_session(world.a.id) as db:
            assert len(db.scalars(select(Alert).where(Alert.number == report["number"])).all()) == 1
            media = db.scalars(select(Evidence).where(Evidence.alert_id == alert.id)).all()
            assert before == {
                str(e.id): hashlib.sha256(file_path(e, "redacted").read_bytes()).hexdigest()
                for e in media
            }
        report = json.loads((tmp_path / "browser-result.json").read_text())
        report.update(
            packageHashesVerified=True,
            tamperedPackageRejected=True,
            encryptedEvidenceUnchanged=True,
            backendPidChanged=True,
            source="SYNTHETIC TEST frozen licensed frame; not a real incident",
        )
        (output / "complete-browser-result.json").write_text(json.dumps(report, indent=2))
        print(
            "PASS real browser ZIP hash verification/tamper rejection "
            "and unchanged ciphertext after process restart"
        )
    finally:
        for process in (frontend, api_process):
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
        for handle in handles:
            handle.close()
