# Fresh browser mission execution ledger

Updated 2026-11-10T23:54:00.244161+00:00 (local date 2026-11-11, Europe/Bucharest).

Runtime A: existing UI5175 → API8003 → `rsint_20261110b@127.0.0.1:55446`, app `rsint_app_261110b`, Alembic0022.
Runtime B: new uniquely named clusters, databases and test-owned files; actual identities are in each run's `database.json`.
Runtime C: both original source trees/databases, read-only and never used for writes.
All browser actions use genuine Chromium156.0.8078.4 via Playwright, real Vite/FastAPI/PostgreSQL, no network interceptions or mocked success responses.
[Live identity/proxy/RLS proof](runtime_verification/browser-20261111T011541+0200/active-runtime-final.json); [timestamped screenshot hashes](REAL_BROWSER_SCREENSHOTS/2026-11-11/index.json).


| Suite | Fresh outcome | Evidence |
|---|---|---|
| Entire backend |423 passed,0 failed,2 skipped | [backend.log](runtime_verification/runs/20261110T234143Z-edae720a/backend.log) |
| Entire root/pipeline |221 passed,0 failed,0 skipped | [pipeline.log](runtime_verification/runs/20261110T234217Z-655b6cb9/pipeline.log) |
| Focused browser recorded |1 passed,0 failed,0 skipped | [browser.log](runtime_verification/runs/20261110T232618Z-eb8e75d7/browser.log) |
| Focused camera browser/real worker |1 passed,0 failed,0 skipped | [camera.log](runtime_verification/runs/20261110T234129Z-259e8c90/camera.log) |
| React tests |24 passed,0 failed,0 skipped | [test.log](runtime_verification/runs/20261110T232408Z-16c65bc9/test.log) |
| React lint/build incl.TypeScript |PASS | [commands.json](runtime_verification/runs/20261110T232408Z-16c65bc9/commands.json) |
| Secure PWA tests |9 passed,0 failed,0 skipped | [test.log](runtime_verification/runs/20261110T232408Z-c6fd661f/test.log) |
| Secure PWA lint/format/build incl.TypeScript |PASS | [commands.json](runtime_verification/runs/20261110T232408Z-c6fd661f/commands.json) |
| Native Chromium auth |5 role journeys passed,0 JS page errors | [auth-final-code.log](runtime_verification/browser-20261111T011541+0200/auth-final-code.log) |
| Fresh migrations |base→0022 in each B cluster; one head; lookup-owner/RLS assertions | backend/new cluster logs |
| Live schema |0022,32 named ENABLE+FORCE RLS tables, app NOBYPASS, tenant-negative read | [active-runtime-final.json](runtime_verification/browser-20261111T011541+0200/active-runtime-final.json) |

The two focused cases are included in the423 backend total; do not add them as distinct unique tests. Backend count rose from historical419/422 to423 because the full process-restart browser journey was added. Root count rose213→214 for cancellation, then221 for approved counting-line validation/reconciliation. React count24 includes provenance/redaction regressions; PWA remains9. Warnings are actual ByteTrack removal/SQLAlchemy Result.tuples deprecations, not accuracy warnings suppressed to pass.

Two legacy backend tests remain skipped by their own opt-ins: test_real_yolo_e2e requires RS_RUN_REAL_YOLO_E2E and an in-tree weight/media path; test_offline_analytics_real_video requires RS_OFFLINE_ANALYTICS_REAL_VIDEO. This run does not claim those legacy harnesses passed. The new mission/browser/camera tests genuinely execute the stock model and Chromium separately. PWA HTTPS installation and field accuracy are NOT RUN.

| Command stage | UTC start | Duration | Exit | Bounded log |
|---|---|---|---|---|
| `initdb` | `2026-11-10T23:41:43.070322+00:00` | 1.517s | 0 | [initdb.log](runtime_verification/runs/20261110T234143Z-edae720a/initdb.log) |
| `start` | `2026-11-10T23:41:44.587882+00:00` | 0.114s | 0 | [start.log](runtime_verification/runs/20261110T234143Z-edae720a/start.log) |
| `backend` | `2026-11-10T23:41:44.702787+00:00` | 344.834s | 0 | [backend.log](runtime_verification/runs/20261110T234143Z-edae720a/backend.log) |
| `stop` | `2026-11-10T23:47:30.897426+00:00` | 49.582s | 0 | [stop.log](runtime_verification/runs/20261110T234143Z-edae720a/stop.log) |
| `initdb` | `2026-11-10T23:26:18.280923+00:00` | 1.066s | 0 | [initdb.log](runtime_verification/runs/20261110T232618Z-eb8e75d7/initdb.log) |
| `start` | `2026-11-10T23:26:19.347085+00:00` | 0.114s | 0 | [start.log](runtime_verification/runs/20261110T232618Z-eb8e75d7/start.log) |
| `browser` | `2026-11-10T23:26:19.461798+00:00` | 61.78s | 0 | [browser.log](runtime_verification/runs/20261110T232618Z-eb8e75d7/browser.log) |
| `stop` | `2026-11-10T23:27:21.242442+00:00` | 0.616s | 0 | [stop.log](runtime_verification/runs/20261110T232618Z-eb8e75d7/stop.log) |
| `initdb` | `2026-11-10T23:41:29.679795+00:00` | 1.518s | 0 | [initdb.log](runtime_verification/runs/20261110T234129Z-259e8c90/initdb.log) |
| `start` | `2026-11-10T23:41:31.197798+00:00` | 0.114s | 0 | [start.log](runtime_verification/runs/20261110T234129Z-259e8c90/start.log) |
| `camera` | `2026-11-10T23:41:31.312773+00:00` | 183.021s | 0 | [camera.log](runtime_verification/runs/20261110T234129Z-259e8c90/camera.log) |
| `stop` | `2026-11-10T23:44:34.334411+00:00` | 0.819s | 0 | [stop.log](runtime_verification/runs/20261110T234129Z-259e8c90/stop.log) |
| `pipeline` | `2026-11-10T23:42:17.662192+00:00` | 7.735s | 0 | [pipeline.log](runtime_verification/runs/20261110T234217Z-655b6cb9/pipeline.log) |
| `test` | `2026-11-10T23:24:08.801546+00:00` | 2.372s | 0 | [test.log](runtime_verification/runs/20261110T232408Z-16c65bc9/test.log) |
| `lint` | `2026-11-10T23:24:11.173934+00:00` | 2.369s | 0 | [lint.log](runtime_verification/runs/20261110T232408Z-16c65bc9/lint.log) |
| `build` | `2026-11-10T23:24:13.543357+00:00` | 8.132s | 0 | [build.log](runtime_verification/runs/20261110T232408Z-16c65bc9/build.log) |
| `test` | `2026-11-10T23:24:08.803952+00:00` | 1.718s | 0 | [test.log](runtime_verification/runs/20261110T232408Z-c6fd661f/test.log) |
| `lint` | `2026-11-10T23:24:10.522170+00:00` | 3.772s | 0 | [lint.log](runtime_verification/runs/20261110T232408Z-c6fd661f/lint.log) |
| `build` | `2026-11-10T23:24:14.294849+00:00` | 4.173s | 0 | [build.log](runtime_verification/runs/20261110T232408Z-c6fd661f/build.log) |

Repeat from integration root: `python3 scripts/verify-integration.py backend`, then `pipeline`, `frontend`, `pwa`; focused `browser` and `camera` create independent owned clusters. Requirements are .venv.integration, Node22, local licensed source, configured verified model, ffmpeg and installed Playwright Chromium. No environment defaults can reset the existing native DB; the runner clears RS_/VITE_/DATABASE_URL, uses unique guarded names/ports and stops only its own cluster.

Failed experiments are retained. Earlier camera-ui-start run failed on duplicate/obscured selectors (harness), then private media-root mismatch (fixed pipeline/media), then repeated browser password logins hit existing throttle (fixed session reuse, not weakened limits). Full run20261110T233508Z-7edbc976 had422 pass/1 fail/2 skip at that checkpoint; the final full result above supersedes it. Earlier requested3FPS run produced75 frames and has been replaced by the90-frame regression proof. Failed login-navigation wait assumptions and nominal source timestamp scan were corrected without fabricating results.

No secrets/cookies/QR seeds/ZIP media are copied into this ledger. Temporary test evidence warnings are intentional: B uses a temporary store and verifies persistence across process restart, not across fixture teardown. Native A data is preserved.

## Final focused security and static verification

After making fixture-user repr hide TOTP/password, `python3 scripts/verify-integration.py auth` passed **42/0/0** (lookup-owner, repeated/partial seed, password and MFA),22.63s on its own fresh cluster. This is overlapping regression coverage, not42 new unique tests. [Commands](runtime_verification/runs/20261110T235235Z-251c0912/commands.json), [result](runtime_verification/runs/20261110T235235Z-251c0912/auth.log).

Final `compileall -q backend/app backend/alembic roadsentinel scripts backend/tests`, targeted Ruff on15 changed source/test/helper files, Node syntax checks of the three browser scripts and `python3 scripts/check_docs.py` all returned0. Logs: [compile](runtime_verification/browser-20261111T011541+0200/compile-final.log), [Ruff](runtime_verification/browser-20261111T011541+0200/ruff-final.log), [docs](runtime_verification/browser-20261111T011541+0200/docs-check-final.log), [one Alembic head](runtime_verification/browser-20261111T011541+0200/alembic-heads.log). Whole-tree style/type perfection is not claimed. [Artifact sanitization](runtime_verification/browser-20261111T011541+0200/artifact-sanitization.json).
