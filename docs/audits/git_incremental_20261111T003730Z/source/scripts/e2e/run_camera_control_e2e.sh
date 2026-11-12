#!/usr/bin/env bash
# A18: camera control plane end to end on a DISPOSABLE local stack.
#
#   PG_PORT=55441 API_PORT=8441 WEB_PORT=5441 scripts/e2e/run_camera_control_e2e.sh
#
# Needs a throwaway PostgreSQL superuser at localhost:$PG_PORT (postgres/postgres), e.g.
#   docker run -d --rm --name rs-e2e-pg -e POSTGRES_PASSWORD=postgres -p 55441:5432 postgres:16-alpine
# The database $E2E_DB on that server is DROPPED and recreated. Secrets are generated per run
# (test-only, never written to disk). No third-party camera is contacted: the source is a local
# recording reference and the worker reads only $E2E_VIDEO.
#
# Steps: bootstrap + migrate + seed + demo accounts (+ a second admin), start the API, run the
# API/worker harness (scripts/e2e/camera_control_e2e.py), RESTART the API (status must survive),
# build the UI, serve it with `vite preview` proxied to the API, run the headless browser check
# (frontend/scripts/e2e-camera-control.mjs) and the visual editor check
# (frontend/scripts/e2e-config-editor.mjs, two administrators and a worker pass). Servers are
# stopped on exit.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
PG_PORT=${PG_PORT:-55441}
API_PORT=${API_PORT:-8441}
WEB_PORT=${WEB_PORT:-5441}
E2E_DB=${E2E_DB:-rs_e2e_camera_control}
BACKEND_PY=${BACKEND_PY:-$HOME/token/backend/.venv/bin/python}
ROOT_PY=${ROOT_PY:-$HOME/token/.venv/bin/python}
E2E_VIDEO=${E2E_VIDEO:-$HOME/token/data/videos/vehicles-2.mp4}
ARTIFACTS=${E2E_ARTIFACTS:-$(mktemp -d)}
LOGS=$(mktemp -d)

secret() { "$BACKEND_PY" -c 'import secrets; print(secrets.token_urlsafe(32))'; }
export RS_ENV=development
export RS_ADMIN_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:${PG_PORT}/postgres"
export RS_MIGRATOR_DATABASE_URL="postgresql+psycopg://rs_e2e_owner:$(secret)@localhost:${PG_PORT}/${E2E_DB}"
export RS_DATABASE_URL="postgresql+psycopg://rs_e2e_app:$(secret)@localhost:${PG_PORT}/${E2E_DB}"
export RS_JWT_SECRET=$(secret) RS_URL_SIGNING_KEY=$(secret)
export RS_MASTER_KEYS="1:$("$BACKEND_PY" -c 'import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export RS_MASTER_KEY_CURRENT=1 RS_EVIDENCE_DIR=$(mktemp -d) RS_SEED_PASSWORD=$(secret)
export RS_PUBLIC_ORIGIN="http://localhost:${WEB_PORT}" RS_COOKIE_SECURE=false
E2E_PASSWORD=$(secret)
API_PID="" WEB_PID=""
cleanup() {
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT

echo "[e2e] fresh database ${E2E_DB} on localhost:${PG_PORT}"
"$BACKEND_PY" - <<PY
import psycopg
with psycopg.connect("postgresql://postgres:postgres@localhost:${PG_PORT}/postgres", autocommit=True) as c:
    c.execute('DROP DATABASE IF EXISTS "${E2E_DB}" WITH (FORCE)')
PY
cd "$REPO/backend"
"$BACKEND_PY" -m app.cli bootstrap-db
"$BACKEND_PY" -m app.cli migrate >"$LOGS/migrate.log" 2>&1
"$BACKEND_PY" -m app.cli seed --users-only >/dev/null
"$BACKEND_PY" -m app.cli demo-accounts --tenant unit-a --password "$E2E_PASSWORD"
E2E_PASSWORD="$E2E_PASSWORD" "$BACKEND_PY" - <<'PY'
import os
from app.core.security import hash_password
from app.db import tenant_session
from app.models import Role, User
from app.services.seed import tenant_id_for_slug

tid = tenant_id_for_slug("unit-a")
with tenant_session(tid) as db:  # second administrator for four-eyes approval (demo, MFA-exempt)
    db.add(User(tenant_id=tid, email="admin2@roadsentinel.local", display_name="Administrator 2",
                role=Role.tenant_admin, password_hash=hash_password(os.environ["E2E_PASSWORD"]),
                is_active=True, mfa_enabled=False, mfa_exempt=True))
    db.commit()
print("[e2e] second administrator created")
PY

start_api() {
  (unset RS_ADMIN_DATABASE_URL; cd "$REPO/backend"; exec "$BACKEND_PY" -m uvicorn app.main:create_app --factory \
    --host 127.0.0.1 --port "$API_PORT" --no-server-header) >>"$LOGS/api.log" 2>&1 &
  API_PID=$!
  for _ in $(seq 1 100); do
    curl -fsS "http://localhost:${API_PORT}/api/health" >/dev/null 2>&1 && return 0
    sleep 0.2
  done
  cat "$LOGS/api.log"; return 1
}
start_api
echo "[e2e] API up on :${API_PORT}"

cd "$REPO"
"$ROOT_PY" scripts/e2e/camera_control_e2e.py --api "http://localhost:${API_PORT}" \
  --origin "http://localhost:${WEB_PORT}" --password "$E2E_PASSWORD" --video "$E2E_VIDEO" | tee "$LOGS/harness.log"
SUMMARY=$(tail -n 1 "$LOGS/harness.log")
CAMERA_ID=$("$ROOT_PY" -c 'import json,sys; print(json.loads(sys.argv[1])["camera_id"])' "$SUMMARY")

echo "[e2e] restarting the API: worker status must survive (it lives in PostgreSQL)"
kill "$API_PID"; wait "$API_PID" 2>/dev/null || true
start_api

cd "$REPO/frontend"
npm run build >"$LOGS/build.log" 2>&1
RS_API_PROXY="http://localhost:${API_PORT}" npx vite preview --host localhost --port "$WEB_PORT" --strictPort \
  >"$LOGS/web.log" 2>&1 &
WEB_PID=$!
for _ in $(seq 1 100); do curl -fsS "http://localhost:${WEB_PORT}/login" >/dev/null 2>&1 && break; sleep 0.2; done

E2E_BASE="http://localhost:${WEB_PORT}" E2E_PASSWORD="$E2E_PASSWORD" E2E_CAMERA_ID="$CAMERA_ID" \
  E2E_ARTIFACTS="$ARTIFACTS" node scripts/e2e-camera-control.mjs
# The visual editor: draw, validate, submit, four-eyes approval, activation, worker application, rollback.
E2E_BASE="http://localhost:${WEB_PORT}" E2E_PASSWORD="$E2E_PASSWORD" E2E_ARTIFACTS="$ARTIFACTS" \
  E2E_WORKER="$ROOT_PY $REPO/scripts/e2e/worker_once.py --api http://localhost:${API_PORT} --origin http://localhost:${WEB_PORT} --video $E2E_VIDEO" \
  node scripts/e2e-config-editor.mjs
echo "[e2e] screenshots: $ARTIFACTS  logs: $LOGS"
if grep -q -E "S3cr3t|password=|token=" "$LOGS/api.log"; then echo "[e2e] secret-looking text in API log"; exit 1; fi
