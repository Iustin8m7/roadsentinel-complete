> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Existing integration runtime verification

Recorded 2026-11-10T13:10:51.595733+00:00. This report supersedes the earlier conclusion that live login was blocked. Runtime A is the user's existing application; runtime B is disposable test infrastructure; runtime C is the original project and remains read only.

| Runtime | Actual identity | Writes performed |
|---|---|---|
| A | UI 127.0.0.1:5175; FastAPI 127.0.0.1:8003; rsint_20261110b at 127.0.0.1:55446 | Verified backup/rehearsed additive schema upgrade and lookup ownership repair; normal login/MFA/session/audit records. No seed/reset/password replacement. |
| B1 | New /tmp/rslogin-tests-e7z6iko0 PostgreSQL; 55481; rslogin_testroot; rsmission_final_regression | Fresh migrated test DB, fixture-owned records only. |
| B2 | New /tmp/rsverify-0mil4kkg PostgreSQL; 37651; rsverify_root; rsmission_verify_0136cfcfa3 | Independent repeat run, 44 passed; automatically stopped and temporary cluster removed. |
| C | ../roadsentinel and ../roadsentinel-github-review | No modifications; model read only from original path. No original database connected for writes. |

## Source and active process mapping

- Physical write root: `/home/justin7m8/Documents/roadsentinel-integration`, distinct from both references. Integration has no `.git`; none was created.
- New source checkpoint: `runtime_verification/source-checkpoint.zip`, `source-baseline.json` and `document-baseline.json`. No secrets/media were copied into the checkpoint.
- Initial integration FastAPI PID 1655813 used the original dependency interpreter but integration cwd. Only positively matched integration backend PIDs were restarted. Current PID and executable are in [runtime-after.json](runtime_verification/runtime-after.json); the backend now uses `.venv.integration/bin/python`, with root+backend on PYTHONPATH. No package was installed into the original virtual environment.
- Existing Vite PID 1671183, cwd integration/frontend, actually has `RS_API_ORIGIN=http://127.0.0.1:8003`. It serves updated source through HMR. The generic Vite fallback remains 8000; the new integration startup helper always supplies 8003 without changing production defaults.
- `scripts/integration-dev.py` starts loopback-only services, refuses occupied ports, and verifies UID/cwd/argv/DB endpoint before a targeted restart. No other service was stopped.
- Direct and proxied `/api/health/live` and `/api/health/ready`: 200. Unauthenticated `/api/auth/me`: 401 on both origins. Authenticated browser requests to the same proxy: 200. A health 200 is not used as login or worker evidence.
- Current development cookie/MFA settings, selected nonsecret process settings and environment names are in runtime-after.json. Local HTTP cookies retain SameSite and HttpOnly rules; production HTTPS policy was not weakened. MFA exemption remains disabled.

## Live database identity and safe migration

Live SQL confirmed `current_database=rsint_20261110b`, server address `127.0.0.1`, port `55446`, admin `rsint_root_261110`; system identifier `7706309627307635180`. Application identity is `rsint_app_261110b`. Initial revision `rsint_case2`; final revision `0022`.

The available integration-specific administrator was discovered through the integration server's role metadata. The earlier assumption that a `postgres` role was required was wrong. No unrelated credential file or database was searched.

A private `pg_dump` was restored to a unique loopback cluster; every table's row digest matched; the additive upgrade was rehearsed there. Only then did the guarded repair modify A. [Recovery log](runtime_verification/recovery-apply-verified.log). Backup: `backend/.integration-backups/20261110T124010Z-e07b2253/`, mode 0700; dump and metadata 0600. Immediately after migration all pre-existing public-table row digests matched, excluding Alembic's expected version change. Subsequent MFA/login/audit/session writes are deliberate application behavior.

Current security enumeration is in [live-security-after.json](runtime_verification/live-security-after.json): 32 named tenant tables retain ENABLE + FORCE RLS; app and original migrator stay NOBYPASSRLS. The six identifier lookup functions have a dedicated NOLOGIN owner with column-limited SELECT and no access to password hashes.

## Preservation and limits

[reference-preservation-final.json](runtime_verification/reference-preservation-final.json) verifies both HEADs and 608 source-file hashes (307 + 301) against this execution's initial baseline. This is source/HEAD preservation evidence, not a claim of byte-hashing every ignored video/model/log. No GitHub push or other GitHub mutation occurred. The existing integration remains running; test-owned servers are stopped after testing. No external camera was accessed.
