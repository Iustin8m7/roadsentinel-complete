#!/usr/bin/env bash
# One-off setup of the demo data on the deployed secure backend (Railway service "secure-api").
# Run it yourself: it asks for the demo password, and the pipeline's HMAC secret is printed only
# in your terminal (copy it into prod.local.env as RS_INGEST_KEY_ID / RS_INGEST_SECRET).
#
# Needs an SSH key registered with Railway once:  railway ssh keys github   (or: railway ssh keys add)
#
# Creates: platform + Unit A + Unit B with one account per role (MFA enrollment on first login),
# the two demo cameras in Unit A (slugs from cameras/*.yaml), and a service account for the pipeline.
set -euo pipefail
SERVICE=secure-api
run() { railway ssh --service "$SERVICE" -- "$@"; }

read -r -s -p "Demo account password (min 12 chars, used for every seeded account): " PW; echo
[ ${#PW} -ge 12 ] || { echo "password too short" >&2; exit 1; }

# The API runs with RS_ENV=production, which refuses to seed; this one process is a dev seed.
run env RS_ENV=development RS_SEED_PASSWORD="$PW" python -m app.cli seed --users-only
run python -m app.cli register-camera --tenant unit-a --slug demo-highway \
  --name "Autostradă – cameră demo (pod pietonal)" --location "Demo highway, gantry km 12"
run python -m app.cli register-camera --tenant unit-a --slug demo-urban \
  --name "Bulevard subteran – cameră demo (pasaj)" --location "Demo urban expressway, overpass"
echo
echo "Pipeline credentials (shown once, store them in prod.local.env):"
run python -m app.cli create-service-account --tenant unit-a --name pipeline-laptop
