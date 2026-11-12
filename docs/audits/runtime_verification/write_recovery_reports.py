"""Update the current execution evidence without rewriting the historical BEFORE audit."""
import collections
import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / 'docs/audits'
E = D / 'runtime_verification'
NOW = datetime.now(UTC).isoformat()
FLOW = 'runtime_verification/runs/20261110T130556Z-dbe51341'


def write(name, content):
    (D / name).write_text(content.strip() + '\n')


def banner(name, text):
    p = D / name
    marker = '> Current runtime verification — 2026-11-10'
    s = p.read_text()
    if marker not in s:
        p.write_text(marker + '\n> ' + text + '\n> Historical observations below retain their original scope/date.\n\n' + s)


# Preserve every stable requirement ID and the frozen source anchors.
mp = D / 'README_COVERAGE_MATRIX.csv'
rows = list(csv.DictReader(mp.open()))
fields = list(rows[0])
assert len(rows) == 185 and len({r['id'] for r in rows}) == 185
for r in rows:
    if r['id'] in {'A18', 'A26', 'REQ-0088', 'REQ-0091'}:
        r.update(current_status='VERIFIED REAL END-TO-END', evidence_link='docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md', test_path='backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs', code_owner='backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts', verification_limit='Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.', next_acceptance='Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.')
    if r['id'] in {'REQ-0012', 'REQ-0024', 'REQ-0025', 'REQ-0032', 'REQ-0035', 'REQ-0051', 'REQ-0089', 'REQ-0090', 'REQ-0095', 'REQ-0113', 'REQ-0116', 'REQ-0143'}:
        r.update(current_status='PARTIAL', evidence_link='docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md', verification_limit='Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.')
    if r['id'] in {'A11', 'A14', 'A19'}:
        r.update(current_status='PARTIAL', evidence_link='docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md', verification_limit='Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.')
    if r['id'] in {'A12', 'A13', 'A15', 'A16', 'A17', 'A23', 'A24', 'A25', 'A27', 'A28', 'A33', 'A34', 'A35'}:
        r['evidence_link'] = 'docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md'
        if r['id'] in {'A12','A13','A15','A16','A24'}:
            r['current_status'] = 'VERIFIED REAL INPUT PARTIAL'
        r['verification_limit'] = 'Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.'
    if r['id'] == 'A16':
        r['test_path'] = 'backend/tests/test_managed_live_runtime.py;frontend/e2e/camera-control-runtime.mjs'
        r['next_acceptance'] = 'Config creation/approval/activation passed via authenticated APIs, registration and preview via browser. Next automate the entire configuration editor and approval in two independent browser contexts.'
    if r['id'] == 'A24':
        r['next_acceptance'] = 'Real managed replay, duplicate lease refusal, revision 1 to 2, outage recovery, disable/re-enable passed. Next provide lawful positive live event and multi-camera soak.'
with mp.open('w', newline='') as fp:
    writer = csv.DictWriter(fp, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
counts = dict(collections.Counter(r['current_status'] for r in rows))
(E / 'coverage-summary.json').write_text(json.dumps({'rows':len(rows),'statuses':counts}, indent=2))

write('POST_INTEGRATION_RUNTIME_VERIFICATION.md', f'''
# Existing integration runtime verification

Recorded {NOW}. This report supersedes the earlier conclusion that live login was blocked. Runtime A is the user's existing application; runtime B is disposable test infrastructure; runtime C is the original project and remains read only.

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
''')

write('INTEGRATED_LOGIN_RECOVERY_REPORT.md', '''
# Existing integration login recovery — VERIFIED

The saved development password now authenticates against the actual existing 5175 → 8003 → rsint_20261110b:55446 application, with mandatory MFA and authenticated dashboard access. See [browser evidence](ACTUAL_BROWSER_LOGIN_EVIDENCE.md).

## Proven cause

`rs_tenant_id_by_slug`, `rs_auth_find_user` and related lookups were SECURITY DEFINER with pinned `search_path=public, pg_temp`, but their owner `rsint_owner_261110b` had BYPASSRLS=false. FORCE RLS applies to a normal table owner, including when entered by SECURITY DEFINER. Before a tenant is known, the lookup session has no `app.tenant_id`; tenant policies hide the existing tenant/user rows. Authentication therefore could not discover the account and returned its normal generic Invalid credentials response.

The same visibility failure made `seed()` believe the existing platform slug was absent. Its attempted INSERT conflicted with the actual unique slug index. A zero-row app-role SELECT was not evidence of an empty table.

Authorized administrator reads found **3 tenants and 9 users**. All nine existing hashes matched the password in `backend/.integration-test-credentials.json`; accounts were active/unlocked and MFA exemption false. None was enrolled before this execution. The password and existing identities required no recovery/reset. Sanitized account evidence: [account-inspection-before.json](runtime_verification/account-inspection-before.json). Hashes/passwords are excluded.

## Least-privilege repair

New `backend/app/services/lookup_roles.py::install_lookup_owner` and Alembic `0022_narrow_lookup_owner.py` establish `rsint_app_261110b__lookup`:

- NOLOGIN, NOSUPERUSER, NOINHERIT, NOCREATEDB, NOCREATEROLE, NOREPLICATION; no members/memberships.
- BYPASSRLS solely for the six reviewed identifier-only pre-tenant functions. It owns no application tables.
- SELECT only the required lookup columns: tenant identity/slug/platform flag; user ID/email/tenant; token lookup fields; allowlisted resource ID/tenant. **No users.password_hash read privilege and no public schema CREATE.**
- Six existing SECURITY DEFINER functions retain the fixed search_path; PUBLIC EXECUTE revoked, runtime EXECUTE explicitly granted. No unsigned or general-purpose lookup API was introduced.
- Runtime app and old migration owner remain NOBYPASSRLS. All 32 tenant tables retain FORCE RLS. Tenant context still uses transaction-local configuration in `app/db.py`.

The guarded `scripts/recover_integration_login.py` defaults to read-only inspection. `--apply` requires exact workspace/URL/DB/user/system identifier/current-owner checks, private backup, isolated restore and migration rehearsal, unchanged live row digests, and final preservation verification. It refuses identity mismatches. The old shell repair now delegates to this guarded script; its former blanket migration-owner BYPASSRLS grant was removed.

The existing DB upgraded rsint_case2 → 0020 → 0021 → 0022 only after rehearsal. 0021 adds two indexes. 0020's owner prerequisite was satisfied by the narrow dedicated owner before migration; no broad privilege was granted to the migrator. 0022 intentionally retains ownership hardening on downgrade. Admin URL is needed only for setup/migration, never provided to the HTTP runtime.

## Seed and partially initialized databases

`app/services/seed.py` refuses production. Existing tenants are resolved securely, missing expected development users/keys are created in tenant context, and conflicts are reconciled instead of assuming an existing unit is complete. Repeated seed preserves existing user IDs, password hashes, roles and MFA; it does not silently reset unrelated users. New users use the supplied development password. `--users-only` skips synthetic camera/alert/evidence creation. Existing user hashes are never rewritten just because the command was rerun. An invisible existing slug produces an explicit RLS/owner diagnosis instead of repeated blind insertion.

No seed command ran against A during recovery: every required account already existed. Repeated/partial seeding was tested solely on B.

## React auth/MFA corrections

- Real `/api/auth/me` identity/permissions now drive UI roles. Patrol and auditor no longer appear as operators; auditor lands at `/app/audit`. Unauthorized stats/alert/SSE fetches are suppressed.
- Mandatory enrollment uses `/api/auth/mfa/enroll/start`, QR, six-digit TOTP, `/confirm`, then shows eight recovery codes. Authenticated navigation occurs only after acknowledging the codes, fixing the previous early redirect.
- Empty tenant data now ends loading correctly instead of showing permanent dashboard skeletons.
- Sessions survive browser reload and an actual integration backend process restart. Logout invalidates protected requests. Wrong password stays 401 and wrong/replayed TOTP is rejected by regression tests.

## Actual live state

Operator, tenant admin, patrol and auditor Unit A accounts completed genuine QR enrollment and authenticated browser sessions. The operator also passed a subsequent normal TOTP challenge. Password unchanged. Private phone-import QR and recovery artifacts are in `backend/.integration-authenticators/` (0700 directory, 0600 files); not in screenshots or Markdown. Local test credential metadata marks the observed verified state. These development authenticators are intentionally local conveniences, not a production key-storage recommendation.

## Rollback/restore guidance

The private backup folder contains dump SHA-256, original row digests, original function owners and `rollback-lookup-owners.sql`. Restoring old ownership would intentionally restore the login visibility bug; never run that SQL blindly. First verify the exact database/system identifier again. Do not restore over the running database or drop existing data. A safe restore drill creates a new unique DB/cluster, recreates the two named roles, restores the dump, and compares the metadata digests, as the recovery script already did. The additive migration has no data-deleting rollback. Keep the verified backup private and retain the functional narrow owner.

## Regression proof

`backend/tests/test_lookup_ownership.py` reproduces the exact missing-row failure by changing only the dedicated owner's attribute in a disposable DB, then restores it in finally and proves lookup/repeated seed recovery. It also denies password column access and preserves an existing changed password across reseeding. `test_seed.py` verifies partial unit repair and forced RLS. `test_auth.py` covers password/TOTP/recovery/session/CSRF/invitation isolation. Full backend: 422 passed, 2 opt-in skipped. Reproducible fresh-cluster auth + both-feature subset: 44 passed. No security control disabled.
''')

write('ACTUAL_BROWSER_LOGIN_EVIDENCE.md', '''
# Actual existing-browser login evidence — PASS

Runtime **A**, not an ephemeral substitute: Chromium accessed `http://127.0.0.1:5175/login`; Vite proxied to actual FastAPI 8003; its process URL and live DB queries verified rsint_20261110b on 127.0.0.1:55446. Password was read from the existing protected credential file. No credential is repeated here.

| Account | Real backend role | Observed browser behavior |
|---|---|---|
| operator.a@roadsentinel.local | operator | Wrong password 401; correct password 200 + MFA required; visible QR; valid TOTP; eight recovery codes held until acknowledgement; /app; refresh; protected APIs; logout. Then normal TOTP sign-in again. |
| admin.a@roadsentinel.local | tenant_admin | QR enrollment, TOTP, recovery acknowledgement, /app; users API allowed; logout. |
| patrol.a@roadsentinel.local | patrol | QR enrollment, /app; users and audit verify forbidden; no unauthorized stats request; logout. |
| auditor.a@roadsentinel.local | auditor | QR enrollment, /app/audit; real audit chain data; events forbidden; logout. |

Executed `PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH node frontend/e2e/live-login-recovery.mjs`. First run: five successful journeys, no JavaScript page errors. [Original enrollment result](runtime_verification/live-browser-enrollment-result.json), [original log](runtime_verification/live-browser-enrollment.log). A subsequent run verifies completed dashboard loading/empty state, not only navigation or HTTP status; see [latest result](runtime_verification/live-browser-result.json) and [latest log](runtime_verification/live-browser-loaded.log). Screenshots are taken only after MFA, with no password/QR/recovery material:

- [Operator dashboard](runtime_verification/screenshots/live-operator.png)
- [Tenant administrator](runtime_verification/screenshots/live-tenant_admin.png)
- [Patrol dashboard](runtime_verification/screenshots/live-patrol.png)
- [Auditor view](runtime_verification/screenshots/live-auditor.png)

The sanitized network trace in the result includes only role/method/path/status. Protected `/api/auth/me` returns 200 after MFA and 401 after logout. `/api/users` returns 200 for tenant admin and 403 for the other three roles. `/api/audit/verify` returns 200 for admin/auditor and 403 for operator/patrol. Auditor `/api/events` returns 403 as required. Browser reload preserves identity. An actual owned backend process restart preserved a previously issued session, followed by a successful logout and subsequent 401: [restart-session.json](runtime_verification/restart-session.json).

The existing integration contains no test incidents/cameras from these browser login tests. An empty queue is a legitimate completed response. The fixed dashboard shows Nicio alertă de verificat instead of permanent loading. No demo/mock alert was inserted to disguise the empty tenant.

MFA is now enrolled for those four development accounts. To use a phone, locally open the corresponding private `backend/.integration-authenticators/<email-prefix>.html` and scan its QR into your authenticator. Then login asks for its current six-digit code. The local helper `scripts/integration_totp.py <email>` reads the enrolled secret under mode-0600 protection and computes a genuine TOTP; it does not exempt or bypass MFA. Do not share these files. Codes are single-use within their time step; if an immediately repeated code is rejected, wait for the next 30-second step.
''')

write('FULL_INTEGRATION_E2E_VALIDATION.md', f'''
# Full integration E2E validation — observed scope

Existing login: **PASS on A**. Feature 1 selected fixture journey: **PASS on B; broader feature PARTIAL**. Feature 2 selected controlled camera journey: **PASS on B; broader feature PARTIAL**. No external-live/accuracy/production acceptance claim.

## Inputs and runtime

- Model: Megvii YOLOX-S COCO ONNX; SHA-256 `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`; CPUExecutionProvider; actual ONNX Runtime detections and Supervision ByteTrack, no detector mock.
- Model location: original `models/yolox_s.onnx`, read only through explicitly configured `RS_YOLOX_MODEL_PATH`; stock checksum is enforced. No model download, copy, move or unknown-model fallback.
- Media: Editor's Wikimedia Commons Street traffic.webm, CC BY 3.0; local `/tmp/Street_traffic.webm`; SHA-256 `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`.
- B1 full suite: rsmission_final_regression, 127.0.0.1:55481, rslogin_testroot. B2 independent repeat: [database identity]({FLOW}/database.json). Each starts at base and migrates to 0022 with role/RLS prerequisites. Neither is the existing integration DB.

## Feature 1 — actual HTTP + Chromium + encrypted persistence

`backend/tests/test_mission_vertical.py::test_real_inference_recorded_candidate_to_encrypted_review` constructs a 36-second frozen derivative of a licensed frame, explicitly **SYNTHETIC TEST**. Actual model/tracker processes 60 samples; the focused run observed 8 candidates (an earlier run observed 9). Candidate count can vary with model/runtime scheduling; the test asserts actual nonempty inference/candidates, not a hardcoded accuracy figure. This is artificial stationary dwell, not a real obstruction incident.

Observed sequence:

1. Actual password/TOTP HTTP authentication; POST `/api/recordings` 201; crop confirmation 200; POST analysis 202; polling completed with real nonempty model tracks.
2. GET owned candidates; explicit POST candidate promotion 200; duplicate request returns the same alert. Recorded origin, run/track/model/media-position details persist. No automatic live alert or dispatch.
3. Authenticated redacted keyframe and bounded MP4 retrieval; encrypted storage metadata and RSE1 payload asserted. Chromium plays the protected MP4 with nonzero dimensions and duration.
4. Chromium password/TOTP login → `/app/analiza-video` → candidate duplicate submission → canonical alert → actual Respinge dialog/confirmation → case observation added through the real UI. Subsequent HTTP decision receives 409, proving UI performed the persisted transition.
5. Real HTTP case note, admin-recorded explicit fixture license grant, export request with not-ready 409, self-approval rejection, independent administrator approval, package generation and protected download. `verify_package` independently checks manifest SHA-256 and member hashes, with at least two files checked.
6. Other tenant receives 404; patrol/auditor receive 403 on promotion; other-tenant media denied. Complete backend suites cover ingest HMAC/replay/idempotency, approvals/evidence and tenant rules as separate negative tests.

[Executed focused log](runtime_verification/full-feature-journeys.log), [fresh repeat]({FLOW}/flows.log), [real browser screenshot](screenshots/recorded-review.png). Test-owned recording, ciphertext and export were not copied into the existing user's database.

Limits: initial upload/analysis/first promotion and final approval/export used HTTP rather than every step in Chromium. No abrupt service crash during an evidence write, complete archive UI retrieval after restart, original-media retention soak, or real incident precision/recall was proved. Manifest integrity is not a cryptographic signature or external custody anchor. The standalone case-export authorization/tamper/unit suites passed, but do not substitute for every browser scenario.

## Feature 2 — actual registration → approval → worker → preview → recovery

`test_managed_live_runtime.py::test_managed_replay_ack_preview_and_revocation` now creates camera state through actual authenticated operations rather than injected preapproved rows:

1. Tenant administrator logs in with real MFA in Chromium, adds LOCAL RECORDED REPLAY via `/app/camere`, receives camera POST201 and opens its control panel.
2. Authenticated camera-control APIs record source `recorded_replay`, local replay reference and explicit CC BY processing grant. Author creates/validates/submits a config; self approval is 403; a distinct tenant admin approves; activation succeeds.
3. Actual `roadsentinel.pipeline` subprocess obtains HMAC lease before source open, validates model hash/frame dimensions, applies approved config and ACKs revision 1. Signed heartbeats and authenticated preview show actual detections/track IDs and changing decoded JPEG content/timestamps.
4. A competing actual worker exits without opening the controlled source; lease ownership is not duplicated.
5. Operator Chromium login opens live detail; decoded preview updates; LOCAL RECORDED REPLAY provenance is asserted. [Registration screenshot](runtime_verification/screenshots/camera-register.png), [preview screenshot](runtime_verification/screenshots/camera-preview.png).
6. Independent config approval and activation of revision 2 causes old worker to exit cleanly. Fresh worker acquires a new lease and ACKs revision 2; subsequent telemetry is stamped accordingly.
7. Only test server sockets are interrupted. Authoritative state becomes reconnecting; stale preview returns404. Restored source yields real frames and healthy state. No hidden sample fallback is used.
8. Actual disable API stops processing. Self re-enable is403; independent reviewer re-enables; new lease/ACK/real frames succeed. Final pause stops worker cleanly. Best-effort stopped heartbeat now releases the lease immediately on orderly worker exit; expiry remains the failure fallback.

The captured worker measured CPU inference p50 approximately83–92ms, p95 approximately95–117ms and peak RSS approximately344–345MB in one short run. These are observed test measurements, not throughput/accuracy/service guarantees. Source dimensions1920×1080; actual processing roughly1–2.35fps in this resource-limited run, despite10fps source delivery. Calibration-dependent rules remain gated. Moving replay produced **zero eligible incident events**; this is reported honestly. Model-derived positive rule/evidence is demonstrated separately by Feature1's explicit synthetic recorded fixture. Live-camera event-to-case/export as a single positive managed run is still unverified.

Configuration edits/approval were through real MFA-authenticated APIs; registration and preview were through Chromium. The entire configuration editor/approval flow in two browser windows is not yet automated. No externally authorized camera, physical UVC camera, two-camera capacity run, long soak, or live incident ground truth was exercised. External camera processing remains blocked by documentary rights, not silently replaced by a live claim.

## Reproduce safely

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/verify-integration.py flows
```

This creates a unique loopback PostgreSQL cluster and database, verifies guarded fixture identity, runs auth/seed plus both actual-model/browser journeys, records UTC start/end/exit/duration and exact commands, and stops only that owned cluster. No existing service/DB is reset. Model and licensed fixture must already be present; no external fetch is attempted. The executed independent run passed **44 tests**, no skips, and shut down its own test cluster: [commands]({FLOW}/commands.json).
''')

write('OPERATOR_DEMO_QUICKSTART.md', '''
# Operator demo quickstart — existing login verified

The current UI/API/database are running. Start with the existing instance; do not seed or run migrations again.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
xdg-open backend/.integration-authenticators/operator.a.html
xdg-open http://127.0.0.1:5175/login
```

The first command opens a private development QR. Scan it into your own authenticator. It contains secret material: keep it local. These accounts were enrolled during the actual browser test, so login now shows a six-digit challenge rather than new enrollment.

- Tenant: unit-a; no tenant input field is required.
- Operator: `operator.a@roadsentinel.local`.
- Admin: `admin.a@roadsentinel.local` (use its own admin.a.html QR).
- Password: existing, unchanged, verified value in `backend/.integration-test-credentials.json` (0600). It is shown once in the interactive final handoff; do not paste it into docs/logs.
- Enter the current TOTP from the imported QR. Dashboard: `/app`. Auditor: `/app/audit`.
- Save recovery codes privately from `backend/.integration-authenticators/authenticators.json`; no shared screenshot/log should contain them.

Without a phone, local development can compute its genuine enrolled second factor:

```bash
.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local
```

Never store the printed code in a shared log. TOTP is replay protected; wait for the next30-second interval if already consumed. MFA is not disabled.

## Check or start only integration services

```bash
curl --fail http://127.0.0.1:8003/api/health/live
curl --fail http://127.0.0.1:5175/api/health/live
```

If a service is stopped, start only that service:

```bash
python3 scripts/integration-dev.py backend
python3 scripts/integration-dev.py frontend
```

The helper refuses occupied ports. For a necessary restart use `--restart-pid <verified integration PID>`; it checks user/cwd/command/DB target before signaling. It never stops PostgreSQL. Backend uses `.venv.integration`; frontend starts with explicit `RS_API_ORIGIN=http://127.0.0.1:8003` and mocks off. Alternative foreground frontend command:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/frontend
PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH RS_API_ORIGIN=http://127.0.0.1:8003 VITE_USE_MOCKS=0 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Do not launch a competing frontend/backend while their ports are occupied. Private owned logs/PID metadata: `backend/.integration-runtime/`. API development schema path is `/api/openapi.json`; `/openapi.json` is not the configured path.

## Actual fixture demonstrations without contaminating the existing DB

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/verify-integration.py flows
```

This runs actual Chromium and actual model/HTTP against a newly created disposable DB, with its own Vite/API/replay servers. Evidence/logs and exact commands go to `docs/audits/runtime_verification/runs/<unique>/`; all owned servers stop afterward. It does not fill your dashboard with artificial cases.

For your own permitted media, use `/app/analiza-video`: upload, confirm crop, start analysis, inspect eligible obstruction/queue candidates and explicitly send for review. This is recorded evidence; it is never live dispatch. `/app/alerte/<id>` shows media/rejection/case notes. The camera demo uses `/app/camere`: registration, control/source/grant/version workflow, separate administrator approval, lease/ACK and real preview. Sources without documented rights must remain disabled. See the two feature implementation reports for configuration contracts. Not every real clip will generate an incident; zero events is a valid outcome.

## Login repair diagnostics (normally unnecessary now)

```bash
bash scripts/repair-integration-dev-auth.sh
```

Default is inspection only. Do not rerun privileged changes simply to log in. If repair is needed after independent changes, the sole guarded `--apply` path verifies exact server system ID, private backup, isolated restore/rehearsal and row preservation. No reset or password overwrite occurs. See INTEGRATED_LOGIN_RECOVERY_REPORT.md for the backup/rollback limitations.
''')

write('FINAL_LOGIN_HANDOFF.md', '''
# Verified existing login — YES

Open **http://127.0.0.1:5175/login**. API **http://127.0.0.1:8003** uses **rsint_20261110b@127.0.0.1:55446**, revision0022.

Operator: **operator.a@roadsentinel.local**, tenant **unit-a** (no tenant field). Password is unchanged and actually tested: use `backend/.integration-test-credentials.json` (0600). Admin **admin.a@roadsentinel.local** was also verified with the same saved development password.

MFA is enabled and already enrolled by the browser verification. Locally open `backend/.integration-authenticators/operator.a.html`, scan its private QR into your authenticator, and enter the current six-digit code when logging in. Alternatively run `.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local` to compute the real development TOTP. Do not share QR/secrets/recovery codes.

Actual Chromium proof: [operator dashboard](runtime_verification/screenshots/live-operator.png), [network/result evidence](runtime_verification/live-browser-result.json). The last successful journey includes authenticated role/dashboard data, refresh and logout followed by401. No remaining host privilege blocker for login. [Copy/paste quickstart](OPERATOR_DEMO_QUICKSTART.md).

Both broader AI features remain PARTIAL despite successful isolated fixture journeys: no claim of real incident accuracy, external camera rights, complete live-incident export or production readiness. Originals preserved; NO GITHUB PUSH.
''')

# Preserve the earlier AFTER report and regenerate its individual entries from unchanged IDs.
old_after = D / 'POST_INTEGRATION_README_AUDIT_AFTER.md'
old_snapshot = E / 'README_AUDIT_AFTER_BEFORE_LOGIN_RECOVERY.md'
if not old_snapshot.exists():
    shutil.copyfile(old_after, old_snapshot)
body = ['# Post-integration README audit — after runtime recovery', '', f'Updated {NOW}. The historical BEFORE inventory remains unchanged. All185 IDs remain in the coverage matrix:150 source paragraph/table criteria and35 category checks. This is source coverage plus scoped executed acceptance, not185 passed feature tests. Full transitive specification acceptance, representative accuracy and production/legal readiness remain unproved.', '', '## Current verdict', '', '- Existing 5175/8003/55446 login: PASS; four Unit A roles enrolled, normal operator MFA challenge, protected requests, reload/restart/logout verified.', '- Feature1: selected real-model synthetic-recorded fixture journey passes, including actual UI rejection/case note and independently approved hash-verified HTTP export. Broader feature PARTIAL.', '- Feature2: actual UI registration, two-admin API approval, real worker lease/ACK/changing browser preview, revision2, duplicate refusal, outage recovery and disable/re-enable pass. Broader feature PARTIAL; zero eligible live events and no external live rights.', '- Fresh backend422 passed/2 opt-in skipped; pipeline213; React19; PWA9; both builds/lints pass. Reproducible independent fresh-cluster auth+flows44 passed.', '- Exact current reports: INTEGRATED_LOGIN_RECOVERY_REPORT.md, ACTUAL_BROWSER_LOGIN_EVIDENCE.md, FULL_INTEGRATION_E2E_VALIDATION.md, TEST_EXECUTION_LEDGER.md.', '', 'Status totals: ' + json.dumps(counts, sort_keys=True) + '.', '', 'The earlier after-audit is preserved at runtime_verification/README_AUDIT_AFTER_BEFORE_LOGIN_RECOVERY.md. Historical blocked-auth statements in older documents are superseded by the current reports.', '']
for r in rows:
    body += [f"### {r['id']} — {r['requirement'][:130]}", f"Source: `{r['source']}:{r['lines']}`. **{r['current_status']}**; priority {r['priority']}.", f"Owner: `{r['code_owner']}`. Tests: `{r['test_path']}`.", f"Evidence: `{r['evidence_link'] or 'No direct current-run criterion-level acceptance proof'}`.", f"Next acceptance: {r['next_acceptance']}", f"Limit: {r.get('verification_limit','')}", '']
old_after.write_text('\n'.join(body))

for name in ['FINAL_ENGINEERING_HANDOFF.md','INTEGRATED_BROWSER_DEMO_RUNBOOK.md','ISSUES_AND_UNVERIFIED_EVIDENCE.md','MISSION_CHECKPOINT.md','PRE-FLIGHT.md']:
    banner(name, 'Existing integrated login is now VERIFIED with MFA on5175/8003/rsint_20261110b:55446 after backup/rehearsed narrow lookup-owner repair and0022. Use [FINAL_LOGIN_HANDOFF.md](FINAL_LOGIN_HANDOFF.md), [POST_INTEGRATION_RUNTIME_VERIFICATION.md](POST_INTEGRATION_RUNTIME_VERIFICATION.md) and [FULL_INTEGRATION_E2E_VALIDATION.md](FULL_INTEGRATION_E2E_VALIDATION.md).')

# Preserve architecture route inventory, add the corrected current lineage/security facts.
p = D / 'ARCHITECTURE_AND_CONTRACT_MAP.md'
s = p.read_text().replace('→ 0020 → 0021. 0021 adds two offline tenant indexes only. Existing integration DB not migrated.', '→ 0020 → 0021 → 0022. 0021 adds two offline tenant indexes;0022 gives six identifier-only functions a column-limited NOLOGIN owner. Existing integration DB upgraded only after verified backup/restore rehearsal. Runtime/migrator remain NOBYPASSRLS.')
p.write_text(s)
p = ROOT / 'README.md'
s = p.read_text().replace('All seeded accounts share the password in `RS_SEED_PASSWORD` from your `.env` (random per\nmachine). Every account must enroll TOTP on first login (QR code + 8 recovery codes).', 'New development accounts use `RS_SEED_PASSWORD` from the local environment. Repeated seeding\npreserves existing passwords, roles and MFA. Every new account must enroll TOTP on first login\n(QR code + 8 recovery codes). The verified integrated5175/8003 login and private credential\nlocations are documented in [the operator quickstart](docs/audits/OPERATOR_DEMO_QUICKSTART.md).')
p.write_text(s)
print('Reports generated; preserved criteria:', len(rows), 'statuses:', counts)
