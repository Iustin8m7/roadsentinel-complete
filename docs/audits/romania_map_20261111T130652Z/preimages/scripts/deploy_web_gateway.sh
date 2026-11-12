#!/usr/bin/env bash
# Deploy the web gateway (police UI + dashboard + /api proxy) to the Railway service "web".
# Railway builds the Dockerfile at the root of the upload, so the needed folders are staged.
set -euo pipefail
cd "$(dirname "$0")/.."
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
rsync -a --exclude node_modules --exclude dist frontend "$STAGE/"
rsync -a web "$STAGE/"
mkdir -p "$STAGE/deploy" && rsync -a deploy/railway-web "$STAGE/deploy/"
cp deploy/railway-web/Dockerfile "$STAGE/Dockerfile"
railway up "$STAGE" --path-as-root --service web --detach --message "web gateway"
