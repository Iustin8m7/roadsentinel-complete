#!/usr/bin/env python3
"""Start or restart only verified integration development services, bound to loopback."""

import argparse
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "backend/.integration-runtime"


def settings():
    result = {}
    for line in (ROOT / "backend/.env.integration.local").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            tokens = shlex.split(value, comments=True)
            result[key] = tokens[0] if tokens else ""
    return result


def live(port):
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def owned(pid, kind):
    cwd = Path(f"/proc/{pid}/cwd").resolve()
    args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    values = [x.decode() for x in args if x]
    folder = ROOT / ("backend" if kind == "backend" else "frontend")
    port = "8003" if kind == "backend" else "5175"
    if (
        cwd != folder
        or port not in values
        or not any(("uvicorn" if kind == "backend" else "vite") in x for x in values)
    ):
        raise RuntimeError("PID does not belong to the expected integration service")
    if Path(f"/proc/{pid}").stat().st_uid != os.getuid():
        raise RuntimeError("Service belongs to another OS user")
    env = dict(x.split("=", 1) for x in Path(f"/proc/{pid}/environ").read_text().split("\0") if "=" in x)
    if kind == "backend":
        u = urlsplit(env.get("RS_DATABASE_URL", ""))
        if (u.hostname, u.port, u.path) != ("127.0.0.1", 55446, "/rsint_20261110b"):
            raise RuntimeError("Backend runtime DB identity mismatch")
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("service", choices=["backend", "frontend"])
    ap.add_argument("--restart-pid", type=int)
    args = ap.parse_args()
    kind = args.service
    port = 8003 if kind == "backend" else 5175
    env = os.environ.copy()
    if args.restart_pid:
        env = owned(args.restart_pid, kind)
        os.kill(args.restart_pid, signal.SIGTERM)
        for _ in range(200):
            if not live(port):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Owned service did not release its port; no replacement launched")
    if live(port):
        raise RuntimeError("Port already occupied; refusing a competing service")
    STATE.mkdir(mode=0o700, exist_ok=True)
    if kind == "backend":
        env.update(settings())
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "backend"), str(ROOT)])
        env.setdefault("RS_YOLOX_MODEL_PATH", str(ROOT.parent / "roadsentinel/models/yolox_s.onnx"))
        python = ROOT / ".venv.integration/bin/python"
        if not (ROOT / ".venv.integration/.ready").exists():
            python = Path("/tmp/rsint-venv/bin/python")
        if not python.is_file():
            raise RuntimeError("Install requirements.integration-test.txt in .venv.integration first")
        command = [
            str(python),
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8003",
            "--no-access-log",
        ]
    else:
        env = {k: v for k, v in env.items() if not k.startswith(("RS_", "VITE_"))}
        env.update(RS_API_ORIGIN="http://127.0.0.1:8003", VITE_USE_MOCKS="0")
        node = Path("/home/justin7m8/miniconda3/envs/rs-node22/bin/node")
        command = [
            str(node) if node.is_file() else shutil.which("node"),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "5175",
            "--strictPort",
        ]
    path = STATE / f"{kind}.log"
    with path.open("ab") as log:
        path.chmod(0o600)
        child = subprocess.Popen(
            command, cwd=ROOT / kind, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True
        )
    (STATE / f"{kind}.json").write_text(json.dumps({"pid": child.pid, "port": port, "cwd": str(ROOT / kind)}))
    for _ in range(200):
        if child.poll() is not None:
            raise RuntimeError("Integration service exited; inspect private service log")
        if live(port):
            print(f"{kind} started PID={child.pid} http://127.0.0.1:{port}")
            return
        time.sleep(0.1)
    raise RuntimeError("Integration service did not become reachable")


if __name__ == "__main__":
    main()
