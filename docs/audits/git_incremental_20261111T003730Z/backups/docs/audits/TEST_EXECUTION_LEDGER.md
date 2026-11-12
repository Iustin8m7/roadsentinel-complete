> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Current execution — existing login recovered, 2026-11-10

This section supersedes the historical midnight-run ledger below. A is existing5175/8003/rsint_20261110b:55446. B is fresh disposable PostgreSQL on55481 or a new unique random port. C is the original read-only project. Tests can see native loopback in this session; there was no socket/administrator blocker.

| Check | Actual outcome | Runtime and evidence |
|---|---|---|
| Full backend `python -m pytest tests -o addopts='' -q` | **422 passed, 0 failed, 2 skipped**, 19 warnings,138.45s | B, rsmission_final_regression:55481, `runtime_verification/backend-suite-final.log` |
| Full root `python -m pytest tests -o addopts='' -q` | **213 passed, 0 failed, 0 skipped**,2 warnings,5.67s | B test-owned temp files, `pipeline-suite-current-fixed.log`; stock model path explicitly supplied |
| React `npm run test` | **19 passed,0 failed,0 skipped**,3 files | `frontend-tests-final.log` |
| React `npm run lint`; `npm run typecheck`; `npm run build -- --outDir <new verification output>` | PASS | `frontend-lint.log`, `frontend-typecheck.log`, `frontend-build.log`; build includes TypeScript |
| PWA `npm run test` | **9 passed,0 failed,0 skipped**,2 files | `pwa-tests.log` |
| PWA `npm run lint`; `npm run build -- --outDir <new verification output>` | PASS; build includes TypeScript | `pwa-lint-final.log`, `pwa-build.log` |
| Actual live Chromium login | **5/5 journeys** first run and **5/5 repeat**; no JS page errors | A, `live-browser-enrollment-result.json`, `live-browser-result.json`; current screenshot requires completed data loading |
| Recorded + camera focused HTTP/model/browser | **2 passed**,17 warnings,47.21s | B, `full-feature-journeys.log` |
| Independent new-cluster auth/seed/model/browser repeat | **44 passed,0 failed,0 skipped**,17 warnings,67.30s | B2 rsmission_verify_0136cfcfa3:37651; [runtime_verification/runs/20261110T130556Z-dbe51341/commands.json](runtime_verification/runs/20261110T130556Z-dbe51341/commands.json) records exact UTC start/end/exit/duration, including clean owned shutdown |
| Python compilation | PASS | `compile.log`; backend/app, backend/alembic, roadsentinel, new scripts |
| Targeted Ruff | PASS after corrections | `python-quality.log`; reviewed changed lookup/migration/test/pipeline/helper files; whole-tree style cleanliness is not claimed |
| Guarded repair inspection | PASS; inspection-only after repair | `recovery-final-inspection.log`; exact native identity verified |
| Live migration/RLS | rsint_case2→0022 after verified backup/restore/rehearsal;32 named FORCE RLS tables retained | `live-security-after.json`; no live reset/seed/password overwrite |
| Reference source preservation | **608/608 hashes + both HEADs unchanged** | `reference-preservation-final.json` |

The44-test repeat is a subset of the backend suite, not44 additional unique tests. Skipped legacy real tests use separate opt-in flags and an in-tree model requirement; `test_real_yolo_e2e` and `test_offline_analytics_real_video` remain skipped. The newer mission tests actually ran the model and browser in the422/44 results. Supervision ByteTrack and SQLAlchemy Result.tuples deprecation warnings remain; no test was weakened to suppress them.

## Exact reproducible backend command from this run

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/backend
PYTHONDONTWRITEBYTECODE=1 \
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \
RS_MISSION_REAL=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://rslogin_testroot@127.0.0.1:55481/postgres \
RS_TEST_DATABASE_NAME=rsmission_final_regression \
RS_TEST_ALLOW_DATABASE_RESET=rsmission_final_regression RS_TEST_EXPECTED_PORT=55481 \
PYTHONPATH=.. ../.venv.integration/bin/python -m pytest tests -o addopts='' -q
```

55481 is this mission's disposable cluster, never the user's55446 database. After cleanup, use `.venv.integration/bin/python scripts/verify-integration.py backend` or `... flows` from the project root to create a fresh uniquely named cluster. It records commands/exit codes and closes only its own servers. No broad DATABASE_URL fallback is accepted by the test fixtures.

Other actual commands:

```bash
PYTHONDONTWRITEBYTECODE=1 RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx .venv.integration/bin/python -m pytest tests -o addopts='' -q
PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH node frontend/e2e/live-login-recovery.mjs
.venv.integration/bin/python scripts/verify-integration.py flows
```

The live browser script reads only the protected verified credentials and writes authenticators privately; its public trace omits bodies/headers/cookies/secrets. The wrapper logs print no passwords. Final individual result file timestamps are captured in `test-artifact-ledger.json`; these are completion/file-modification times, not invented command start times. Only the new repeat harness has instrumented UTC start/end telemetry.

## Failure history retained and resolved

- First recovery restore rehearsal failed on missing backend PYTHONPATH. No live writes occurred; fixed root+backend import path, reran full backup/restore/rehearsal before live apply. `recovery-apply.log` vs `recovery-apply-verified.log`.
- Initial broad root run lacked legacy itsdangerous and stock model resolution; itsdangerous2.2.0 was added only to integration test requirements/venv. Explicit checked readonly stock-model mapping and stale unsupported.pt test assertions were corrected. A later run accidentally omitted RS_YOLOX_MODEL_PATH:3 failed/210 passed; rerun with documented setting:213 passed. Both logs retained.
- Targeted Ruff initially reported formatting/unused imports and fixture subprocess annotations; reviewed fixes now pass. `.venv.integration` itself does not include Ruff; the already isolated `/tmp/rsint-venv/bin/ruff` was used. No original venv mutation.
- PWA lint found one existing Vite config formatting error; fixed using its installed Prettier; final lint passes. React empty-data spinner was exposed by actual screenshot inspection, fixed with explicit loaded state, then browser assertions strengthened.

## Scope boundaries

Positive recorded incident fixture is SYNTHETIC TEST, generated from a licensed frozen real frame. Real moving replay produced detections/tracks but zero eligible live incident events. No accuracy score is claimed. Full configuration/approval via API is proved, while two-admin browser configuration editing and live positive event export remain open. Existing integration password/MFA/login/dashboard and process-restart session are independently verified on A; fixture feature journeys are on B. No conflation.

---

# Historical ledger preserved below

# Test execution ledger

All tests in this mission ran in the agent-visible environment on the native loopback network. Original services were not restarted. Artifact timestamps below are UTC file completion/modification times, not instrumented command start times. pytest durations/counts are copied from actual output. Shell exit codes were not persisted uniformly; passing summaries establish test outcome but are not invented process telemetry.

## Guarded database command used

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 \
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \
RS_MISSION_REAL=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55479/postgres \
RS_TEST_DATABASE_NAME=rsmission_release RS_TEST_ALLOW_DATABASE_RESET=rsmission_release \
RS_TEST_EXPECTED_PORT=55479 PYTHONPATH=.. \
/home/justin7m8/Documents/roadsentinel/.venv/bin/python -m pytest tests -o addopts='' -q
```
Final full result: **419 passed, 2 skipped, 11 warnings in 109.86 s**. The suite includes actual model/HTTP/Chromium tests via RS_MISSION_REAL=1; older opt-in tests test_real_yolo_e2e and test_offline_analytics_real_video remained skipped because their separate flags were not enabled. No skipped test was counted as passing.

Final focused rerun used rsmission_negatives and `tests/test_mission_vertical.py tests/test_managed_live_runtime.py tests/test_managed_heartbeat.py -o addopts='' -q -s`: **3 passed in 18.32 s**. This added explicit cross-tenant/patrol/auditor promotion denials and private media denial. The same test verifies UI duplicate submission returns the original alert.

Database final inspection: rsmission_negatives / 127.0.0.1 / 55479 / postgres; Alembic 0021; **32 tables ENABLE + FORCE RLS**. rs_test_app BYPASSRLS=false, rs_test_owner BYPASSRLS=true. Existing integration READ ONLY identity: rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b; lookup owner rsint_owner_261110b BYPASSRLS=false; platform/unit-a lookups NULL. Administrator connection to integration was unavailable; no integration DB writes.

## Other exact commands

- Pipeline: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend <read-only-python> -m pytest tests/test_remote_config.py tests/test_live.py tests/test_sources.py tests/test_rules.py tests/test_rules_rates.py tests/test_sink.py tests/test_catalog_sync.py tests/test_consent.py -o addopts='' -q`: **91 passed in 2.29 s**.
- React: `npm run typecheck && npm test && npm run build`: **15 tests passed**, build passed. `npm run lint`: passed. Full captured Vite output was returned by the tool; frontend-typecheck.log records typecheck.
- PWA: `npm ci --offline`; then Node 22 PATH and `npm run typecheck && npm test && npm run build`: **9 passed**, typecheck/build passed in pwa-verified.log. Initial Node 20 run had two Vitest worker errors; initial build found missing tokens.css, restored from original source. Config uses configurable RS_API_ORIGIN via Vite loadEnv.
- Core changed services: `ruff check backend/app/services/offline_promotion.py backend/app/api/ingest.py backend/app/api/offline_analytics.py roadsentinel/remote_config.py`: passed (ruff-core.log). Whole-tree Ruff was not green and is not claimed; imported/offline/test lint findings remain in ruff logs.
- `python -m compileall -q backend/app roadsentinel`: passed. Shell guard script syntax was validated in previous prerequisite work; it was not executed against integration.

## Real model and fixture provenance

Model: YOLOX-S ONNX SHA-256 c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063, CPUExecutionProvider; Supervision 0.30.7 ByteTrack, ONNX Runtime 1.23.2. Read-only approved local model path, no model download and no install into original venv.
Media: Editor, Street traffic.webm, Wikimedia Commons, CC BY 3.0; SHA-256 e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2. Raw licensed input remained in /tmp/Street_traffic.webm. Positive recorded fixture freezes the first real frame, resizes to 640x360, writes 36 s at 5 fps in test-owned tmp_path and processes at 2 fps. Actual outcome: 60 model samples and 9 obstruction candidates. Existing rule uses 90% dwell coverage tolerance (candidate reason reports 27 s for the configured 30 s); this must not be described as an observed street obstruction or exact threshold certification.
Live test: loopback-only MJPEG replay of the same licensed moving recording. Approved config/grant rows were fixture-created. Actual subprocess obtained lease, ACKed revision 1, produced two distinct authenticated preview payloads, then stopped on disable. External live and physical camera were not tested. Per-condition detector accuracy and live inference latency percentiles were not recorded as new acceptance metrics.

## Executed browser scope

Actual Chromium via frontend/e2e/mission-review.mjs: password → TOTP → /app/analiza-video → reason → explicit resubmission of already promoted candidate → same /app/alerte/{id} → rejected state, synthetic source label and playable protected clip. Upload/job and first promotion were real HTTP, not browser interactions. No claim that browser performed the upload or first promotion. Screenshot: screenshots/recorded-review.png; inspected, no auth secrets shown. Full UI confirm/case/export/archive/restart and live camera-detail browser journey remain unverified.

## Retained run artifacts (failures included)

### backend-final.log
Artifact UTC: 2026-11-10T00:39:39.698014+00:00
Outcome excerpt: 419 passed, 2 skipped, 3 warnings in 132.82s (0:02:12)

### backend-full.log
Artifact UTC: 2026-11-10T00:39:39.661580+00:00
Outcome excerpt: 6 failed, 411 passed, 2 skipped, 2 warnings in 101.89s (0:01:41)

### backend-release.log
Artifact UTC: 2026-11-10T00:39:39.667985+00:00
Outcome excerpt: 419 passed, 2 skipped, 11 warnings in 109.86s (0:01:49)

### backend-targeted-utf8.log
Artifact UTC: 2026-11-10T00:39:39.707103+00:00
Outcome excerpt: Inspect retained bounded trace; no passing summary recorded.

### backend-targeted.log
Artifact UTC: 2026-11-10T00:39:39.694132+00:00
Outcome excerpt: Inspect retained bounded trace; no passing summary recorded.

### browser-live-final.log
Artifact UTC: 2026-11-10T00:39:39.666517+00:00
Outcome excerpt: 2 failed, 1 warning in 34.31s

### browser-live-verified.log
Artifact UTC: 2026-11-10T00:39:39.667258+00:00
Outcome excerpt: 2 passed, 9 warnings in 18.35s

### frontend-lint.log
Artifact UTC: 2026-11-10T00:39:39.696436+00:00
Outcome excerpt: Inspect retained bounded trace; no passing summary recorded.

### frontend-typecheck.log
Artifact UTC: 2026-11-10T00:39:39.658122+00:00
Outcome excerpt: Inspect retained bounded trace; no passing summary recorded.

### managed-live.log
Artifact UTC: 2026-11-10T00:39:39.695429+00:00
Outcome excerpt: 1 failed in 1.36s

### pipeline-final.log
Artifact UTC: 2026-11-10T00:39:39.662143+00:00
Outcome excerpt: 90 passed in 2.21s

### pipeline-release.log
Artifact UTC: 2026-11-10T00:39:39.695551+00:00
Outcome excerpt: 91 passed in 2.29s

### pipeline-targeted.log
Artifact UTC: 2026-11-10T00:39:39.709623+00:00
Outcome excerpt: 3 failed, 85 passed in 2.31s

### pipeline-verified.log
Artifact UTC: 2026-11-10T00:39:39.667802+00:00
Outcome excerpt: 90 passed in 2.52s

### pwa-install.log
Artifact UTC: 2026-11-10T00:39:39.663915+00:00
Outcome excerpt: Inspect retained bounded trace; no passing summary recorded.

### pwa-node22.log
Artifact UTC: 2026-11-10T00:39:39.710819+00:00
Outcome excerpt: ✓ built in 120ms; Build failed with 1 error:; Error: Build failed with 1 error:

### pwa-verified.log
Artifact UTC: 2026-11-10T00:39:39.664074+00:00
Outcome excerpt:       Tests  9 passed (9); ✓ built in 291ms; ✓ built in 46ms

### real-vertical.log
Artifact UTC: 2026-11-10T00:39:39.713760+00:00
Outcome excerpt: 1 failed in 2.16s

### ruff-core.log
Artifact UTC: 2026-11-10T00:39:39.709692+00:00
Outcome excerpt: All checks passed!

### ruff-final.log
Artifact UTC: 2026-11-10T00:39:39.696357+00:00
Outcome excerpt: Found 9 errors.

### ruff-last.log
Artifact UTC: 2026-11-10T00:39:39.708514+00:00
Outcome excerpt: Found 33 errors (5 fixed, 28 remaining).

### ruff-new.log
Artifact UTC: 2026-11-10T00:39:39.713042+00:00
Outcome excerpt: Found 47 errors (4 fixed, 43 remaining).

### ruff-pending.log
Artifact UTC: 2026-11-10T00:39:39.697425+00:00
Outcome excerpt: Found 8 errors (2 fixed, 6 remaining).

### vertical-final.log
Artifact UTC: 2026-11-10T00:39:39.668657+00:00
Outcome excerpt: 2 passed, 1 warning in 9.30s

### vertical-release.log
Artifact UTC: 2026-11-10T00:39:39.696791+00:00
Outcome excerpt: 3 passed, 9 warnings in 18.32s

## Additional executed acceptance: export and source recovery

After the earlier checkpoint, real HTTP case export uncovered two integration defects: CaseError/ExportError were not registered with the application error mapper (not-ready export answered 500), and approval API approve/deny/revoke did not call the existing export-job transition hook. app.main now registers the existing domain response mapping; app.api.unblur connects on_approval_decided. No policy was bypassed. The expanded real-model test adds a case observation, records the fixture's explicit CC BY 3.0 license through the existing admin grant API, requests export, observes not-ready 409, obtains independent admin approval, generates/downloads the encrypted package through signed authenticated access, and verifies the canonical manifest digest and all member hashes using verify_package. Package remains unsigned: hash integrity is not independent legal custody. **14 passed in 17.29 s** with the approvals suite (case-export-release.log).

The managed test now forcibly interrupts only sockets belonging to its controlled replay server and temporarily refuses reconnection. It observes authoritative reconnecting health, expiry of stale preview (404), restoration of actual frames and healthy state, then stops the worker on disable. **1 passed in 14.70 s** (managed-recovery.log). This does not establish external-live availability or multi-camera capacity. Approved configuration state is still fixture-created; actual two-admin UI activation and revision change remain unverified.

The full original-suite checkpoint was 419 passed + 2 skipped; backend-final-proof.log is the subsequent full run including these added assertions. Consult its final summary before using it as release evidence. Docs checker now works without Git metadata; snapshot omissions and quoted relative links were corrected, with 0 broken links in 85 Markdown files at that checkpoint. README source snapshot is README_BEFORE_SOURCE.txt.

## Final checked release snapshot

`backend-final-proof.log`: **419 passed, 2 skipped, 15 warnings in 135.04 s**, including the added real-model/HTTP/Chromium/export/recovery assertions. `dedicated-runtime.log`: **5 passed in 27.91 s** in `/tmp/rsint-venv` (independent of original venv, OpenCV 4.12.0.88). `requirements.integration-test.txt` records the reproduced dependency set. `pipeline-release.log`: **91 passed**; React **15**, PWA **9**, both typechecks/builds passed. Core changed services Ruff passed; original/imported whole-tree style debt remains unclaimed. `docs-check-final.log`: **0 broken links in 85 Markdown files**.

Full case export and controlled source recovery are now passed local acceptance components, as described in the preceding appendix. Remaining P0 acceptance is actual existing-integration authentication/rollout, complete browser first-creation and case/export interaction, retained-state service restart/crash cleanup, real approved-revision UI change/rollback, multi-camera bounds, broader permission/grant/tamper/hold cases and representative moving incident positives/negatives. These prevent marking either complete against the full mission. External live remains BLOCKED pending rights.

Final original-source recheck: 307 primary and 301 review source files unchanged relative to the recorded late baseline. No original worktree mutation command, Git commit/init/push/remote mutation, or original database write was performed. Existing integration DB and protected credentials were not modified. Source changes have not been restarted into the preserved integration API process.

Test-owned cluster at /tmp/rsmission-RSjATEiF/pgutf stopped after exact server/data-directory identity check at 2026-11-10T00:49:04.398985+00:00. Files retained; no protected database or unrelated process stopped.

## Final preservation and repeat-restore proof

The completed0022 database, including real enrolled MFA state, was backed up and restored again using `scripts/recover_integration_login.py --rehearse-only`. Every row digest matched, narrow lookup ownership was re-established in the clone and the clone stopped cleanly. No live DB mutation occurred in this repeat drill. Proof: runtime_verification/recovery-idempotent-rehearsal.log. New private backup: backend/.integration-backups/20261110T131915Z-5be60312. The repair supports both old and already-hardened ownership states without blind seeding.

Final tenant-scoped app-role checks found9 existing accounts with matching saved password and all4 Unit A accounts with MFA enabled/no exemptions: runtime_verification/account-inspection-after.json. Actual function definitions/search_path/ACLs and tenants/users policies: runtime_verification/lookup-function-contracts.json. Full disposable schema proof: runtime_verification/disposable-schema-proof.json,0022 and32 FORCE tables.

Test cluster55481 was stopped only after SELECT identity+data_directory exactly matched its recorded mission-owned root. Runtime B2 stopped automatically; existing55446 PostgreSQL and5175/8003 remain running. Final direct/proxy health/readiness/OpenAPI200 and unauthenticated protected401 are in runtime_verification/final-http-status.json. Frontend was rerun through the instrumented runner after the empty-dashboard fix: all19 tests/lint/TypeScript/build pass; exact commands/timing in runtime_verification/runs/20261110T131348Z-6f99f550/commands.json. Final documentation link check:0 broken links in93 active Markdown files; private dependency trees and frozen source evidence are intentionally excluded.
