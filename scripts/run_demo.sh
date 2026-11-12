#!/usr/bin/env bash
# Processes every demo camera (VLM check runs inline when ANTHROPIC_API_KEY is set) and serves the dashboard on :8000.
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/download_data.sh
for cam in cameras/*.yaml; do
  .venv/bin/python -m roadsentinel.pipeline "$cam" "$@"
done
exec .venv/bin/uvicorn roadsentinel.server:app --port 8000
