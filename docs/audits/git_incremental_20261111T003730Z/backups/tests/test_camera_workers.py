from __future__ import annotations

import subprocess
import sys
import uuid

import pytest

from backend.app.services import camera_workers as workers


def test_profile_is_local_and_slug_bound():
    with pytest.raises(ValueError, match="local YAML filename"):
        workers._profile("../README.md", "local-uvc-camera")
    with pytest.raises(ValueError, match="slug"):
        workers._profile("local-uvc.yaml", "another-camera")
    profile, config, digest = workers._profile("local-uvc.yaml", "local-uvc-camera")
    assert profile.name == "local-uvc.yaml"
    assert config["video"] == "device:0"
    assert len(digest) == 64


def test_supervisor_start_is_idempotent_and_stop_reaps_process(monkeypatch, tmp_path):
    real_popen = subprocess.Popen
    tenant_id, camera_id = str(uuid.uuid4()), str(uuid.uuid4())
    key = f"{tenant_id}-{camera_id}"
    monkeypatch.setattr(workers, "STATE_DIR", tmp_path)
    monkeypatch.setattr(workers, "_children", {})
    monkeypatch.setenv("RS_API_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("RS_INGEST_KEY_ID", "test-key")
    monkeypatch.setenv("RS_INGEST_SECRET", "test-secret")
    monkeypatch.setenv("RS_DATABASE_URL", "must-not-reach-worker")
    monkeypatch.setenv("RS_MASTER_KEY", "must-not-reach-worker")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-reach-worker")

    def launch(_command, **kwargs):
        assert "RS_DATABASE_URL" not in kwargs["env"]
        assert "RS_MASTER_KEY" not in kwargs["env"]
        assert "AWS_SECRET_ACCESS_KEY" not in kwargs["env"]
        assert kwargs["env"]["RS_INGEST_SECRET"] == "test-secret"
        assert __import__("pathlib").Path(kwargs["env"]["RS_PIPELINE_WORK_DIR"]).is_relative_to(tmp_path)
        return real_popen(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        )

    monkeypatch.setattr(workers.subprocess, "Popen", launch)
    first = workers.start(tenant_id, camera_id, "local-uvc-camera", "local-uvc.yaml")
    second = workers.start(tenant_id, camera_id, "local-uvc-camera", "local-uvc.yaml")
    assert first["pid"] == second["pid"]
    assert second["desired_state"] == "RUNNING"
    stopped = workers.stop(tenant_id, camera_id, timeout_s=1)
    assert stopped["state"] == "STOPPED"
    assert stopped["desired_state"] == "STOPPED"
    assert key not in workers._children
    restarted = workers.restart(tenant_id, camera_id, "local-uvc-camera", "local-uvc.yaml")
    assert restarted["state"] in {"STARTING", "RUNNING"}
    assert restarted["pid"] is not None
    assert workers.stop(tenant_id, camera_id, timeout_s=1)["state"] == "STOPPED"
    workers.start(tenant_id, camera_id, "local-uvc-camera", "local-uvc.yaml")
    workers.shutdown_all()
    assert workers.status(tenant_id, camera_id)["state"] == "STOPPED"


def test_profile_requires_enabled_source_and_model():
    with pytest.raises(ValueError, match="policy validation"):
        workers._profile("iasi-piata-unirii.yaml", "iasi-piata-unirii")


def test_worker_refuses_to_start_without_local_signed_ingest(monkeypatch, tmp_path):
    monkeypatch.setattr(workers, "STATE_DIR", tmp_path)
    for key in ("RS_API_URL", "RS_INGEST_KEY_ID", "RS_INGEST_SECRET"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="localhost RS_API_URL"):
        workers.start(str(uuid.uuid4()), str(uuid.uuid4()), "local-uvc-camera", "local-uvc.yaml")
