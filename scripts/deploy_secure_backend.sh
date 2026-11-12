#!/usr/bin/env bash
# Deploy the secure backend (backend/) to the Railway service "secure-api".
#
#   scripts/deploy_secure_backend.sh bootstrap   # one-off: create DB roles + database, migrate
#   scripts/deploy_secure_backend.sh serve       # normal deploy: migrate, then run the API
#
# The repository root holds the prototype's Dockerfile and railway.json, so the backend is
# staged into a temporary folder (backend/, scripts/, a root Dockerfile) and uploaded from there.
#
# Evidence lives in the Railway bucket "evidence" (ciphertext only): the service needs
# RS_EVIDENCE_S3_{BUCKET,ENDPOINT,REGION,ACCESS_KEY_ID,SECRET_ACCESS_KEY} = ${{evidence.*}}.
# No volume is needed, so redeploys never lose evidence.
#
# Bootstrap needs RS_ADMIN_DATABASE_URL (superuser) on the service; the API refuses to start
# while that variable exists, so remove it right after bootstrapping:
#   railway variable delete RS_ADMIN_DATABASE_URL --service secure-api
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:?usage: $0 bootstrap|serve}
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

rsync -a --exclude .venv --exclude __pycache__ --exclude tests --exclude .pytest_cache \
  --exclude .mypy_cache --exclude .ruff_cache backend "$STAGE/"
rsync -a scripts "$STAGE/"

# Railway builds the Dockerfile at the root of the upload, so the backend's Dockerfile goes
# there with the command for this mode.
case "$MODE" in
  bootstrap)
    CMD='["sh", "-c", "python -m app.cli bootstrap-db && python -m app.cli migrate && echo BOOTSTRAP_DONE && sleep 86400"]' ;;
  serve)
    CMD='["sh", "-c", "python -m app.cli migrate && exec uvicorn app.main:create_app --factory --host :: --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips \"*\" --no-server-header"]' ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
sed '/^CMD \[/,$d' backend/Dockerfile > "$STAGE/Dockerfile"
echo "CMD $CMD" >> "$STAGE/Dockerfile"

railway up "$STAGE" --path-as-root --service secure-api --detach --message "secure backend ($MODE)"
