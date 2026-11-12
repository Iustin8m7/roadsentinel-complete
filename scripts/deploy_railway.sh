#!/usr/bin/env bash
# Deploy the secure backend and the web gateway to Railway (manual, never automatic).
# MFA stays mandatory; no demo accounts are created here (users come from invitations). Works without rsync (Git Bash on Windows).
#
#   bash scripts/deploy_railway.sh
#
# Needs: railway CLI logged in and linked to project "roadsentinel" / environment "production",
# and an SSH key registered with Railway for the accounts step (railway ssh keys add).
set -euo pipefail
cd "$(dirname "$0")/.."

wait_ok() {  # wait_ok <service>
  for _ in $(seq 1 90); do
    s=$(railway deployment list --service "$1" --json | python -c "import sys,json;print(json.load(sys.stdin)[0]['status'])")
    case "$s" in SUCCESS) echo "$1: $s"; return 0;; FAILED|CRASHED) echo "$1: $s" >&2; return 1;; esac
    sleep 10
  done
  echo "$1: timed out" >&2; return 1
}

echo "== secure backend"
S=$(mktemp -d)
git archive HEAD backend scripts | tar -x -C "$S"
rm -rf "$S/backend/tests"
sed '/^CMD \[/,$d' backend/Dockerfile > "$S/Dockerfile"
cat >> "$S/Dockerfile" <<'EOF'
CMD ["sh", "-c", "python -m app.cli migrate && exec uvicorn app.main:create_app --factory --host :: --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips \"*\" --no-server-header"]
EOF
railway up "$S" --path-as-root --service secure-api --detach --message "backend"
wait_ok secure-api

echo "== web gateway"
W=$(mktemp -d)
git archive HEAD frontend deploy/railway-web | tar -x -C "$W"
cp deploy/railway-web/Dockerfile "$W/Dockerfile"
railway up "$W" --path-as-root --service web --detach --message "web"
wait_ok web

echo "done. Create users with invitations (tenant admin) or the CLI; see docs/OPERATIONS.md."
