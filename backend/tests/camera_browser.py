"""Bounded browser harness for fixture-owned camera UI; never targets existing native services."""

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def camera_browser(actor, tmp_path, monkeypatch, task, api_port=None, config=None, revision=None):
    from app.config import get_settings
    from app.main import create_app

    root = Path(__file__).resolve().parents[2]
    ui_port = free_port()
    origin = f"http://127.0.0.1:{ui_port}"
    server = thread = None
    frontend = None
    result = tmp_path / f"camera-{task}.json"
    try:
        with monkeypatch.context() as settings:
            settings.setenv("RS_PUBLIC_ORIGIN", origin)
            settings.setenv("RS_COOKIE_SECURE", "false")
            get_settings.cache_clear()
            if api_port is None:
                from app.services import camera_workers

                if any(child.poll() is None for child in camera_workers._children.values()):
                    raise RuntimeError(
                        "Active workers require the same running API port in browser tasks"
                    )
                api_port = free_port()
                server = uvicorn.Server(
                    uvicorn.Config(create_app(), host="127.0.0.1", port=api_port, log_level="error")
                )
                thread = threading.Thread(target=server.run, daemon=True)
                thread.start()
                deadline = time.monotonic() + 15
                while not server.started and time.monotonic() < deadline:
                    time.sleep(0.05)
                assert server.started
            with (tmp_path / f"vite-{task}.log").open("wb") as log:
                node = "/home/justin7m8/miniconda3/envs/rs-node22/bin/node"
                frontend = subprocess.Popen(  # noqa: S603 - fixed local fixture executable, no shell
                    [
                        node,
                        "node_modules/vite/bin/vite.js",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(ui_port),
                        "--strictPort",
                    ],
                    cwd=root / "frontend",
                    env={
                        **os.environ,
                        "RS_API_ORIGIN": f"http://127.0.0.1:{api_port}",
                        "VITE_USE_MOCKS": "0",
                    },
                    stdout=log,
                    stderr=log,
                )
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    try:
                        if httpx.get(origin).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                output = Path(
                    os.environ.get(
                        "RS_MISSION_EVIDENCE_DIR", root / "docs/audits/runtime_verification"
                    )
                )
                assert output.resolve().is_relative_to(root)
                shot = output / f"screenshots/camera-{task}-{revision or 0}.png"
                shot.parent.mkdir(parents=True, exist_ok=True)
                browser = subprocess.run(  # noqa: S603 - fixed local fixture executable, no shell
                    [node, "e2e/camera-control-runtime.mjs"],
                    cwd=root / "frontend",
                    env={
                        **os.environ,
                        "RS_UI_ORIGIN": origin,
                        "RS_UI_USER": actor.email,
                        "RS_UI_PASSWORD": actor.password,
                        "RS_UI_TOTP": actor.totp(),
                        "RS_UI_TOTP_SECRET": actor.totp_secret,
                        "RS_UI_PYTHON": sys.executable,
                        "RS_CAMERA_TASK": task,
                        "RS_CAMERA_RESULT": str(result),
                        "RS_CAMERA_SESSION": str(
                            tmp_path
                            / (hashlib.sha256(actor.email.encode()).hexdigest() + "-session.json")
                        ),
                        "RS_CAMERA_CONFIG": json.dumps(config),
                        "RS_CAMERA_REVISION": str(revision or 0),
                        "RS_E2E_SCREENSHOT": str(shot),
                    },
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                failure = browser.stderr.replace(actor.password, "<redacted>")
                if actor.totp_secret:
                    failure = failure.replace(actor.totp_secret, "<redacted>")
                (tmp_path / f"browser-{task}.log").write_text(failure)
                assert browser.returncode == 0, failure[:1500] + failure[-1000:]
                print(browser.stdout.strip())
    finally:
        if frontend:
            frontend.terminate()
            frontend.wait(timeout=10)
        if server:
            server.should_exit = True
            thread.join(15)
        get_settings.cache_clear()
    if task in {"register", "visual", "recording", "draft", "approve", "start", "stop"}:
        return json.loads(result.read_text())
    return None
