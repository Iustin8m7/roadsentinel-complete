"""Real HTTP + PostgreSQL + actual ONNX inference on an explicitly synthetic frozen-frame fixture.

The source frame is from Editor's Street traffic (CC BY 3.0); this demonstrates rule mechanics,
not a real street obstruction, incident accuracy, or live-camera permission.
"""

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import cv2
import httpx
import pytest
import uvicorn


@pytest.mark.skipif(
    os.getenv("RS_MISSION_REAL") != "1", reason="explicit licensed fixture/model opt-in"
)
def test_real_inference_recorded_candidate_to_encrypted_review(world, tmp_path, monkeypatch):
    from sqlalchemy import select

    from app.config import get_settings
    from app.core.http import CSRF, cookie_name
    from app.db import tenant_session
    from app.main import create_app
    from app.models import Alert, Evidence
    from app.services.evidence import file_path

    cap = cv2.VideoCapture("/tmp/Street_traffic.webm")
    ok, frame = cap.read()
    cap.release()
    assert ok
    frame = cv2.resize(frame, (640, 360))
    clip = tmp_path / "SYNTHETIC_TEST_frozen_licensed_frame.mp4"
    writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), 5, (640, 360))
    assert writer.isOpened()
    for _ in range(180):
        writer.write(frame)
    writer.release()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        ui_port = sock.getsockname()[1]
    ui_origin = f"http://127.0.0.1:{ui_port}"
    monkeypatch.setenv("RS_PUBLIC_ORIGIN", ui_origin)
    monkeypatch.setenv("RS_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        with httpx.Client(base_url=origin, timeout=60) as client:
            client.get("/api/auth/csrf").raise_for_status()
            client.headers.update(
                {"Origin": ui_origin, "X-CSRF-Token": client.cookies.get(cookie_name(CSRF))}
            )
            user = world.a.operator
            r = client.post(
                "/api/auth/login", json={"email": user.email, "password": user.password}
            )
            assert r.status_code == 200, r.text
            r = client.post("/api/auth/mfa/verify", json={"code": user.totp()})
            assert r.status_code == 204, r.text
            with clip.open("rb") as src:
                r = client.post("/api/recordings", files={"file": (clip.name, src, "video/mp4")})
            assert r.status_code == 201, r.text
            rid = r.json()["id"]
            rights = {
                "source_name": "Licensed synthetic traffic test",
                "rightsholder": "Test fixture rightsholder",
                "permission_basis": "licensed",
                "authorization_reference": "Local licensed fixture record",
                "scope": "Offline analysis, incident evidence extraction and retention for tests",
                "allow_analysis": True,
                "allow_evidence_extraction": True,
                "allow_retention": True,
                "operator_declaration": True,
            }
            r = client.patch(f"/api/recordings/{rid}/rights", json={"expected_revision": 0, "rights": rights})
            assert r.status_code == 200, r.text
            r = client.patch(
                f"/api/locations/recording/{rid}",
                json={
                    "expected_revision": 0,
                    "state": "unknown",
                    "explanation": "Synthetic test recording has no declared filming position",
                    "source_reference": "test-fixture",
                },
            )
            assert r.status_code == 200, r.text
            r = client.patch(
                f"/api/recordings/{rid}/crop",
                json={
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "confirmed": True,
                    "expected_revision": 0,
                },
            )
            assert r.status_code == 200, r.text
            r = client.post(
                f"/api/recordings/{rid}/analyses",
                json={
                    "sample_fps": 2,
                    "confidence": 0.3,
                    "crop_revision": 1,
                    "stationary_duration_s": 30,
                    "queue_enabled": False,
                },
            )
            assert r.status_code == 202, r.text
            run = r.json()["id"]
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                result = client.get(f"/api/analyses/{run}").json()
                if result["status"] not in ("queued", "running"):
                    break
                time.sleep(0.5)
            assert result["status"] == "completed", result
            assert result["processed_frames"] >= 60
            candidates = client.get(f"/api/recordings/{rid}/analyses/{run}/candidates")
            assert candidates.status_code == 200, candidates.text
            assert candidates.json()["candidates"], result["counts"]
            path = f"/api/recordings/{rid}/analyses/{run}/candidates/0/promote"
            r = client.post(
                path,
                json={
                    "synthetic_test": True,
                    "reason": "SYNTHETIC TEST: verify recorded-source review mechanics",
                },
            )
            assert r.status_code == 200, r.text
            number = r.json()["id"]
            assert (
                client.post(path, json={"reason": "Repeated test submission"}).json()["id"]
                == number
            )
            detail = client.get(f"/api/events/{number}")
            assert detail.status_code == 200, detail.text
            data = detail.json()
            assert data["details"]["origin"] == "recorded_upload"
            for key in ("keyframe_url", "clip_url"):
                response = client.get(data[key])
                assert response.status_code == 200, response.text[:200]
                assert len(response.content) > 200
            from app.models import Role
            from tests.conftest import make_user

            browser_user = make_user(world.a.id, Role.operator, "browser@mission.local")
            root = Path(__file__).resolve().parents[2]
            browser_log = (tmp_path / "vite.log").open("wb")
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
                env={**os.environ, "RS_API_ORIGIN": origin, "VITE_USE_MOCKS": "0"},
                stdout=browser_log,
                stderr=browser_log,
            )
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    try:
                        if httpx.get(ui_origin).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                shot = root / "docs/audits/screenshots/recorded-review.png"
                shot.parent.mkdir(exist_ok=True)
                result_browser = subprocess.run(
                    [
                        "/home/justin7m8/miniconda3/envs/rs-node22/bin/node",
                        "e2e/mission-review.mjs",
                    ],
                    cwd=root / "frontend",
                    env={
                        **os.environ,
                        "RS_MISSION_UI": ui_origin,
                        "RS_MISSION_EMAIL": browser_user.email,
                        "RS_MISSION_PASSWORD": browser_user.password,
                        "RS_MISSION_OTP": browser_user.totp(),
                        "RS_MISSION_ALERT": str(number),
                        "RS_MISSION_SCREENSHOT": str(shot),
                    },
                    timeout=45,
                    capture_output=True,
                    text=True,
                )
                assert result_browser.returncode == 0, result_browser.stderr[-1500:]
                print(result_browser.stdout.strip())
            finally:
                frontend.terminate()
                frontend.wait(timeout=10)
                browser_log.close()
            r = client.post(
                f"/api/events/{number}/decision",
                json={"decision": "reject", "note": "Synthetic fixture; no real incident"},
            )
            assert r.status_code == 409, r.text  # browser already decided; repeat is refused
            assert client.get(f"/api/events/{number}").json()["status"] == "rejected"
            with tenant_session(world.a.id) as db:
                alert = db.scalar(select(Alert).where(Alert.number == number))
                media = db.scalars(select(Evidence).where(Evidence.alert_id == alert.id)).all()
                assert len(media) == 2
                assert all(
                    file_path(e, "redacted").read_bytes()[:3] != b"\xff\xd8\xff" for e in media
                )
            # Existing investigation/export authority: real HTTP, independent admin approval,
            # documented license grant, encrypted package download and offline manifest verifier.
            note = client.post(
                f"/api/events/{number}/notes",
                json={
                    "kind": "observation",
                    "body": "SYNTHETIC TEST: licensed frozen-frame candidate reviewed.",
                },
            )
            assert note.status_code == 201, note.text
            assert client.get(f"/api/events/{number}/case").status_code == 200
            with tenant_session(world.a.id) as db:
                camera_id = db.scalar(select(Alert.camera_id).where(Alert.number == number))
            from datetime import UTC, datetime, timedelta

            with httpx.Client(base_url=origin, timeout=30) as admin:
                admin.get("/api/auth/csrf").raise_for_status()
                admin.headers.update(
                    {"Origin": ui_origin, "X-CSRF-Token": admin.cookies.get(cookie_name(CSRF))}
                )
                admin.post(
                    "/api/auth/login",
                    json={"email": world.a.admin.email, "password": world.a.admin.password},
                ).raise_for_status()
                admin.post(
                    "/api/auth/mfa/verify", json={"code": world.a.admin.totp()}
                ).raise_for_status()
                grant = admin.post(
                    f"/api/camera-control/cameras/{camera_id}/grants",
                    json={
                        "granting_party": "Editor / Wikimedia Commons",
                        "basis": "licence",
                        "basis_reference": (
                            "CC BY 3.0 Street traffic.webm; synthetic frozen derivative"
                        ),
                        "purpose": "Isolated case export verification",
                        "valid_from": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                        "valid_until": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                        "capture_method": "recorded_replay",
                        "max_analysis_fps": 2,
                        "max_frame_height": 360,
                        "retention_days": 1,
                        "export_allowed": True,
                        "media_scope": "events_only",
                    },
                )
                assert grant.status_code == 201, grant.text
                requested = client.post(
                    f"/api/events/{number}/exports",
                    json={
                        "justification": "Verify licensed synthetic recorded candidate package",
                        "case_reference": "MISSION-SYNTHETIC",
                        "idempotency_key": "mission-export-positive-01",
                    },
                )
                assert requested.status_code == 201, requested.text
                job = requested.json()
                assert client.post(f"/api/exports/{job['id']}/link").status_code == 409
                approved = admin.post(
                    f"/api/approvals/{job['approval_id']}/approve",
                    json={"note": "Independent admin: licensed synthetic test package"},
                )
                assert approved.status_code == 200, approved.text
                built = client.post(f"/api/exports/{job['id']}/run")
                assert built.status_code == 200, built.text
                assert built.json()["state"] == "completed", built.text
                signed = client.post(f"/api/exports/{job['id']}/link")
                assert signed.status_code == 200, signed.text
                package = client.get(signed.json()["url"])
                assert package.status_code == 200, package.text[:200]
                package_path = tmp_path / "case.zip"
                package_path.write_bytes(package.content)
                from app.services.package_verify import verify_package

                verified = verify_package(
                    package_path,
                    built.json()["manifest_sha256"],
                    max_uncompressed=100 * 1024 * 1024,
                )
                assert verified.ok, verified.errors
                assert verified.files_checked >= 2
                print(
                    "PASS actual HTTP case note, source license grant, four-eyes expor"
                    "t, download, SHA-256 manifest verification"
                )
            # Real HTTP negative authorization on the same completed run and evidence.
            for other, expected in (
                (world.b.operator, 404),
                (world.a.patrol, 403),
                (world.a.auditor, 403),
            ):
                with httpx.Client(base_url=origin, timeout=10) as denied:
                    denied.get("/api/auth/csrf").raise_for_status()
                    denied.headers.update(
                        {"Origin": ui_origin, "X-CSRF-Token": denied.cookies.get(cookie_name(CSRF))}
                    )
                    denied.post(
                        "/api/auth/login", json={"email": other.email, "password": other.password}
                    ).raise_for_status()
                    denied.post(
                        "/api/auth/mfa/verify", json={"code": other.totp()}
                    ).raise_for_status()
                    response = denied.post(
                        path, json={"reason": "Unauthorized submission must fail"}
                    )
                    assert response.status_code == expected, response.text
                    if other == world.b.operator:
                        assert denied.get(data["clip_url"]).status_code in (403, 404)
            print(
                "REAL HTTP: YOLOX/ByteTrack frozen licensed-frame fixture -> candi"
                "date -> encrypted media -> idempotent recorded review -> rejectio"
                "n; frames=",
                result["processed_frames"],
                "candidates=",
                len(candidates.json()["candidates"]),
            )
    finally:
        server.should_exit = True
        thread.join(15)
        get_settings.cache_clear()
