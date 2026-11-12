> Current runtime verification — 2026-11-10
> Existing integrated login is now VERIFIED with MFA on5175/8003/rsint_20261110b:55446 after backup/rehearsed narrow lookup-owner repair and0022. Use [FINAL_LOGIN_HANDOFF.md](FINAL_LOGIN_HANDOFF.md), [POST_INTEGRATION_RUNTIME_VERIFICATION.md](POST_INTEGRATION_RUNTIME_VERIFICATION.md) and [FULL_INTEGRATION_E2E_VALIDATION.md](FULL_INTEGRATION_E2E_VALIDATION.md).
> Historical observations below retain their original scope/date.

# Isolated native runbook

Do not point pytest at an existing developer DB. The current integration at http://127.0.0.1:5175/login and http://127.0.0.1:8003 has a confirmed lookup-owner configuration issue. Its credentials file is backend/.integration-test-credentials.json (never print). Existing databases are preserved.

## One-time isolated test setup

Use Python 3.12, Node >=22.12 and PostgreSQL binaries already installed. Create a unique test cluster (example; retain the printed path for shutdown):

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
TASK_DIR=$(mktemp -d /tmp/rsmission-XXXXXXXX)
PG_BIN=/home/justin7m8/miniconda3/envs/rs-pg/bin
"$PG_BIN/initdb" -D "$TASK_DIR/pg" -U postgres -A trust --encoding=UTF8 --no-locale
"$PG_BIN/pg_ctl" -D "$TASK_DIR/pg" -l "$TASK_DIR/pg.log" -o "-h 127.0.0.1 -p 55479 -k $TASK_DIR" start
```

Check that port 55479 is unused first. Trust auth is only for this loopback disposable cluster, never an operational setup. The test fixture proves identity and requires reset opt-in. A dedicated integration venv is preferred; use backend/requirements.lock and requirements.txt with supervision==0.30.7 and onnxruntime==1.23.2, then pytest/httpx. Do not install into the original .venv. This mission executed the already installed original interpreter read-only with PYTHONDONTWRITEBYTECODE=1; it did not install into that environment.

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55479/postgres \
RS_TEST_DATABASE_NAME=rsmission_demo RS_TEST_ALLOW_DATABASE_RESET=rsmission_demo \
RS_TEST_EXPECTED_PORT=55479 RS_MISSION_REAL=1 \
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \
PYTHONPATH=.. /home/justin7m8/Documents/roadsentinel/.venv/bin/python -m pytest tests/test_mission_vertical.py tests/test_managed_live_runtime.py -o addopts='' -q -s
```

Model is read-only from the approved local path; verify its registry SHA first. /tmp/Street_traffic.webm is the previously documented Editor CC BY 3.0 sample; no download or rights inference from a public camera URL. The recorded positive fixture intentionally freezes a licensed frame and is SYNTHETIC TEST, not a real obstruction.

## Standard integration UI start

After separately backed-up and guarded authentication repair, start only the integration backend from backend/ using its protected environment file, restricted role, and mandatory MFA. Do not paste secrets to terminal output. Existing processes are preserved by this mission.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/frontend
RS_API_ORIGIN=http://127.0.0.1:8003 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Only run this when no verified integration frontend already owns 5175. Backend canonical command from backend/: `python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8003`; load the protected integration environment without printing secrets. Do not run migrations/seed against the existing DB until backup, identity and migration review are complete. The earlier guarded repair script requires privileged role repair; this mission has not run it.

Sign in, enroll TOTP with QR/manual secret and save recovery codes privately. /app/analiza-video → permitted upload → confirm crop → analyze → candidate → enter reason → explicit review submission → /app/alerte/{id}. Verify RECORDED label and media, then human reject/confirm. Archive and case panels are existing routes; full browser journey is still an acceptance task, not an executed demo claim.

For managed replay use the existing private YAML source profile plus approved control configuration. `control_source_reference: replay://<registered-ref>` maps to a literal loopback stream, with `source_replay: true` and licensed scope. HMAC service account must be camera-scoped. Run `python -m roadsentinel.live <private-profile.yaml> --status <integration-owned-state-path>`; source/keys are local protected configuration, never doc literals. Worker refuses missing model/hash/config/permission, ACKs after actual decoded frame dimensions, and exits on revision/lease change. No automatically approved camera or secret-bearing canned production profile is provided.

Stop only owned test services with their handles; shutdown only `$TASK_DIR/pg` using pg_ctl. Never stop PostgreSQL 55446/55444/55432 or unrelated UI/API ports.

## Independently reproduced dedicated Python environment

The five new-flow/seed tests also passed with `/tmp/rsint-venv/bin/python` (5 passed in 27.91 s), independently of the original venv: OpenCV 4.12.0.88, NumPy 2.2.6, ONNX Runtime 1.23.2, Supervision 0.30.7, pytest 9.2.0, httpx 0.28.1. Exact reproducible dependency file is `requirements.integration-test.txt`.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
python3.12 -m venv .venv.integration
.venv.integration/bin/pip install -r requirements.integration-test.txt
```

Use `.venv.integration/bin/python` in the isolated test command above. This is a new integration-owned environment; never install into either original tree. Model/media paths remain read-only explicit inputs, not dependencies to download silently.
