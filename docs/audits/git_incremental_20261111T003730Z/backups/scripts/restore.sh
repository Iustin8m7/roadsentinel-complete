#!/usr/bin/env bash
# Restore a backup made by backup.sh into an EMPTY database (never over production).
#
#   RS_RESTORE_DATABASE_URL=postgresql://user:pass@host:5432/restored  scripts/restore.sh /backups/2026-11-05 [evidence-target-dir]
#
# Verifies the checksums first. Then check: python -m app.cli verify-audit --tenant <slug>, and open an alert.
set -euo pipefail
IN=${1:?usage: restore.sh <backup-dir> [evidence-target-dir]}
: "${RS_RESTORE_DATABASE_URL:?set RS_RESTORE_DATABASE_URL (an empty database)}"
( cd "$IN" && sha256sum -c SHA256SUMS )
pg_restore --no-owner --exit-on-error --dbname "$RS_RESTORE_DATABASE_URL" "$IN/db.dump"
if [ -f "$IN/evidence.tar.gz" ] && [ -n "${2:-}" ]; then
  mkdir -p "$2"; tar -C "$2" -xzf "$IN/evidence.tar.gz"
fi
echo "restored"
