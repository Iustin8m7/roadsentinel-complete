#!/usr/bin/env bash
# Backup of the database (pg_dump custom format) and the evidence store, with checksums.
#
#   RS_BACKUP_DATABASE_URL=postgresql://user:pass@host:5432/roadsentinel \
#   RS_EVIDENCE_DIR=/data/evidence  scripts/backup.sh /backups/2026-11-05
#
# Needs pg_dump on PATH. Evidence is ciphertext (AES-GCM): a backup of it is useless without the
# master keys (RS_MASTER_KEYS), which are NOT included: store them separately (docs/OPERATIONS.md).
# With S3/R2 evidence storage (RS_EVIDENCE_S3_BUCKET) use bucket versioning / replication instead.
set -euo pipefail
OUT=${1:?usage: backup.sh <target-dir>}
: "${RS_BACKUP_DATABASE_URL:?set RS_BACKUP_DATABASE_URL (a role that can read every table, e.g. the owner)}"
mkdir -p "$OUT"
umask 077
pg_dump --format=custom --no-owner --file "$OUT/db.dump" "$RS_BACKUP_DATABASE_URL"
if [ -n "${RS_EVIDENCE_DIR:-}" ] && [ -d "$RS_EVIDENCE_DIR" ]; then
  tar -C "$RS_EVIDENCE_DIR" -czf "$OUT/evidence.tar.gz" .
fi
( cd "$OUT" && sha256sum db.dump $( [ -f evidence.tar.gz ] && echo evidence.tar.gz ) > SHA256SUMS )
echo "backup written to $OUT"; cat "$OUT/SHA256SUMS"
