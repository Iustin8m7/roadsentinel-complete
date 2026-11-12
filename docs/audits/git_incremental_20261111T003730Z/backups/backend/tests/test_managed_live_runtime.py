"""Real replay: browser registration, two-admin API approval, worker ACK and browser preview.

Only identities are fixtures; camera/control transitions use authenticated UI/API.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import uvicorn
import yaml
from sqlalchemy import select


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(os.getenv("RS_MISSION_REAL") != "1", reason="licensed model/media opt-in")
def test_managed_replay_ack_preview_and_revocation(world, tmp_path, monkeypatch, login):
    from roadsentinel.replay import make_server

    from app.config import get_settings
    from app.db import tenant_session
    from app.main import create_app
    from app.models import CameraWorkerStatus
    from app.services import camera_config as cc
    from app.services import ingest_auth
    from app.services.keys import load_keyring

    root = Path(__file__).resolve().parents[2]
    # A moving licensed excerpt contains actual person detections. The road zone below is
    # deliberately SYNTHETIC TEST geometry, not a claim those pedestrians violated a rule.
    import shutil

    excerpt = tmp_path / "SYNTHETIC_TEST_geometry_licensed_moving_excerpt.mp4"
    subprocess.run(  # noqa: S603 - fixed encoder and test-owned local output, no shell
        [
            shutil.which("ffmpeg"),
            "-nostdin",
            "-loglevel",
            "error",
            "-ss",
            "32",
            "-i",
            "/tmp/Street_traffic.webm",
            "-t",
            "3",
            "-vf",
            "fps=10",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(excerpt),
        ],
        check=True,
        timeout=30,
        capture_output=True,
    )
    replay = make_server(excerpt, "127.0.0.1", free_port(), 10)
    disconnect = threading.Event()
    connections = []
    original_get_request = replay.get_request

    def tracked_request():
        connection, address = original_get_request()
        connections.append(connection)
        del connections[:-32]
        return connection, address

    replay.get_request = tracked_request
    replay.verify_request = lambda *_: not disconnect.is_set()
    rt = threading.Thread(target=replay.serve_forever, daemon=True)
    rt.start()
    source = f"http://127.0.0.1:{replay.server_port}/stream.mjpg"
    model = os.environ["RS_YOLOX_MODEL_PATH"]
    digest = __import__("hashlib").sha256(Path(model).read_bytes()).hexdigest()
    cfg = yaml.safe_load((root / "cameras/demo-highway.yaml").read_text())
    config = dict(
        schema_version=1,
        reference_frame=dict(width=1920, height=1080),
        calibration=None,
        counting_lines=[dict(id="crossing", points=[[100, 650], [1800, 650]], lane="test")],
        min_y=0,
        zones=[
            dict(
                id="scene",
                name="Synthetic scene geometry",
                kind="carriageway",
                direction=[0, 1],
                polygon=[[0, 0], [1919, 0], [1919, 1079], [0, 1079]],
            )
        ],
        rules=["pedestrian_on_road"],
        thresholds=cfg["thresholds"],
        acquisition=dict(
            target_fps=10, reconnect_backoff_s=1, read_timeout_s=3, max_reconnect_attempts=20
        ),
        model=dict(id="stock-yolox-s", sha256=digest),
    )
    assert cc.validate(config) == []
    # Control state is created through authenticated APIs, never preapproved DB rows.
    from uuid import UUID

    from app.models import Role
    from tests.conftest import make_user

    monkeypatch.setenv("RS_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    administrator = login(world.a.admin)
    reviewer_user = make_user(world.a.id, Role.tenant_admin, "reviewer@mission.local")
    reviewer = login(reviewer_user)
    from tests.camera_browser import camera_browser

    created = camera_browser(world.a.admin, tmp_path, monkeypatch, "register")
    cid = UUID(created["id"])
    base = f"/api/camera-control/cameras/{cid}"

    def revision():
        response = administrator.get(base)
        assert response.status_code == 200, response.text
        return response.json()["revision"]

    adopted = administrator.post(
        base + "/lifecycle",
        {
            "expected_revision": revision(),
            "reason": "Adopt controlled local replay",
            "to": "onboarding",
        },
    )
    assert adopted.status_code == 200, adopted.text
    registered = administrator.post(
        base + "/source",
        {
            "expected_revision": revision(),
            "reason": "Licensed loopback replay reference",
            "kind": "recorded_replay",
            "url": "replay://mission-fixture",
        },
    )
    assert registered.status_code == 200, registered.text
    grant = administrator.post(
        base + "/grants",
        {
            "granting_party": "Editor / Wikimedia Commons",
            "basis": "licence",
            "basis_reference": "CC BY 3.0 Street traffic.webm",
            "purpose": "Isolated local replay integration test",
            "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "capture_method": "recorded_replay",
            "max_analysis_fps": 10,
            "max_frame_height": 1080,
            "retention_days": 1,
            "media_scope": "events_only",
            "export_allowed": True,
        },
    )
    assert grant.status_code == 201, grant.text

    def publish_configuration(value):
        drafted = camera_browser(
            world.a.admin,
            tmp_path,
            monkeypatch,
            "draft",
            config=value,
            revision=len(administrator.get(base + "/versions").json()) + 1,
        )
        vid = drafted["id"]
        assert (
            administrator.post(
                base + f"/versions/{vid}/approve", {"note": "Self approval must be refused"}
            ).status_code
            == 403
        )
        return camera_browser(
            reviewer_user, tmp_path, monkeypatch, "approve", revision=drafted["revision"]
        )

    publish_configuration(config)
    with tenant_session(world.a.id) as db:
        account = ingest_auth.create_account(db, world.a.id, "mission-runtime", camera_ids=[cid])
        key = ingest_auth.issue_key(db, load_keyring(db, world.a.id), account)
        db.commit()
    cfg.update(
        id="mission-replay",
        video=source,
        enabled=True,
        source_replay=True,
        source_fps=10,
        synthetic_test=True,
        test_disclosure=(
            "SYNTHETIC TEST whole-scene road zone on lawful moving replay; "
            "no real traffic violation"
        ),
        source_provenance={
            "title": "Licensed moving excerpt with SYNTHETIC TEST road zone",
            "url": "https://commons.wikimedia.org/wiki/File:Street_traffic.webm",
            "author": "Editor",
            "license": "CC BY 3.0",
        },
        control_source_reference="replay://mission-fixture",
        model="models/yolox_s.onnx",
        source_consent=dict(
            granted=True,
            by="Editor / CC BY 3.0",
            date="2026-11-10",
            scope="Local test replay and inference",
            evidence="https://commons.wikimedia.org/wiki/File:Street_traffic.webm",
            licence="CC BY 3.0",
        ),
    )
    from app.services import camera_workers

    profile = root / "cameras" / f"mission-{cid.hex}.yaml"
    with profile.open("x") as handle:
        handle.write(yaml.safe_dump(cfg))
    profile.chmod(0o600)
    monkeypatch.setattr(camera_workers, "STATE_DIR", tmp_path / "supervisor")
    # Worker needs only scoped HMAC credentials, never DB/admin/master keys. Relative
    # pipeline scratch output lives inside this unique test directory as well.
    worker_env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("RS_", "S3_", "WANDB_", "DATABASE_URL"))
    }
    worker_env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")

    port = free_port()
    monkeypatch.setenv("RS_API_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("RS_INGEST_KEY_ID", key.key_id)
    monkeypatch.setenv("RS_INGEST_SECRET", key.secret)
    monkeypatch.setenv("RS_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    proc = None
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        log = (tmp_path / "worker.log").open("w+")

        def launch_worker():
            started = camera_browser(
                world.a.admin, tmp_path, monkeypatch, "start", api_port=port,
                config={"profile": profile.name},
            )
            child = camera_workers._children[f"{world.a.id}-{cid}"]
            assert started["pid"] == child.pid
            child_env = dict(
                item.split("=", 1)
                for item in Path(f"/proc/{child.pid}/environ").read_text().split("\0")
                if "=" in item
            )
            assert not any(name in child_env for name in (
                "RS_DATABASE_URL", "RS_ADMIN_DATABASE_URL", "RS_MASTER_KEY",
                "RS_TEST_ADMIN_DATABASE_URL",
            ))
            return child

        proc = launch_worker()
        deadline = time.monotonic() + 35
        ack = False
        operator = login(world.a.operator)
        previews = []
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                ack = bool(row and row.applied_revision == 1 and row.health == "healthy")
            response = operator.get(f"/api/cameras/{cid}/preview")
            if response.status_code == 200:
                previews.append(__import__("hashlib").sha256(response.content).hexdigest())
            if ack and len(set(previews)) >= 2:
                break
            time.sleep(1)
        log.flush()
        log.seek(0)
        assert ack, log.read()[-2000:]
        assert len(set(previews)) >= 2
        # A competing real process must lose the lease before opening another source.
        opened_before = len(connections)
        duplicate = subprocess.run(  # noqa: S603 - fixed local fixture executable, no shell
            [
                sys.executable,
                "-m",
                "roadsentinel.pipeline",
                str(profile),
                "--live",
                "--no-wandb",
            ],
            cwd=tmp_path,
            env={
                **worker_env,
                "RS_API_URL": f"http://127.0.0.1:{port}",
                "RS_INGEST_KEY_ID": key.key_id,
                "RS_INGEST_SECRET": key.secret,
                "RS_YOLOX_MODEL_PATH": model,
            },
            stdout=log,
            stderr=log,
            timeout=12,
        )
        assert duplicate.returncode != 0
        assert len(connections) == opened_before
        print("PASS duplicate real worker denied before source open")
        camera_browser(world.a.operator, tmp_path, monkeypatch, "preview", api_port=port)
        from app.models import Alert, Evidence
        from app.services.evidence import file_path

        deadline = time.monotonic() + 30
        incident = None
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                incident = db.scalar(
                    select(Alert).where(Alert.camera_id == cid).order_by(Alert.detected_at)
                )
            if incident is not None:
                break
            time.sleep(0.5)
        if incident is None:
            worker_log = camera_workers._paths(str(world.a.id), str(cid))[1].read_text()
            assert incident is not None, worker_log[-3500:]
        assert (
            incident.details["origin"] == "local_replay" and incident.details["synthetic"] is True
        )
        assert (
            incident.details["config_revision"] == 1 and incident.details["model_sha256"] == digest
        )
        with tenant_session(world.a.id) as db:
            evidence = db.scalars(select(Evidence).where(Evidence.alert_id == incident.id)).all()
            assert len(evidence) == 2
            assert all(
                file_path(item, "redacted").read_bytes().startswith(b"RSE1") for item in evidence
            )
        camera_browser(
            world.a.operator,
            tmp_path,
            monkeypatch,
            "event",
            api_port=port,
            config={"event_number": incident.number},
        )
        assert operator.get(f"/api/events/{incident.number}").json()["status"] == "rejected"
        print(
            "PASS actual model -> synthetic-zone candidate -> signed managed ingest -> "
            "encrypted media -> browser rejection"
        )
        from app.services.package_verify import verify_package

        note = operator.post(
            f"/api/events/{incident.number}/notes",
            {
                "kind": "observation",
                "body": "SYNTHETIC TEST: real model on licensed replay with artificial zone",
            },
        )
        assert note.status_code == 201
        exported = operator.post(
            f"/api/events/{incident.number}/exports",
            {
                "justification": (
                    "Verify managed synthetic-zone replay evidence with independent approval"
                ),
                "case_reference": "MANAGED-SYNTHETIC",
                "idempotency_key": "managed-test-export-01",
            },
        )
        assert exported.status_code == 201, exported.text
        job = exported.json()
        assert operator.post(f"/api/approvals/{job['approval_id']}/approve").status_code == 403
        assert (
            administrator.post(
                f"/api/approvals/{job['approval_id']}/approve",
                {"note": "Independent licensed synthetic replay verification"},
            ).status_code
            == 200
        )
        package_job = operator.post(f"/api/exports/{job['id']}/run")
        assert package_job.status_code == 200 and package_job.json()["state"] == "completed"
        link = operator.post(f"/api/exports/{job['id']}/link")
        assert link.status_code == 200
        downloaded = operator.get(link.json()["url"])
        assert downloaded.status_code == 200
        package = tmp_path / "managed-case.zip"
        package.write_bytes(downloaded.content)
        verified = verify_package(
            package, package_job.json()["manifest_sha256"], max_uncompressed=100 * 1024 * 1024
        )
        assert verified.ok and verified.files_checked >= 2
        print(
            "PASS managed model-derived synthetic-zone case note, independent export "
            "and ZIP hash verification"
        )
        updated = dict(config, min_y=10)
        activated = publish_configuration(updated)
        assert activated["version"]["revision"] == 2
        proc.wait(timeout=15)
        assert proc.returncode == 0
        proc = launch_worker()
        deadline = time.monotonic() + 25
        applied = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                applied = bool(row and row.applied_revision == 2 and row.health == "healthy")
            if applied:
                break
            time.sleep(0.5)
        assert applied
        print(
            "PASS actual configuration API: independent approval, revision 1 -"
            "> 2, old worker stopped, fresh lease + ACK revision 2"
        )
        # Interrupt only sockets accepted by this test-owned source. Keep control/API up.
        disconnect.set()
        for connection in list(connections):
            with suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
        deadline = time.monotonic() + 12
        degraded = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                degraded = bool(row and row.health == "reconnecting")
            if degraded:
                break
            time.sleep(0.5)
        assert degraded
        assert operator.get(f"/api/cameras/{cid}/preview").status_code == 404
        camera_browser(
            world.a.admin, tmp_path, monkeypatch, "health", api_port=port,
            config={"expected": "reconnecting"}, revision=1,
        )
        disconnect.clear()
        deadline = time.monotonic() + 25
        recovered = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                healthy = bool(row and row.health == "healthy")
            fresh = operator.get(f"/api/cameras/{cid}/preview")
            if healthy and fresh.status_code == 200:
                recovered = True
                break
            time.sleep(0.5)
        assert recovered
        camera_browser(
            world.a.admin, tmp_path, monkeypatch, "health", api_port=port,
            config={"expected": "replay"}, revision=2,
        )
        print(
            "PASS controlled source disconnect: reconnecting, stale preview ex"
            "pired, recovered actual frames"
        )
        # Kill only the subprocess created above; exercise the real90-second lease TTL.
        with tenant_session(world.a.id) as db:
            row = db.scalar(select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid))
            dead_epoch, expires = row.lease_epoch, row.lease_expires_at
        proc.kill()
        proc.wait(timeout=10)
        print(
            "Testing owned worker SIGKILL and real lease expiry; no policy/time shortcuts",
            flush=True,
        )
        while datetime.now(UTC) <= expires:
            time.sleep(min(1.0, max(0.05, (expires - datetime.now(UTC)).total_seconds())))
        status = administrator.get(base).json()
        assert status["runtime"]["state"] in {"stale", "offline"}
        assert operator.get(f"/api/cameras/{cid}/preview").status_code == 404
        proc = launch_worker()
        deadline = time.monotonic() + 30
        reacquired = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                reacquired = bool(
                    row
                    and row.lease_epoch != dead_epoch
                    and row.applied_revision == 2
                    and row.health == "healthy"
                )
            if reacquired and operator.get(f"/api/cameras/{cid}/preview").status_code == 200:
                break
            time.sleep(0.5)
        assert reacquired
        print(
            "PASS actual worker SIGKILL -> stale/expired preview -> natural lease expiry -> "
            "fresh epoch/ACK/frames"
        )
        disabled = administrator.post(
            base + "/disable",
            {
                "expected_revision": revision(),
                "reason": "Stop capture after successful recovery verification",
            },
        )
        assert disabled.status_code == 200, disabled.text
        with tenant_session(world.a.id) as db:
            accepted_at_disable = len(
                db.scalars(select(Alert.id).where(Alert.camera_id == cid)).all()
            )
        proc.wait(timeout=12)
        with tenant_session(world.a.id) as db:
            assert (
                len(db.scalars(select(Alert.id).where(Alert.camera_id == cid)).all())
                == accepted_at_disable
            )
        assert proc.returncode == 0  # supervisor may restart; restart cannot acquire after disable
        requested = administrator.post(
            base + "/enable-request",
            {"expected_revision": revision(), "reason": "Request reviewed local replay recovery"},
        )
        assert requested.status_code == 200, requested.text
        assert (
            administrator.post(
                base + "/enable",
                {"expected_revision": revision(), "reason": "Self enable must be refused"},
            ).status_code
            == 403
        )
        enabled = reviewer.post(
            base + "/enable",
            {"expected_revision": revision(), "reason": "Independent enable after tested disable"},
        )
        assert enabled.status_code == 200, enabled.text
        proc = launch_worker()
        deadline = time.monotonic() + 25
        ready = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                ready = bool(row and row.applied_revision == 2 and row.health == "healthy")
            if ready:
                break
            time.sleep(0.5)
        assert ready
        camera_browser(world.a.admin, tmp_path, monkeypatch, "rollback", revision=1)
        proc.wait(timeout=15)
        assert proc.returncode == 0
        proc = launch_worker()
        deadline = time.monotonic() + 30
        rolled_back = False
        while time.monotonic() < deadline and proc.poll() is None:
            with tenant_session(world.a.id) as db:
                row = db.scalar(
                    select(CameraWorkerStatus).where(CameraWorkerStatus.camera_id == cid)
                )
                rolled_back = bool(row and row.applied_revision == 1 and row.health == "healthy")
            if rolled_back:
                break
            time.sleep(0.5)
        assert rolled_back
        camera_browser(world.a.admin, tmp_path, monkeypatch, "disable", api_port=port)
        proc.wait(timeout=15)
        assert proc.returncode == 0
        print("PASS independent re-enable -> new lease/ACK -> real processing -> final pause")
        print(
            "LOCAL RECORDED REPLAY: actual YOLOX/ByteTrack -> managed lease + "
            "ACK revision 1 -> changing authenticated preview -> stop on disab"
            "le"
        )
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        camera_workers.stop(str(world.a.id), str(cid), timeout_s=2)
        profile.unlink()
        replay.shutdown()
        replay.server_close()
        server.should_exit = True
        thread.join(10)
        get_settings.cache_clear()
