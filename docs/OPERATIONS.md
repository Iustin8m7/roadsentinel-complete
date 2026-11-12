# Operations

Everything below was exercised on a Linux laptop against a local PostgreSQL 18.6 unless it says
**not run**. Docker, Railway and GitHub were not available during development of this branch.

## Processes
| Process | Command | Notes |
|---|---|---|
| API | `uvicorn app.main:create_app --factory` (from `backend/`) | one process: the rate limiter and the SSE polling are in-process |
| Migrations | `python -m app.cli migrate` | run before the API; `bootstrap-db` creates roles (needs the superuser URL) |
| Pipeline (per camera) | `python -m roadsentinel.live cameras/<id>.yaml ...` | Python supervisor: restarts with backoff, records the reason in `~/.roadsentinel/live-status.json`, stops on SIGTERM. Replaces the bash loop `scripts/run_live_cameras.sh` |
| Retention job | `python -m app.cli purge-evidence --tenant unit-a unit-b` (cron, daily) | run `--dry-run` first |
| Audit checkpoint (local development) | `python -m app.cli anchor-audit --tenant unit-a --anchor-file /var/lib/roadsentinel/audit.jsonl --signing-key /var/lib/roadsentinel/audit-ed25519.key` | keep the public key separately for `verify-audit-anchor`; same-host JSONL/key storage is not independent or immutable production anchoring |
| Nonce cleanup | `python -m app.cli purge-nonces` (cron, hourly) | |

## Health, metrics, what a human should be told about
* `GET /api/health` liveness (DB answers) · `GET /api/ready` readiness (DB + schema migrated; returns the schema version, 503 otherwise).
* `GET /api/metrics`: Prometheus text, **off unless `RS_METRICS_TOKEN` is set** (then `Authorization: Bearer`). Per-process counters: `rs_http_requests_total{method,status}`, `rs_ingest_events_total{result=accepted|duplicate}`, histogram `rs_ingest_store_seconds`.
* `GET /api/ops/status` (tenant admin): alerts in 24 h by type, unreviewed count, evidence files/purged, and per camera the heartbeat age, measured fps and the rules it **cannot** run at that rate.
* Logs: structured, secrets/tokens/plates redacted by a logging filter; the Caddy log drops cookies and auth headers.

Alert a person when (suggested thresholds; no alerting system is wired up in this repo):
1. `/api/ready` fails for > 1 min, or the API restarts repeatedly.
2. A camera's `last_seen_age_s` > 120 (`stale: true` in `/api/ops/status`) or `fps` falls below what its rules need.
3. `rs_ingest_events_total{result="accepted"}` stops growing while cameras are live (pipeline down or rejected).
4. `new_unreviewed` keeps growing (nobody is looking), or > 50 in 24 h.
5. 5xx rate in `rs_http_requests_total{status="5xx"}`; a startup log line `EVIDENCE STORAGE:` (ephemeral storage).
6. The supervisor status file shows a camera restarting repeatedly (`restarts` rising, `last_reason`).

## Evidence storage persistence (read before ANY redeploy)
Evidence files are encrypted and live in `RS_EVIDENCE_DIR` or in an S3-compatible bucket (`RS_EVIDENCE_S3_BUCKET`, endpoint, region, key id/secret). On a container platform the local directory is **lost on redeploy** unless it is a persistent volume. The API logs `EVIDENCE STORAGE: …` at start-up when the directory is under `/tmp` (always) or on local disk in production (a reminder). The deploy workflow is manual and requires a green CI run for the commit; it cannot be triggered by a push.

## Audit checkpoints (local adapter)

`anchor-audit` first verifies the tenant's database chain, then appends a signed Ed25519
checkpoint. The key file is created with mode `0600`; its `.pub` companion is safe to distribute
to verifiers. Verify the checkpoint signature and that its sequence/head still matches the current
database chain with:

```bash
python -m app.cli verify-audit-anchor --tenant unit-a \
  --anchor-file /var/lib/roadsentinel/audit.jsonl \
  --public-key /var/lib/roadsentinel/audit-ed25519.key.pub
```

Run commands from `backend/` with the backend environment configured. Store checkpoints and
signing keys on separate administrative systems before treating anchoring as an independent
tamper-resistance control. The local adapter is for development and verification only.

## Backup and restore (verified locally)
```bash
RS_BACKUP_DATABASE_URL=postgresql://owner:pw@host/roadsentinel RS_EVIDENCE_DIR=/data/evidence scripts/backup.sh /backups/$(date +%F)
RS_RESTORE_DATABASE_URL=postgresql://owner:pw@host/restored scripts/restore.sh /backups/2026-11-05 /data/evidence-restored   # into an EMPTY database
```
Verified here: backup → restore into an empty database → table counts equal (tenants 3, users 9, alerts 14, evidence 14, audit_log 3), `verify-audit` gives the same head hash, the runtime role (`rs_app`) works on the restored database. **Not covered:** the master keys (`RS_MASTER_KEYS`) are not in the backup and without them the evidence ciphertext is unreadable: keep them in a separate secret store with its own backup. A restore drill on the production platform has **not** been run.

## Migrations and rollback
`python -m app.cli migrate` applies 0001…0012. `alembic downgrade -1` works for 0007–0012 (columns/tables dropped; 0009 cannot remove the `account_reset` enum value, harmless; 0008 deletes alerts with object class `object`; 0010 drops retention policies). Always take a backup first. Never edit an applied migration.

## Keys and secrets
* `RS_MASTER_KEYS` (versioned) wraps each tenant's data keys: rotate with a new version + `python -m app.cli rewrap-keys --tenant …`; `rotate-tenant-key` creates a new data key (existing evidence files keep the old key version, see docs/LIMITS.md).
* `RS_JWT_SECRET`, `RS_URL_SIGNING_KEY`: rotating logs everybody out. The API refuses to start in production with known/weak values, with the demo MFA exemption on, or with a privileged DB role.
* `python scripts/scan_secrets.py [--history]` reports file:line only.

## Incident recipes
* Locked-out user: tenant admin → Cont → *Recuperare cont* (needs a second admin to approve); no second admin or a system-admin account: `python -m app.cli reset-account --tenant T --email E [--reset-mfa]` prints a single-use token once (audited).
* Suspected tampering: `python -m app.cli verify-audit --tenant T`.
* Bad model after activation: `python scripts/model_rollback.py cameras/<id>.yaml`.
