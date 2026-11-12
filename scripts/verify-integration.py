#!/usr/bin/env python3
"""Run integration tests on a NEW owned PostgreSQL cluster; never the existing app DB."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = Path("/home/justin7m8/miniconda3/envs/rs-pg/bin")
NODE = Path("/home/justin7m8/miniconda3/envs/rs-node22/bin")
PYTHON = ROOT / ".venv.integration/bin/python"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "suite", choices=["incremental", "auth", "flows", "backend", "browser", "camera", "pipeline", "frontend", "pwa"]
    )
    ap.add_argument("--evidence-root", type=Path, default=ROOT / "docs/audits/runtime_verification/runs")
    args = ap.parse_args()
    if ROOT != Path("/home/justin7m8/Documents/roadsentinel-integration"):
        raise SystemExit("Unexpected integration workspace")
    tag = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    evidence_root = args.evidence_root.resolve()
    if not evidence_root.is_relative_to(ROOT / "docs/audits"):
        raise SystemExit("Evidence must remain under the integration audit directory")
    output = evidence_root / tag
    output.mkdir(parents=True)
    records = []
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PATH": str(NODE) + os.pathsep + os.environ["PATH"]}
    for key in list(env):
        if key.startswith(("RS_", "VITE_", "DATABASE_URL")):
            del env[key]
    env["RS_YOLOX_MODEL_PATH"] = os.environ.get(
        "RS_YOLOX_MODEL_PATH", str(ROOT.parent / "roadsentinel/models/yolox_s.onnx")
    )

    def run(command, cwd, name, timeout=300):
        start = datetime.now(UTC).isoformat()
        at = time.monotonic()
        with (output / (name + ".log")).open("w") as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=log, timeout=timeout, check=False)
        records.append(
            {
                "name": name,
                "command": command,
                "cwd": str(cwd),
                "start": start,
                "end": datetime.now(UTC).isoformat(),
                "duration_s": round(time.monotonic() - at, 3),
                "exit_code": result.returncode,
            }
        )
        (output / "commands.json").write_text(json.dumps(records, indent=2))
        print(name, "exit", result.returncode, "log", output / (name + ".log"), flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)

    if args.suite in ("incremental", "auth", "backend", "flows", "browser", "camera"):
        if args.suite != "auth" and not Path("/tmp/Street_traffic.webm").is_file():
            raise SystemExit("Licensed local fixture /tmp/Street_traffic.webm is required; no download attempted")
        with tempfile.TemporaryDirectory(prefix="rsverify-") as temporary:
            root = Path(temporary)
            data = root / "pg"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            if port in (55432, 55444, 55446, 55479, 55481):
                raise SystemExit("Refusing a protected or existing test port")
            role = "rsverify_root"
            db = "rsmission_verify_" + uuid.uuid4().hex[:10]
            env.update(
                RS_TEST_ADMIN_DATABASE_URL=f"postgresql+psycopg://{role}@127.0.0.1:{port}/postgres",
                RS_TEST_DATABASE_NAME=db,
                RS_TEST_ALLOW_DATABASE_RESET=db,
                RS_TEST_EXPECTED_PORT=str(port),
                RS_MISSION_REAL="1",
                RS_MISSION_EVIDENCE_DIR=str(output),
                PYTHONPATH=str(ROOT),
            )
            (output / "database.json").write_text(
                json.dumps(
                    {
                        "runtime": "B: new disposable cluster",
                        "root": str(root),
                        "port": port,
                        "role": role,
                        "database": db,
                    },
                    indent=2,
                )
            )
            run(
                [str(PG / "initdb"), "-D", str(data), "-U", role, "-A", "trust", "--encoding=UTF8", "--no-locale"],
                ROOT,
                "initdb",
            )
            started = False
            try:
                run(
                    [
                        str(PG / "pg_ctl"),
                        "-D",
                        str(data),
                        "-l",
                        str(root / "postgres.log"),
                        "-o",
                        f"-h 127.0.0.1 -p {port} -k {root}",
                        "start",
                    ],
                    ROOT,
                    "start",
                )
                started = True
                targets = (
                    ["tests"]
                    if args.suite == "backend"
                    else [
                        "tests/test_lookup_ownership.py",
                        "tests/test_seed.py",
                        "tests/test_auth.py",
                        "tests/test_mission_vertical.py",
                        "tests/test_managed_live_runtime.py",
                        "tests/test_browser_complete_journey.py",
                    ]
                )
                if args.suite == "browser":
                    targets = ["tests/test_browser_complete_journey.py"]
                elif args.suite == "camera":
                    targets = ["tests/test_managed_live_runtime.py"]
                elif args.suite == "auth":
                    targets = ["tests/test_lookup_ownership.py", "tests/test_seed.py", "tests/test_auth.py"]
                elif args.suite == "incremental":
                    targets = [
                        "tests/test_incremental_security.py",
                        "tests/test_contract_api.py",
                        "tests/test_contract_ingest.py",
                        "tests/test_notifications.py",
                    ]
                run(
                    [str(PYTHON), "-m", "pytest", *targets, "-o", "addopts=", "-q", "-s"],
                    ROOT / "backend",
                    args.suite,
                    timeout=600,
                )
                run(
                    [
                        str(PYTHON),
                        "-c",
                        """
import json, os, psycopg
from sqlalchemy.engine import make_url
u=make_url(os.environ['RS_TEST_ADMIN_DATABASE_URL']).set(database=os.environ['RS_TEST_DATABASE_NAME'])
with psycopg.connect(u.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://'), autocommit=True) as c:
    identity=c.execute('SELECT current_database(),host(inet_server_addr()),inet_server_port(),current_user').fetchone()
    assert identity[0]==os.environ['RS_TEST_DATABASE_NAME'] and str(identity[2])==os.environ['RS_TEST_EXPECTED_PORT']
    revision=c.execute('SELECT version_num FROM alembic_version').fetchall()
    tables=c.execute("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND (relname='tenants' OR EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=pg_class.oid AND a.attname='tenant_id' AND NOT a.attisdropped)) ORDER BY relname").fetchall()
    roles=c.execute("SELECT rolname,rolsuper,rolbypassrls FROM pg_roles WHERE rolname IN ('rs_test_owner','rs_test_app') ORDER BY rolname").fetchall()
    assert revision==[('0028',)] and len(tables)==37 and all(row[1] and row[2] for row in tables)
    print(json.dumps(dict(identity=identity,revision=revision,tenant_tables=tables,roles=roles),indent=2),flush=True)
    assert len(roles)==2 and all(not row[1] for row in roles)
    assert next(row for row in roles if row[0]=='rs_test_app')==('rs_test_app',False,False)
    # The disposable bootstrap migrator retains its documented pre-0022 BYPASSRLS; never used by API.
""",
                    ],
                    ROOT,
                    "schema-security",
                )
            finally:
                if started:
                    # Refuse shutdown of anything other than this freshly created PGDATA.
                    if data.parent != root or not root.name.startswith("rsverify-"):
                        raise RuntimeError("Owned cluster cleanup identity mismatch")
                    run([str(PG / "pg_ctl"), "-D", str(data), "stop", "-m", "fast"], ROOT, "stop")
    elif args.suite == "pipeline":
        run([str(PYTHON), "-m", "pytest", "tests", "-o", "addopts=", "-q"], ROOT, "pipeline")
    else:
        folder = ROOT / ("frontend" if args.suite == "frontend" else "secure-pwa")
        for name, command in [
            ("test", ["npm", "run", "test"]),
            ("lint", ["npm", "run", "lint"]),
            ("build", ["npm", "run", "build", "--", "--outDir", str(output / "build")]),
        ]:
            run(command, folder, name)


if __name__ == "__main__":
    main()
