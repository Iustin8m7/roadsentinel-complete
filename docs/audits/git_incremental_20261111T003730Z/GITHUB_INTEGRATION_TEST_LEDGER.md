# Incremental integration test ledger — 2026-11-11

All results below were executed in this mission. [TEST_RUN_INDEX.csv](TEST_RUN_INDEX.csv) indexes every guarded-runner command with UTC start/end, monotonic duration, exit status, actual test counts and DB/port. Each run's `commands.json` retains the exact command array/cwd. Failed attempts remain alongside successful reruns. Directory timestamps are checkpoints; a system UTC discontinuity occurred, so use individual command records rather than subtracting directory names.

## Final suite evidence

From `/home/justin7m8/Documents/roadsentinel-integration`:

| Command | Actual result | Evidence |
|---|---|---|
| `python3 scripts/verify-integration.py backend --evidence-root docs/audits/git_incremental_20261111T003730Z/runs` | 437 passed,0 failed,2 skipped;27 deprecation warnings;360.52s. Fresh migrations and schema-security check pass | [Full suite](runs/20261111T120622Z-d8d4f7f5/backend.log), [commands](runs/20261111T120622Z-d8d4f7f5/commands.json), [schema](runs/20261111T120622Z-d8d4f7f5/schema-security.log) |
| Same runner `pipeline` | 229 passed,0 failed/skipped;2 Supervision deprecation warnings | [Final pipeline](runs/20261111T122840Z-c86bc187/pipeline.log) |
| Same runner `frontend` | 112 passed,0 failed/skipped; ESLint PASS, TypeScript/Vite production build PASS | [Tests](runs/20261111T121604Z-faeaa4ed/test.log), [lint](runs/20261111T121604Z-faeaa4ed/lint.log), [build](runs/20261111T121604Z-faeaa4ed/build.log) |
| Same runner `pwa` | 9 passed,0 failed/skipped; ESLint/Prettier PASS, TypeScript/Vite PWA build PASS | [Tests](runs/20261111T115333Z-7e098c31/test.log), [lint](runs/20261111T115333Z-7e098c31/lint.log), [build](runs/20261111T115333Z-7e098c31/build.log) |
| Same runner `incremental` | 84 passed,0 failed/skipped; fresh schema/role inventory PASS | [API/media/security tests](runs/20261111T120657Z-3ed265eb/incremental.log), [schema](runs/20261111T120657Z-3ed265eb/schema-security.log) |
| Same runner `browser`, after late media-offset fix | 1 passed; real moving/synthetic browser, package hash/tamper and OS restart; fresh schema check PASS | [Browser](runs/20261111T121645Z-341086a3/browser.log), [structured proof](runs/20261111T121645Z-341086a3/complete-browser-result.json) |
| Same runner `camera`, after late timing fix | 1 passed;8 deprecation warnings;196.49s including natural90s lease expiry; fresh schema check PASS | [Camera browser/worker](runs/20261111T122821Z-6a5290e8/camera.log), [commands](runs/20261111T122821Z-6a5290e8/commands.json), [schema](runs/20261111T122821Z-6a5290e8/schema-security.log) |

The full437 run preceded the final additive clip-offset/cadence fields. Both affected real-model browser tests, pipeline229 and frontend112 were rerun after that change; do not add their passing counts to437 as if they were new unique backend tests. Earlier frontend109 became112 after three evidence-timing regressions. Historical423/221/24/9 counts were not reused as fresh proof.

The two skipped full-suite tests are `test_real_model_live_replay_posts_signed_telemetry_to_tenant_api` (`backend/tests/test_real_yolo_e2e.py`: requires `RS_RUN_REAL_YOLO_E2E=1` and its legacy integration-local model location) and `test_real_video_upload_yolox_tracker_artifact_and_analytics` (`backend/tests/test_offline_analytics_real_video.py`: requires `RS_OFFLINE_ANALYTICS_REAL_VIDEO`). These optional older harnesses were not enabled. They are NOT failing tests and NOT proof of browser success. The supported current opt-in `RS_MISSION_REAL=1` harness actually ran moving inference, analytics and live worker/browser scenarios with a configured read-only verified model; field accuracy remains untested.

Selected Python Ruff checks passed (`ruff.log`, `timing-python-quality.log`); compileall passed (`compile.log`, `compile-timing.log`). A mistaken Ruff invocation against a TypeScript file is retained as `timing-quality-attempt.log`; TypeScript was validated with its actual compiler and ESLint, not Ruff. Documentation links are checked separately after final reports exist. Build outputs are unique run-owned directories; existing `frontend/dist` media were not overwritten.

## Runtime isolation and actual migrations

- Full suite B: [rsmission_verify_327f32f2db, port49707](runs/20261111T120622Z-d8d4f7f5/database.json).
- Final recorded B and final camera B each have their own `database.json` and owned loopback service ports. These are independent of native5175/8003/55446.
- Each initialized a new PGDATA and migrated base→0022; all32 tenant tables are enumerated with enabled+forced RLS. Restricted `rs_test_app` is NOSUPERUSER/NOBYPASSRLS. The disposable bootstrap migrator's documented BYPASSRLS is reported separately; it is never the API/worker identity. Native app is independently NOBYPASSRLS.
- App-role direct missing/wrong tenant reads, cross-tenant writes, role denials, HMAC/nonce/replay/idempotency, seed/lookup/MFA, media access, crypto/retention and case/export checks are in the full suite. A table count alone is not isolation proof.
- All owned clusters were stopped in `finally`. No original DB, old demo DB or existing integration schema was reset/migrated/seeded.

## Genuine Chromium on native A

Browser: Chromium156.0.8078.4 via installed Playwright, fresh contexts, no page/API mock success responses. Command from `frontend/`:

```bash
RS_LIVE_EVIDENCE_DIR=/home/justin7m8/Documents/roadsentinel-integration/docs/audits/git_incremental_20261111T003730Z/native-final /home/justin7m8/miniconda3/envs/rs-node22/bin/node e2e/live-login-recovery.mjs
```

[Final native log](native-final-browser.log), [request/status/role assertions](native-final/live-browser-result.json), [operator dashboard](native-final/screenshots/live-operator.png), [admin](native-final/screenshots/live-tenant_admin.png), [auditor](native-final/screenshots/live-auditor.png), [logout](native-final/screenshots/logout-operator.png). Five flows pass: operator with wrong password/TOTP negatives, admin, patrol, auditor, then operator again. Each checks real password→mandatory MFA→appropriate destination, actual protected data/role denials, reload/new tab, logout401 and guest redirect. Secrets remain private; no browser trace/HAR containing request bodies/cookies is published.

The only native process stopped was verified integration Uvicorn, after read-only exact DB identity and zero scoped development jobs/leases; see `native-pre-restart.json`, `native-timing-pre-restart.json` and both restart logs. Native Vite proxy stayed `RS_API_ORIGIN=http://127.0.0.1:8003`. Existing account hashes/password/MFA were not reset. Native authentication writes sessions/audit legitimately; new camera/evidence/case fixtures were confined to B.

## Recorded journey and model evidence

Source: locally available `Street_traffic.webm`, Editor/Wikimedia Commons, CC BY3.0; SHA-256 `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`. No external camera was fetched. Real moving derivative:30s,300 encoded10FPS frames,960×540, sampled at3FPS. Model YOLOX-S ONNX SHA-256 `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`, COCO motor vehicle IDs2/3/5/7, CPUExecutionProvider and actual Supervision ByteTrack.

Observed:90 sampled frames,1,013 detection observations,65 unique tracker IDs (20 bus/37 car/8 truck),4 configured line crossings,1,013 heatmap observations. These are model/tracker outputs, not independently validated vehicle counts. Moving footage produced no incident candidates in this run. Mean model latency99.46ms, p95 173.82ms in that run, not a hardware guarantee.

A separate36s frozen licensed-frame SYNTHETIC TEST derivative generated8 candidates from72 real-model samples. Operator browser explicitly promoted one, reviewed redacted encrypted media, rejected it with reason, created note/bookmark, requested export, obtained a distinct admin's approval, downloaded and verified the package. A tampered copy failed SHA-256 verification. Real OS backend restart preserved session/case/decision/note/media ciphertext, and archive retrieved the same event without duplicates. No real incident accuracy is claimed.

Playback: six-second encoded clip measured1.1003s advancement in1.1003s wall time at1×. Candidate is at source/clip start0s: the browser now jumps to0 rather than guessed midpoint3. New cadence metadata drives frame steps; unknown legacy cadence/offset is not fabricated. The underlying live encoder remains CFR over observed span rather than exact irregular PTS.

[Moving upload](runs/20261111T121645Z-341086a3/screenshots/moving-upload.png), [actual overlay](runs/20261111T121645Z-341086a3/screenshots/moving-annotated-result.png), [heatmap/counts](runs/20261111T121645Z-341086a3/screenshots/moving-heatmap-counts.png), [synthetic candidates](runs/20261111T121645Z-341086a3/screenshots/synthetic-candidates.png), [evidence](runs/20261111T121645Z-341086a3/screenshots/recorded-evidence-one-times.png), [independent approval](runs/20261111T121645Z-341086a3/screenshots/independent-approval.png), [restart](runs/20261111T121645Z-341086a3/screenshots/complete-persist.png).

## Camera/editor/recording journey

Camera is explicitly LOCAL RECORDED REPLAY. Input is a moving licensed32–35s excerpt on a test-owned loopback MJPEG server. Deliberately synthetic whole-scene road-zone geometry produces a deterministic pedestrian candidate; it is not a genuine pedestrian violation.

Browser creates managed camera, rejects unsafe source URL, registers replay reference and scoped time/quality/retention/export grant, draws polygon and line, moves a point with keyboard, uses undo/redo and invalid-coordinate validation, submits revision. Distinct administrator approves/activates; proposer self-approval returns403. Real worker starts via UI with a private allowlisted profile, leases and ACKs exact revision1. Real annotated preview changes; conflicting worker is refused before source access.

Signed scoped whole-recording upload is playable through the tile: actual native video duration/1×/pause/seek, signed byte206, and exact server-scoped `Istoric` filter all pass. A genuine model observation with synthetic geometry becomes signed encrypted evidence; operator browser rejects and jumps to actual encoded event frame. Case note/independent export/hash validation also pass. Revision2 approval/restart/ACK, forced stream failure/reconnect/stale preview404, worker SIGKILL/natural90s lease expiry/new epoch, rollback/ACK1, disable/actual stop and grant revocation/old recording403 all pass.

[Visual editor](runs/20261111T122821Z-6a5290e8/screenshots/camera-visual-1-editor.png), [mobile editor](runs/20261111T122821Z-6a5290e8/screenshots/camera-visual-1-editor-mobile.png), [approval](runs/20261111T122821Z-6a5290e8/screenshots/camera-approve-1.png), [real preview](runs/20261111T122821Z-6a5290e8/screenshots/camera-preview-0.png), [recording player](runs/20261111T122821Z-6a5290e8/screenshots/camera-recording-0-player.png), [history](runs/20261111T122821Z-6a5290e8/screenshots/camera-recording-0.png), [actual worker metrics](runs/20261111T122821Z-6a5290e8/worker-summaries.json).

The final run's exact closed-worker frame/count/FPS/latency/RSS measurements are preserved in the linked allow-listed JSON, rather than reusing earlier run numbers. Closing reports are not a camera liveness signal and do not prove production capacity; single-camera local smoke only.

## Public UX/report and retained failures

Desktop1440, tablet820 and mobile390 public layout/screenshots pass without horizontal overflow; media is a rights-cleared real-model derivative clearly marked LOCAL RECORDED REPLAY. Public decisions remain local simulation and auth/me remains401. Login no longer has an ineffective remember checkbox. The print report shows four actual loaded alerts, Europe/Bucharest context and fits one generated A4 page: [PDF](runs/20261111T121645Z-341086a3/screenshots/activity-report.pdf). Rejected alert is absent from open queue and visible among reviewed records after restart.

Failures retained: intermediate missing Query import; clipped/overlapped visual editor; nullable min_y worker crash; stale test selectors/redo selection; incorrect auditor catalogue/header test assumptions; nullable archive TypeScript shapes. Each actual defect was fixed and its failing step rerun. Two earlier auxiliary schema checks assumed the disposable migration owner was NOBYPASSRLS, contrary to existing bootstrap; corrected checker now explicitly reports migration privilege and enforces the actual API role. Subsequent schema/full runs pass without changing production role privileges. No failed log was deleted or assertion weakened to permit a forbidden API action.

Not claimed: representative incident precision/recall, actual public/external camera authorization, comprehensive multi-camera soak, exact VFR gaps, installed HTTPS PWA, exhaustive accessibility/zoom/error/failure-injection combinations or production/legal certification. See the ranked backlog.

## Late lifecycle revalidation correction

The subsequent offset/assertion repeat `20261111T122240Z-05737d02` failed at rollback with worker exit-9. Investigation proved that draft/approval/rollback browser helper calls lacking `api_port` created a second API lifecycle in the same pytest process; its teardown stopped children owned by the main test API. Earlier code-zero revision/rollback checks were therefore not independent of helper teardown. Other model/preview/rights/media observations remain real, but the lifecycle claim requires the corrected rerun.

The helper now refuses a second API lifecycle while owned workers run; all post-start draft/review/rollback actions use the same running API port. The test retains the exit-code0 requirement and adds an actual UI Stop/SIGTERM check. Managed SIGTERM now cancels/counts unaccepted jobs rather than draining retrying jobs indefinitely; accepted encrypted evidence is retained. The failing log remains. The final same-API run is `20261111T122821Z-6a5290e8`; its final result and schema check must pass before signoff. Pipeline229 reran after this shutdown fix (`20261111T122840Z-c86bc187`).

Final same-API result: **1 passed,0 failed,8 deprecation warnings,196.49s**; schema-security PASS and owned cluster shutdown PASS. The actual UI Stop check returns process exit0 and releases the lease. This supersedes the confounded earlier lifecycle check; no exit-code assertion was removed. Final screenshots/worker summaries now link to this corrected run.
