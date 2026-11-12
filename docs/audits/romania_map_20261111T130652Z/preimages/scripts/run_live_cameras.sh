#!/usr/bin/env bash
# Run live camera pipelines into the app and restart any that exit.
#
#   scripts/run_live_cameras.sh <env-file> cameras/iasi-piata-unirii.yaml [more cameras...]
#
# The env file (keep it outside git) holds RS_API_URL, RS_INGEST_KEY_ID and RS_INGEST_SECRET
# of a service account: `python -m app.cli create-service-account --tenant unit-a --name ...`.
# Each camera must be registered first (`python -m app.cli register-camera ...`).
# Redaction is on (full) unless RS_REDACTION=off AND RS_ALLOW_UNREDACTED=1 are both set.
# Logs: $RS_LIVE_LOG_DIR (default ~/.roadsentinel/live-logs). Stop with Ctrl-C.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=${1:?usage: $0 <env-file> <camera.yaml>...}
shift
[ $# -gt 0 ] || { echo "no camera configs given" >&2; exit 2; }
set -a; . "$ENV_FILE"; set +a
export RS_REDACTION=${RS_REDACTION:-full} RS_EXPERIMENT_TRACKING=off RS_EXTERNAL_AI=${RS_EXTERNAL_AI:-off} PYTHONUNBUFFERED=1
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
LOG_DIR=${RS_LIVE_LOG_DIR:-$HOME/.roadsentinel/live-logs}
mkdir -p "$LOG_DIR"
# Keep the machine awake while cameras run (macOS).
KEEP_AWAKE=(); command -v caffeinate >/dev/null && KEEP_AWAKE=(caffeinate -i)

supervise() {
  local cfg=$1 log="$LOG_DIR/$(basename "$1" .yaml).log"
  while true; do
    echo "[$(date '+%F %T')] starting $cfg" >> "$log"
    ${KEEP_AWAKE[@]+"${KEEP_AWAKE[@]}"} "$PY" -m roadsentinel.pipeline "$cfg" --live --no-wandb >> "$log" 2>&1 || true
    echo "[$(date '+%F %T')] $cfg exited, restarting in 10 s" >> "$log"
    sleep 10
  done
}

trap 'kill 0' INT TERM
for cfg in "$@"; do
  supervise "$cfg" &
  echo "live: $cfg -> $LOG_DIR/$(basename "$cfg" .yaml).log"
done
wait
