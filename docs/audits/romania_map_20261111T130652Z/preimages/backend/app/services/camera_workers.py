"""Local supervised camera pipeline processes.

The API accepts only a local YAML profile name, never a command or source URL. The profile is
validated by the same SourceSpec policy as the pipeline before a process is launched.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from roadsentinel.consent import ConsentError
from roadsentinel.sources import SourceError, SourceSpec

ROOT = Path(__file__).resolve().parents[3]
CAMERA_DIR = (ROOT / "cameras").resolve()
STATE_DIR = Path(
    os.environ.get(
        "RS_CAMERA_WORKER_STATE_DIR",
        str(Path(tempfile.gettempdir()) / "roadsentinel-camera-workers"),
    )
)
PROFILE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}\.ya?ml$")
_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()
_children: dict[str, subprocess.Popen[bytes]] = {}


def _lock(key: str) -> threading.RLock:
    with _locks_guard:
        return _locks.setdefault(key, threading.RLock())


def _paths(tenant_id: str, camera_id: str) -> tuple[Path, Path, str]:
    key = f"{tenant_id}-{camera_id}"
    safe = hashlib.sha256(key.encode()).hexdigest()[:24]
    return STATE_DIR / f"{safe}.json", STATE_DIR / f"{safe}.log", key


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _last_safe_error(path: Path) -> str | None:
    """Expose only known source diagnostics, never arbitrary pipeline log lines or URLs."""
    try:
        tail = path.read_bytes()[-12_000:].decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(tail.splitlines()):
        marker = "snapshot not processed:"
        if marker in line:
            message = line.split(marker, 1)[1].strip()
            message = re.sub(r"https?://\S+|rtsp[s]?://\S+", "[source URL redacted]", message)
            return message[:240]
    return None


def _write_state(path: Path, value: dict[str, Any]) -> None:
    _ensure_state_dir()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE_DIR.is_symlink() or not STATE_DIR.is_dir():
        raise RuntimeError("worker state path must be a private local directory")
    os.chmod(STATE_DIR, 0o700)
    if STATE_DIR.stat().st_uid != os.geteuid():
        raise RuntimeError("worker state directory must be owned by the API user")


def _profile(name: str, slug: str) -> tuple[Path, dict[str, Any], str]:
    if not PROFILE_NAME.fullmatch(name):
        raise ValueError("config_ref must be a local YAML filename")
    path = (CAMERA_DIR / name).resolve(strict=True)
    if path.parent != CAMERA_DIR or not path.is_file():
        raise ValueError("camera profile must be a regular file directly inside cameras/")
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError("camera profile could not be parsed") from exc
    if not isinstance(config, dict) or config.get("id") != slug:
        raise ValueError("camera profile id must match the tenant camera slug")
    try:
        spec = SourceSpec.from_camera(config)
    except ConsentError:
        raise ValueError(
            "camera profile policy validation failed: source processing permission is not recorded"
        ) from None
    except (SourceError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"camera profile policy validation failed: {exc}") from None
    if not spec.live_capture:
        raise ValueError("worker controls accept only a configured live camera source")
    model = config.get("model")
    if not isinstance(model, str) or not model or ".." in Path(model).parts:
        raise ValueError("camera profile must select a repository-local model")
    configured = os.environ.get('RS_YOLOX_MODEL_PATH')
    if model == 'models/yolox_s.onnx' and configured:
        from roadsentinel.models import ModelError, resolve_for_pipeline
        try:
            resolve_for_pipeline(config)
        except (OSError, ValueError, ModelError):
            raise ValueError('configured stock model is missing or its checksum differs') from None
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return path, config, digest
    model_path = (ROOT / model).resolve()
    if ROOT not in model_path.parents or not model_path.is_file():
        raise ValueError("configured model is missing or outside the repository")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, config, digest


def _process_alive(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()
        if len(fields) > 2 and fields[2] in {"Z", "X"}:
            return False
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, ValueError):
        return False
    return True


def _is_pipeline_process(pid: int, state: dict[str, Any]) -> bool:
    """Verify PID reuse did not turn a stale state record into a kill target."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = stat[stat.rfind(")") + 2 :].split()
        command = Path(f"/proc/{pid}/cmdline").read_bytes()
        profile = state.get("config_ref")
        expected = str((CAMERA_DIR / str(profile)).resolve()).encode()
        return (
            len(fields) > 2
            and int(fields[2]) == pid
            and b"-m\x00roadsentinel.pipeline\x00" in command
            and expected in command
        )
    except (OSError, ValueError):
        return False


def _owned_process(pid: int, key: str, state: dict[str, Any]) -> bool:
    child = _children.get(key)
    if child is not None and child.pid == pid:
        return True
    return _is_pipeline_process(pid, state)


def _operation_lock(key: str):
    _ensure_state_dir()
    safe = hashlib.sha256(key.encode()).hexdigest()[:24]
    handle = (STATE_DIR / f"{safe}.lock").open("a+b")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def status(tenant_id: str, camera_id: str, last_seen_at: datetime | None = None) -> dict[str, Any]:
    state_path, _, key = _paths(tenant_id, camera_id)
    with _lock(key):
        state = _read_state(state_path)
        if state is None:
            return {"state": "STOPPED", "desired_state": "STOPPED", "pid": None}
        pid = state.get("pid")
        child = _children.get(key)
        if child and child.poll() is not None:
            state["last_exit_code"] = child.returncode
            _write_state(state_path, state)
        alive = isinstance(pid, int) and _process_alive(pid)
        owned = alive and _owned_process(pid, key, state)
        desired = state.get("desired_state", "STOPPED")
        started_text = state.get("started_at")
        try:
            started = datetime.fromisoformat(started_text) if started_text else None
        except ValueError:
            started = None
        heartbeat_after_start = bool(
            last_seen_at and started and last_seen_at.astimezone(UTC) >= started.astimezone(UTC)
        )
        heartbeat_age_s = (
            max(0.0, (datetime.now(UTC) - last_seen_at.astimezone(UTC)).total_seconds())
            if last_seen_at
            else None
        )
        heartbeat_fresh = (
            heartbeat_age_s is not None
            and heartbeat_age_s <= float(state.get("heartbeat_timeout_s", 120))
        )
        if not alive:
            actual = "STOPPED" if desired == "STOPPED" else "ERROR"
        elif not owned:
            actual = "ERROR"
        elif desired == "STOPPED":
            actual = "STOPPING"
        elif heartbeat_after_start and heartbeat_fresh:
            actual = "RUNNING"
        elif started and (datetime.now(UTC) - started.astimezone(UTC)).total_seconds() < 30:
            actual = "STARTING"
        else:
            actual = "RECONNECTING"
        _, log_path, _ = _paths(tenant_id, camera_id)
        return {
            "state": actual,
            "desired_state": desired,
            "pid": pid if owned else None,
            "started_at": started_text,
            "config_version": state.get("config_version"),
            "heartbeat_age_s": heartbeat_age_s,
            "last_error": _last_safe_error(log_path),
            "last_exit_code": state.get("last_exit_code") if not alive else None,
            "log_file": str(log_path),
        }


def start(tenant_id: str, camera_id: str, slug: str, config_ref: str) -> dict[str, Any]:
    profile, config, version = _profile(config_ref, slug)
    heartbeat_timeout_s = float(config.get("heartbeat_max_idle_s", 120))
    if not 15 <= heartbeat_timeout_s <= 600:
        raise ValueError("heartbeat_max_idle_s must be between 15 and 600 seconds")
    api_url = os.environ.get("RS_API_URL", "")
    parsed_api = urlsplit(api_url)
    if (
        parsed_api.scheme not in {"http", "https"}
        or parsed_api.hostname not in {"localhost", "127.0.0.1", "::1"}
        or not all(os.environ.get(key) for key in ("RS_INGEST_KEY_ID", "RS_INGEST_SECRET"))
    ):
        raise ValueError(
            "local worker requires a localhost RS_API_URL and configured scoped ingest credentials"
        )
    state_path, log_path, key = _paths(tenant_id, camera_id)
    operation_lock = _operation_lock(key)
    try:
        with _lock(key):
            current = _read_state(state_path)
            if current and isinstance(current.get("pid"), int) and _process_alive(current["pid"]):
                if not _owned_process(current["pid"], key, current):
                    raise ValueError("stale worker PID does not match the configured pipeline")
                if current.get("config_version") != version:
                    raise ValueError("worker already runs another config version; use restart")
                return status(tenant_id, camera_id)
            _ensure_state_dir()
            log = log_path.open("ab", buffering=0)
            # The inference child talks only to signed ingest. It must never inherit
            # database credentials, evidence master keys, session keys or cloud tokens.
            env = _worker_environment()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            command = [
                sys.executable,
                "-m",
                "roadsentinel.pipeline",
                str(profile),
                "--live",
                "--no-wandb",
            ]
            work = STATE_DIR / (state_path.stem + "-work")
            work.mkdir(mode=0o700, exist_ok=True)
            env["RS_PIPELINE_WORK_DIR"] = str(work.resolve())
            try:
                # The executable and arguments are fixed; profile is resolved under cameras/ above.
                child = subprocess.Popen(  # noqa: S603 - fixed executable; profile is allowlisted
                    command,
                    cwd=ROOT,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    close_fds=True,
                    start_new_session=True,
                )
            finally:
                log.close()
            started = datetime.now(UTC).isoformat()
            _children[key] = child
            _write_state(
                state_path,
                {
                    "pid": child.pid,
                    "tenant_id": tenant_id,
                    "camera_id": camera_id,
                    "owner_api_pid": os.getpid(),
                    "desired_state": "RUNNING",
                    "started_at": started,
                    "config_ref": config_ref,
                    "config_version": version,
                    "heartbeat_timeout_s": heartbeat_timeout_s,
                },
            )
            time.sleep(0.15)
            result = status(tenant_id, camera_id)
            if child.poll() is not None:
                state = _read_state(state_path) or {}
                state.update(last_exit_code=child.returncode)
                _write_state(state_path, state)
                result = status(tenant_id, camera_id)
            return result
    finally:
        fcntl.flock(operation_lock.fileno(), fcntl.LOCK_UN)
        operation_lock.close()


def _worker_environment() -> dict[str, str]:
    allowed = {
        "PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TZ", "TMPDIR",
        "LD_LIBRARY_PATH", "CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONDONTWRITEBYTECODE",
        "RS_API_URL", "RS_INGEST_KEY_ID", "RS_INGEST_SECRET",
        "RS_YOLOX_MODEL_PATH", "RS_ONNX_PROVIDER",
    }
    return {key: value for key, value in os.environ.items() if key in allowed}


def stop(tenant_id: str, camera_id: str, *, timeout_s: float = 8) -> dict[str, Any]:
    state_path, _, key = _paths(tenant_id, camera_id)
    operation_lock = _operation_lock(key)
    try:
        with _lock(key):
            state = _read_state(state_path)
            if state is None:
                return {"state": "STOPPED", "desired_state": "STOPPED", "pid": None}
            pid = state.get("pid")
            state["desired_state"] = "STOPPED"
            _write_state(state_path, state)
            if isinstance(pid, int) and _process_alive(pid) and _owned_process(pid, key, state):
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(pid, signal.SIGTERM)
                deadline = time.monotonic() + timeout_s
                while time.monotonic() < deadline and _process_alive(pid):
                    time.sleep(0.1)
                if _process_alive(pid):
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(pid, signal.SIGKILL)
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline and _process_alive(pid):
                        time.sleep(0.05)
            if isinstance(pid, int) and _process_alive(pid) and _owned_process(pid, key, state):
                return {"state": "STOPPING", "desired_state": "STOPPED", "pid": pid}
            child = _children.pop(key, None)
            if child:
                try:
                    child.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    return {"state": "STOPPING", "desired_state": "STOPPED", "pid": pid}
            state["pid"] = None
            state["stopped_at"] = datetime.now(UTC).isoformat()
            _write_state(state_path, state)
            return status(tenant_id, camera_id)
    finally:
        fcntl.flock(operation_lock.fileno(), fcntl.LOCK_UN)
        operation_lock.close()


def restart(tenant_id: str, camera_id: str, slug: str, config_ref: str) -> dict[str, Any]:
    stop(tenant_id, camera_id)
    return start(tenant_id, camera_id, slug, config_ref)


def shutdown_all() -> None:
    """Stop children owned by this API process during orderly local shutdown."""
    if not STATE_DIR.exists() or STATE_DIR.is_symlink():
        return
    for state_path in STATE_DIR.glob("*.json"):
        state = _read_state(state_path)
        if not state or state.get("owner_api_pid") != os.getpid():
            continue
        tenant_id, camera_id = state.get("tenant_id"), state.get("camera_id")
        if isinstance(tenant_id, str) and isinstance(camera_id, str):
            stop(tenant_id, camera_id)
