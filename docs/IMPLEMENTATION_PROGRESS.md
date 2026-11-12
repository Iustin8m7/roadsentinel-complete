# Enterprise implementation tracker (local work on `release/ready`)

## 2026-11-07 HLS source adapter and authenticated candidate registry

- Added an explicit HLS transport path to `roadsentinel/sources.py`: bounded manifest
  retrieval, master-playlist variant parsing/selection with resolution and bandwidth caps,
  same-host checks for variant/segment/key references, VOD rejection for non-replay live
  mode, and OpenCV/FFmpeg capture with bounded timeouts. `cameras/iasi-piata-unirii.yaml`
  records HLS transport and conservative caps; activation and authorization remain disabled.
  No Romanian media URL was opened or decoded in this implementation step.
- Added 35 unique candidate/directory records in `cameras/romanian-source-registry.json`,
  validated by `backend/app/services/camera_discovery.py`, and authenticated
  `GET /api/cameras/discovery` guarded by `cameras:read`. The React camera page now fetches
  candidates from that API and shows source-page attribution plus adapter/status metadata.
  Entries contain no direct stream endpoint and no fabricated geometry or authorization.
- Local transport regression: `timeout 40s .venv/bin/python -m pytest tests/test_sources.py -q -s`
  — **24 passed**. Its HLS fixture generates a local MPEG-TS playlist and verifies OpenCV/FFmpeg
  decode over loopback; this is a replay fixture, not Romanian live-source evidence.
- Direct backend registry load validated **35 records**. The backend pytest command could not
  start because the configured PostgreSQL server at 127.0.0.1:5432 was unavailable. The
  disposable test server on port 55438 was also unavailable, so no database fixture was run.
- Frontend `npm run typecheck`, `npm run lint`, and `npm run build` passed; `npm test -- --run`
  reported **15 passed**. Ruff on modified Python files and `git diff --check` passed.
- This verifies adapter behavior and catalog loading only. Romanian feeds remain unverified and
  disabled; physical-live YOLO, the discovery endpoint against PostgreSQL/browser, and UI-based
  source/rule administration remain open. Next: run the discovery API and authenticated browser
  assertion using the disposable PostgreSQL instance, then enable a source only after its
  processing basis is documented.

## 2026-11-07 replay regression after camera source labels

Updated authenticated camera detail labels to distinguish `RECORDED REPLAY`, `LOCAL CAMERA LIVE`,
and `LIVE · NETWORK SOURCE`; the backend now accepts `device` in source health. `frontend/e2e/yolo-live.mjs`
was corrected to assert the explicit replay label in the annotated preview region. The bounded real
YOLOX → loopback MJPEG → signed API → disposable PostgreSQL → authenticated Chromium E2E completed
**1 passed, exit 0** after fixing two stale/ambiguous UI text locators. Browser logged 146 camera
detections, two count-line crossings, 1,196 ms heartbeat refresh; DB snapshot 65 frames / 318
detections / 23 tracks / 2 crossings / 1.593 FPS / inference p95 103.09 ms / RSS 347.5 MB. Screenshot
`data/vision/evidence/recorded-replay-overlay-2026-11-07.png` (SHA-256 is in
`END_TO_END_DEMO_EVIDENCE.md`). This is **recorded replay**, not genuine live camera proof. Frontend
typecheck, Vitest (**15 passed**) and production build passed. Focused Python sources/live/rules/
pipeline suite: **66 passed**; Ruff clean. Physical UVC remains blocked because the host has no
`/dev/video*`; Romanian external feeds remain disabled pending source-specific allowed processing.

## 2026-11-07 physical-live camera path

Implemented an explicit `device:N` source (bounded index 0–15), OpenCV V4L2 open, pipeline routing
through the supervised live reader, backend health schema support for `device`, and
`cameras/local-uvc.yaml` as a detection-only/no-fabricated-geometry profile. The rules engine now
honors `rules: []` as disabled and skips metric-speed calculations if calibration is absent.
`scripts/probe_uvc_camera.py` is a bounded, non-recording hardware diagnostic; usage is in
`docs/LIVE_CAMERA_OPERATOR_GUIDE.md`.

Evidence: `timeout 15s .venv/bin/python -m scripts.probe_uvc_camera --device-index 0 --seconds 3`
exited **2**, reporting `/dev/video0` missing. `timeout 90s .venv/bin/python -m pytest
tests/test_sources.py tests/test_live.py tests/test_rules_rates.py tests/test_pipeline_redaction.py
-q` passed **66 tests**; Ruff passed for changed Python files. No physical frames were captured,
and no physical-live YOLO/API/DB/browser claim is made. Romanian source-page metadata was reviewed
again on 2026-11-07, but no media was opened and no processing authorization was found; all remain
disabled (details in `EXACT_ROMANIAN_CAMERA_URL_AUDIT.md`). Next concrete step: connect an owned
UVC camera or supply an eligible authorized source, then run full YOLOX + signed ingest + PostgreSQL
+ authenticated Chromium E2E; worker start/stop UI controls remain open.

Historical baseline: commit `f225bfd` and a clean tree were recorded before the prior mission.
At this resume, the tree already contained tracked edits and untracked implementation files;
they were preserved. Git metadata is read-only in this workspace, so no implementation branch or
commit can be created here. No remote operations are permitted. Historical claims below are not
re-run results unless a dated entry records a current run.

Status definitions: NOT STARTED · IN PROGRESS · IMPLEMENTED · TESTED · VERIFIED · BLOCKED.
`VERIFIED` requires demonstrated acceptance criteria. A `TESTED` status records an actual test run.

| Task | Priority | Status | Work / validation / blockers |
|---|---|---|---|
| RS-001 Documentation reconciliation | High | TESTED | README/API clarify the secure backend/UI roles and legacy boundaries; `scripts/check_docs.py`: 0 broken links in 52 Markdown files. Detailed deployment and model claims still depend on runtime validation. |
| RS-002 Local Compose validation | Critical | BLOCKED | Docker daemon socket returns permission denied. Requires local Docker access approval/configuration; no stack started. |
| RS-003 Supported UI/API matrix | High | IN PROGRESS | README/API identify secure PWA, separate operator client, authoritative backend, and legacy demo boundaries. Demo curation is now fail-closed in real-backend builds even when its flag is set; broader API consolidation remains. |
| RS-004 Dependency/licensing review | High | IN PROGRESS | Selected Apache-2.0 YOLOX-S ONNX + ONNX Runtime instead of Ultralytics; package and model provenance documented. Full repository/dependency legal review remains. |
| RS-005 Detection acceptance thresholds | Critical | BLOCKED | Requires product/domain owner thresholds; evaluation framework exists but operating targets are not approved. |
| RS-006 Representative evaluation data | Critical | BLOCKED | No authorized representative labeled dataset identified; public candidate feeds are not approved data. |
| RS-007 Real model end-to-end validation | Critical | IN PROGRESS | Actual YOLOX-S loopback MJPEG replay → ByteTrack → crossing → HMAC heartbeat → tenant PostgreSQL → authenticated React detail verified in Chromium; 2 crossings, 24 tracks. No incident candidate; accuracy and external live source remain open. |
| RS-008 Full operator workflow validation | Critical | IN PROGRESS | Opt-in E2E uses actual inference, localhost API, disposable PostgreSQL, MFA-authenticated browser, and real camera API polling. Incident review and broader README workflows remain incomplete. |
| RS-009 Privacy/source governance | Critical | IN PROGRESS | Fail-closed network-source consent, disabled Iași config, camera candidate catalog, and permission-gated ranking added; legal basis/DPIA/retention and owner approvals remain blocked. |
| RS-010 Key-provider and recovery design | High | IN PROGRESS | Existing `KeyProvider`/env implementation and rotation/re-wrap procedures retained; no fresh database-backed recovery validation. Production KMS choice is external. |
| RS-011 Independent audit anchoring | High | IN PROGRESS | Local Ed25519 JSONL signer/verifier and CLI added; focused tests pass. It is not an independent production anchor until separate custody/storage is provisioned. |
| RS-012 Security hardening/review | High | IN PROGRESS | Source validation avoids embedded credentials/URL telemetry; strict heartbeat schemas, owner-scoped saved searches, query-text minimization, and checkpoint tests added. Secret scan and backend security suite pass; external dependency audit and independent review remain. |
| RS-013 Audit data retention | High | BLOCKED | Existing evidence retention is present; an approved policy is needed before changing audit retention/integrity behavior. |
| RS-014 Recovery/deployment readiness | High | BLOCKED | Existing local backup/restore procedures documented; Compose validation blocked by Docker access and no deployment is authorized. |
| RS-015 Operational alerting | High | IN PROGRESS | Source health and traffic telemetry are added to secure heartbeat; `LiveReader` now reconnects after capture open/read exceptions. Alert delivery and operational thresholds remain. |
| RS-016 Horizontal scaling | Medium | IN PROGRESS | `/api/stats` now aggregates priority/status/type counts in PostgreSQL without materializing alert rows, plate ciphertext, or event details; patrol assignment scope is retained. Horizontal worker concurrency and load measurements remain unverified. |
| RS-017 Safe camera/rule administration | Medium | IN PROGRESS | Added an audited registry-metadata editor for backend-authorized `cameras:manage` users (name, location, coordinates, timezone); camera list now exposes registry UUID/timezone. Focused contract and existing role/audit tests pass. Operational source, detection rules, zones, approvals, and config history are still incomplete. Browser verification is pending. |
| RS-018 Archive/operator workflows | Medium | IN PROGRESS | Added audited saved-search CRUD/run API and owner-scoped archive UI; searches submit via POST body (legacy GET retained), raw text is not persisted, RLS and cross-tenant behavior tested. Signed keyset paging now covers free-text and saved searches; controlled export and shift handover remain. |

## Current execution checkpoint

- Initial `git switch -c` attempt failed because `.git` is read-only. Current branch is unchanged.
- Docker CLI is installed, but access to `/var/run/docker.sock` is denied; Compose was not started.
- Backend fixture drops/recreates PostgreSQL database `rs_test`; the suite was pointed at a fresh disposable `/tmp` PostgreSQL cluster, never the existing developer database.
- `frontend/node_modules`, `secure-pwa/node_modules`, and `.venv` already exist. No dependency install performed.
- Current resume began with 28 modified tracked files and existing untracked work; no existing edits were reverted or overwritten.
- Runtime: YOLOX-S ONNX and pinned ONNX Runtime/Supervision are installed in `.venv`; actual recorded-traffic inference succeeded. The full run and provenance are in `docs/YOLO_REAL_INFERENCE_REPORT.md`.
- The pipeline module now imports without Ultralytics so its source/config helpers and explicit missing-runtime error remain usable; `run()` fails before reading a camera when YOLO is unavailable.
- Root `pytest --collect-only` now succeeds (554 tests across root and backend); root tests were run separately to avoid backend fixture database side effects. See latest dated result below.

## Test and change log

| Date | Scope | Result |
|---|---|---|
| 2026-11-06 | Initial repository/status inspection | Clean at `f225bfd`; no source changes since prior audit observed. |
| 2026-11-06 | Docker access check | Blocked: permission denied on Docker socket; no container started. |
| 2026-11-06 | Backend fixture safety review | Found destructive recreation of `rs_test`; isolated a new PostgreSQL cluster in `/tmp` on localhost port 55438 before running the suite. Existing developer database untouched. |
| 2026-11-06 | Local source validation/analytics/ranking | Added fail-closed source adapter configuration for local files and consented network sources, bounded image polling, health telemetry, image-space line counts with bounded track state, explainable permission-gated suitability scoring, and frontend camera status display. No stream or model was opened. |
| 2026-11-06 | Reader recovery and local source integration | `LiveReader` reconnects on capture open/read exceptions; generated a synthetic MP4 in a temporary test directory and verified `SourceSpec`/OpenCV decode. Regression suite: 50 passed including source, tracker, consent, audit anchor, and rules cases; Ruff clean. |
| 2026-11-06 | Audit checkpoint adapter | Added local Ed25519-signed append-only checkpoints, verification CLI and tests. Focused audit tests included above. Local same-host storage/key do not meet independent anchoring requirements. |
| 2026-11-06 | UI/docs validation | Frontend typecheck passed; Vitest 11 passed; production frontend build passed. Documentation checker: 0 broken links / 52 files. Backend heartbeat Pydantic contract and CLI help smoke check passed; compileall passed. |
| 2026-11-06 | Secure PWA validation | Typecheck passed; Vitest 9 passed; production build and service-worker generation passed. Existing Vite PWA plugin reports `inlineDynamicImports` deprecation warning. |
| 2026-11-06 | Full root suite attempt | Collection fails on existing `tests/test_rules_rates.py` import of `tests.test_rules` in this environment. Broader suite excluding that file did not complete within the available execution window and was interrupted; not counted as passed. |
| 2026-11-06 | Local deployment validation | Docker access remains denied; Compose and end-to-end acceptance scenario not run. |
| 2026-11-06 | Backend PostgreSQL integration suite | 401 tests collected and completed with exit code 0 against the isolated temporary PostgreSQL cluster, including saved-search ownership, cursor pagination, tenant binding, and cursor signature tests. Existing developer database untouched. Pytest emitted two Starlette status-code deprecation warnings. |
| 2026-11-06 | Compose validation | `docker compose --env-file .env.example -f deploy/docker-compose.yml config --quiet` passed; configured service list parsed. Docker daemon API remains permission denied even after approved local inspection; no containers started. |
| 2026-11-06 | Final heartbeat schema validation | Pydantic model rejects URL fields, invalid dimensions, overlong arrays, and negative/oversized counts; backend focused test file: 5 passed. |
| 2026-11-06 | Local secret scan | `scripts/scan_secrets.py`: 0 findings. Dependency vulnerability checks were not run because they require external vulnerability registries. |
| 2026-11-06 | Saved archive searches and query privacy | Added normalized-filter persistence (raw query discarded), tenant RLS, user ownership, 100-search cap, audited create/update/delete/run endpoints, and secure-operator archive controls. Preferred POST search body avoids exposing query text in URL logs; legacy GET remains for API compatibility. Saved-search integration includes direct DB privacy assertion. Frontend lint/typecheck, 13 tests, and production build passed. Full 401-test backend suite passed. Original full browser route walk passed in 169s; its API data was stubbed. |
| 2026-11-06 | Root pipeline/source/audit regression suite | `tests/test_analytics.py`, `test_audit_anchor.py`, `test_sources.py`, and `test_live.py`: 31 passed. |
| 2026-11-06 | Documentation and patch hygiene | `scripts/check_docs.py`: 0 broken links in 52 Markdown files; `git diff --check`: clean. |
| 2026-11-06 | Camera registry metadata administration | Camera list response now includes UUID/timezone; operator client exposes a permission-gated metadata dialog and updates local state after successful audited PATCH. Focused backend camera contract and role/audit tests: 3 passed. Frontend lint/typecheck/Vitest: 14 passed. Playwright admin edit path is running; source/rule/zone configuration remains intentionally out of scope for this editor. |
| 2026-11-06 | Demo curation safety boundary | Restricted hard-coded alert hide/reclassify behavior to explicit mock mode plus opt-in. Added unit coverage for all flag/mode combinations. Frontend lint, typecheck, 13 tests, and production build passed. Full Playwright walk completed in 168s with 0 failures while `VITE_DEMO_CURATION=1` was intentionally set in real-backend mode. |
| 2026-11-06 | Archive keyset pagination | Added signed one-hour cursors bound to tenant and normalized filter for search and saved-search APIs, deterministic timestamp/priority ordering with a monotonic tie-break, 1–100 page sizes, and append controls in the archive UI. Integration tests cover three-page traversal, saved-search continuation, tampering, tenant/filter mismatch, and expiry. Full 401-test backend suite passed; archive-only browser walk passed and the latest full UI walk completed in 169s with 0 failures. The first expanded browser attempt checked React state too early; the assertion now waits for the rendered count. API data remains stubbed in browser tests. |
| 2026-11-06 | Database-side statistics aggregation | Replaced `/api/stats` ORM materialization with SQL `GROUP BY` queries. The query loads only priority/status/type fields, remains under tenant RLS, applies patrol assignment scope, and excludes superseded alerts. Focused stats tests passed for operator totals and patrol-only counts; Ruff passed. Full 402-test backend suite completed with exit code 0 against isolated PostgreSQL. Two existing Starlette status-code deprecation warnings remain. |
| 2026-11-06 | Root test collection repair and resume validation | Removed the cross-suite `tests` package collision by changing `tests/test_rules_rates.py` to import its local helper as `test_rules`; no package marker remains. `pytest --collect-only -q` collected 554 root+backend tests with no collection errors. Focused root regression suites (`rules`, sampling rules, analytics, live reader, sources, audit anchor): **65 passed**. An isolated `pytest -q tests` invocation did not yield a completion result in this session, so the full root suite is not claimed as passing. Docker probe still returns socket permission denied. Runtime check: OpenCV present; PyTorch/Ultralytics/Supervision absent; no model weights present. |
| 2026-11-06 | Remaining root tests and import collision follow-up | Changed the calibration test helper import to resolve alongside the root tests, removing the second `tests.*` collision. `pytest -q tests --ignore=tests/test_api.py`: **132 passed, 2 skipped**. The legacy API suite and its first test were separately bounded at 20s/12s; both timed out while `TestClient.get('/api/events')` waited in Starlette's AnyIO portal, with no application response. This remains an environment/harness issue to investigate, not a pass. Root Ruff passed, documentation links: 0 broken/52 files, `git diff --check` clean. |
| 2026-11-06 | Detector optional-import path | Made `roadsentinel.pipeline` importable when Ultralytics is absent and added a clear fail-fast runtime message before camera loading. This permits weights-free pipeline utility checks without weakening inference requirements. Pipeline redaction/model-selection/runtime guard tests: **16 passed**; Ruff clean. No inference attempted. |
| 2026-11-06 | Resume checkpoint after optional-import change | Final root suite excluding the blocked legacy `tests/test_api.py`: **135 passed**. Combined root+backend collection: **555 tests**, no collection errors. Ruff clean for touched root test/pipeline files, docs checker: 0 broken links / 52 files, `git diff --check` clean. Existing work remains uncommitted and preserved. |
| 2026-11-06 | Real detector dependency and model | Installed `onnxruntime==1.23.2` and `supervision==0.30.7` in project `.venv`; downloaded official Megvii YOLOX-S ONNX release after network approval and verified SHA-256. Replaced the Ultralytics inference path with YOLOX ONNX decoding + Supervision ByteTrack; added 8 detector tests. No global Python packages changed. |
| 2026-11-06 | Real video inference, tracking and counting | Bounded command in `docs/YOLO_REAL_INFERENCE_REPORT.md` exited 0 on CC BY 3.0 Wikimedia traffic footage. 105 sampled frames / 34.9 source seconds; 1,085 tracked observations, 67 unique tracks, nine configured line crossings; inference p50/p95/p99 84.57/93.07/106.22 ms, pipeline 1.84 sampled FPS, peak RSS 447.2 MB. CPU only; no incident candidate on this clip, therefore no model-generated event was sent to API or UI. A prior unstrided attempt hit its timeout and was not counted as successful evidence. |
| 2026-11-06 | Legacy API hang and infrastructure recheck | Bounded `/api/events` TestClient check timed out (exit 124); stack blocked in Starlette TestClient/AnyIO portal. Minimal FastAPI TestClient and minimal httpx AsyncClient + ASGITransport also hung. Environment: FastAPI 0.143.3, Starlette 1.8.0, httpx 0.28.1, httpx2 2.16.0, AnyIO 4.15.1; root cause not isolated. Docker CLI exists but socket remains permission denied; no host permissions changed. |
| 2026-11-06 | Real replay, dashboard and synthetic incident review | Latest bounded E2E passed after adding a separately labeled signed synthetic event: YOLOX replay telemetry persisted to the camera tenant, authenticated Chromium rendered live-updating camera detail, opened the actual alert detail and rejected the synthetic candidate; PostgreSQL status and audit were asserted. Persisted real model telemetry: 65 frames / 342 observations / 26 tracks / 2 crossings, 1.587 FPS, p95 99.41 ms, peak RSS 346.8 MB; UI update 2.387 s. The replay itself generated zero incident candidates. Test now terminates the loopback relay before stopping capture to avoid a shutdown timeout. |
| 2026-11-06 | Synthetic candidate to operator review and archive | `RuleEngine` generated a wrong-way event from deterministic 25 FPS reverse-motion track coordinates, passed through production `AlertGate`, and was labeled `SYNTHETIC TEST`; signed multipart ingest, isolated PostgreSQL evidence/alert persistence, operator detail/reject APIs, archive search, and append-only audit were asserted. Focused backend ingestion file: **9 passed**. Synthetic rule suite: **34 passed**; detector/source/analytics focused suite: **59 passed**. Frontend typecheck and Vitest: **15 passed**. Ruff and `git diff --check` passed; docs checker: 0 broken links / 52 files. Fresh bounded legacy `tests/test_api.py` run exited 124 at 15s. Docker socket remains inaccessible in this sandbox. Real replay emitted no incident; model-generated incident browser review remains unverified. |
| 2026-11-06 | Authenticated annotated-frame preview | Added transient tenant/camera-scoped preview store (latest frame only, 4-second TTL, 2 MiB cap), signed preview upload route, authenticated camera preview read route with no-store headers, and RemoteSink preview publication through a one-slot worker queue. Pipeline now annotates track IDs/classes/confidence, count-line IDs and UTC frame timestamp after configured redaction; browser polls authenticated JPEGs and displays replay/local-live state and frame timestamp. Regression store tests cover tenant isolation, expiry, stale sequence, malformed/oversize JPEG. Full actual YOLOX loopback-replay + real FastAPI + disposable PostgreSQL + Chromium E2E: **1 passed**. Browser confirmed changing frames and screenshot artifact `camera-live-overlay.png` was saved in the test temp output; exact path is printed by the test. E2E logs: `REAL_API_ANNOTATED_PREVIEW_OK`; real model telemetry persisted (test snapshot: 63 frames, 315 detections, 25 tracks, 2 crossings; CPU ~1.54 FPS, inference p50/p95/p99 ~86.8/107.2/117.8 ms, RSS ~344.5 MB). This is a local recorded replay, not physical/external live. |
| 2026-11-06 | Exact owner-supplied Romanian camera URL audit | Added `docs/EXACT_ROMANIAN_CAMERA_URL_AUDIT.md` with a disposition for all 16 exact supplied URLs and stable IDs for text-enumerated children. Inspected LINX, Cluj, WebcamRomania, InfoBuz, OpenCam, ARGOS, DIGI and webcam.ro pages. Iași exact playlist: one bounded HEAD HTTP/2 200; playlist-only GET advertised a 1920×1080/20 FPS H.264/AAC variant (no variant/segment requested, no frame decoded). WebcamRomania terms state streams are third-party-owner content presented by embed; LINX pages state copyright and municipal monitoring-network origin; InfoBuz states feeds load on selection and only permitted embeds are included. External camera rights and actual moving vehicle frames remain unverified, so all stay disabled. OpenCam/ARGOS interactive map links returned inspection-tool cache misses; exhaustive child enumeration is specifically blocked there. The root-level source catalog and blockers were updated. |
| 2026-11-06 | Discovery catalog in operator camera UI | Added a separate read-only candidate panel to `frontend/src/pages/CamerasPage.tsx` backed by `frontend/src/data/romanianCameraCandidates.ts` (22 named camera/timelapse entries plus four parent-directory rows). It distinguishes publisher listing from verified status, shows per-record disable reasons and source-page attribution, and performs no source request, detection or telemetry injection. Frontend typecheck passed; Vitest **15 passed**; production build passed. This provides discoverability only; it does not create active backend camera records or imply every aggregator child has been enumerated. |
| 2026-11-06 | Repeated full real-model overlay acceptance | Re-ran the real YOLOX-S → ByteTrack → loopback MJPEG replay → signed FastAPI ingest → isolated PostgreSQL → authenticated Chromium scenario after the discovery UI change. `tests/test_real_yolo_e2e.py`: **1 passed** (exit 0). Browser observed current annotated JPEG with a changing sequence/timestamp and refreshed real telemetry; actual screenshot copied to `data/vision/evidence/real-yolox-loopback-replay-2026-11-06.png` (SHA-256 `d32e7c04d4326a8626dd1ed9a1e101ffb8bc8b6041d80554dbcfddb933f268c7`). Persisted snapshot: 64 frames, 326 detections, 25 observed track IDs, 2 configured line crossings, 1.566 sampled pipeline FPS, p95 inference 102.62 ms, peak RSS 369.8 MB. Browser run showed updated camera detail and the same clearly labeled `RECORDED REPLAY`; a separate `SYNTHETIC TEST` alert was rejected and DB status/audit asserted. It is not a physical/live Romanian camera or a model-generated real incident. |
| 2026-11-06 | Focused preview/data validation | `backend/tests/test_live_preview.py`: **3 passed** against the isolated PostgreSQL test target. Backend scoped Ruff clean. Documentation checker: **0 broken links / 52 Markdown files**; `git diff --check` clean. |
| 2026-11-06 | Browser assertion and final catalog E2E | First extended browser run correctly completed YOLO inference, persistence, overlay and synthetic review but failed on an incorrect expected catalog count (expected 27, actual 26); this was a test assertion mistake, not an application failure. Corrected the assertion and reran. Final `tests/test_real_yolo_e2e.py`: exit 0; browser printed `REAL_API_CAMERA_DETAIL_OK detections=149 crossings=2`, `REAL_API_ANNOTATED_PREVIEW_OK`, `REAL_API_SYNTHETIC_ALERT_REVIEW_OK`, and `REAL_ROMANIAN_CATALOG_OK entries=26 enabled=0`. Persisted telemetry at the sampled checkpoint: 65 frames, 329 detections, 26 track IDs, 2 crossings, 1.592 FPS, inference p50/p95/p99 87.39/106.24/125.74 ms, RSS 347.1 MB. Latest browser image: `data/vision/evidence/real-yolox-loopback-replay-catalog-e2e-2026-11-06.png`, SHA-256 `6241f4ab2274e5ecac0d12d7e84e41ef824731d17fb579866fa36a756665111f`. |
| 2026-11-06 | Final source-tree rerun | After moving the catalog TS module to a non-ignored source path, `tests/test_real_yolo_e2e.py` was run again and exited 0; 26 candidate rows/zero enabled were verified in browser. Final persisted interval: 66 frames, 336 detections, 26 tracks, 2 crossings, 1.617 FPS, latency p50/p95/p99 86.88/103.95/108.11 ms, RSS 344.7 MB; heartbeat-to-detail refresh 1,256 ms. Screenshot: `data/vision/evidence/real-yolox-loopback-replay-final-e2e-2026-11-06.png` (SHA-256 `7389edd0a2fc9eb0ccd5618a7578044c628628ae09bb4ac469bd651bad886e6d`). |
| 2026-11-06 | Environment limits for camera sprint | No physical `/dev/video*` input was available in prior host inspection. NVIDIA PCI hardware is present but driver is unavailable (`nvidia-smi` cannot communicate); ONNX Runtime has CPU/Azure providers only. No driver/global changes made. A loopback MJPEG relay is continuously decoded as `RECORDED REPLAY`; it does not satisfy a physical-live-camera claim. |

## Prior branch implementation history (as recorded before this mission)

Resume: "Read docs/IMPLEMENTATION_PROGRESS.md and continue with the next step".
Local only: no push/fetch/gh. Never commit on main. design/pro-ui and design/wow untouched.
Backup before start: ~/roadsentinel-before-release-20261105-0401.bundle
Never use `git add -A` at the root without checking `git status` (untracked frontend/dist-* build dirs exist; now git-ignored).

## Environment (real)
- Node: `export PATH=~/miniconda3/envs/rs-node22/bin:$PATH` -> v22.23.4 (default shell is v20.20.2).
- Postgres: conda env `rs-pg` (PostgreSQL **18.6**; CI uses 16 -> deviation), `~/.rs-pg-data`, port 55432. Start if stopped:
  `~/miniconda3/envs/rs-pg/bin/pg_ctl -D ~/.rs-pg-data -o "-p 55432 -c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp" -l ~/.rs-pg-data/log.txt start`
  then `export RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres:devpg@127.0.0.1:55432/postgres`.
- Python venv: `.venv` (py3.12, git-ignored). Playwright chromium in `~/.cache/ms-playwright` (`PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright`).
- Docker: permission denied -> everything Docker-related is UNVERIFIED.

## Phase 1 (P0): DONE, gate green
1. MFA restored (dc2e7dc): backend 100 failing -> all passing; exemption flag `RS_MFA_EXEMPTION_ENABLED` default false, refused in production.
2. Credentials: `demo-accounts` refuses production, random one-time password, MFA stays on; no `parola` literal in code; `scripts/scan_secrets.py` (file:line only), gitleaks allowlist narrowed. Git history still contains the old demo literal (not rewritten; no real secrets found).
3. Evidence integrity: migration 0007 `evidence.has_original`; pipeline evidence is a single copy; unblur/export-original -> 409 `no_original`; redaction values full|heads_only|off|unknown; pipeline: redaction ON by default, `off` needs `RS_ALLOW_UNREDACTED=1` and is reported as `off` (UI: FĂRĂ REDACTARE); redaction code moved to torch-free `roadsentinel/redaction.py`.
4. Deploy: `deploy.yml` manual (`workflow_dispatch`, type DEPLOY) + CI-green gate for the SHA; startup warning when evidence storage is ephemeral/local.
5. CI: jobs backend, secure-pwa, police-ui, pipeline, repo-checks, secrets, stack. `docs/DEPENDENCY_PLAN.md`. Lint errors gone (via design/wow).
6. CSP: Railway gateway now identical to the strict local policy (no unsafe-inline/tiles/webcam host); gateway image non-root + healthcheck (Docker build UNVERIFIED); walks run under that CSP.
7. design/wow merged (72c3283, clean). Legacy `web/` and `roadsentinel/server.py` marked deprecated; AI prompt files moved to docs/archive.

### Phase 1 gate numbers (real)
- backend pytest 331 passed (PostgreSQL 18.6); ruff, black, mypy clean.
- root tests 60 passed, 2 skipped (need ultralytics); ruff clean.
- frontend/: tsc, eslint 0, vitest 9/9, build entry 413.75 kB (133.14 kB gz); secure-pwa: eslint+prettier, typecheck, vitest 9/9, build.
- Playwright: frontend walk (mock+real stubs, axe, console errors, external requests, strict CSP) 0 failures; secure-pwa walk 0 failures (after stub got the new evidence fields).
- npm audit --omit=dev: 0 vulnerabilities (both apps). Secret scan 0 findings (tree). Docs links 0 broken.

## Phase 2 (P1/P2): DONE (code + tests; nothing validated on real footage/cameras/weights)
- rules: sampling parameters per camera (low-fps time-window mode), `rule_capabilities()` from measured fps, rules switched off + reported when unsupported; near_miss, object_on_roadway, probable_crash needs stationary-after-stop; synthetic tests at 0.5/1/2/5/10/25 fps (tests/test_rules_rates.py). docs/RULES.md.
- alerts: AlertGate (dedupe/cooldown/rate limit, counted), event vs alert separation, idempotent ingestion (`event_key`, migration 0008), heartbeat carries fps + rule capability (cameras.status_info) -> Cameras page.
- live: LiveReader (backoff, stall watchdog), BoundedWorker (bounded, retries, drops oldest non-critical), Supervisor (`python -m roadsentinel.live`), heartbeat withheld when nothing was processed; SIGTERM graceful stop. Wired into pipeline.py but pipeline.py itself is NOT executed here (no ultralytics/torch): UNVERIFIED end to end.
- consent: network streams refuse to run without `source_consent` in the camera yaml; Iasi camera is OFF.
- MODEL KIT: roadsentinel/models.py, scripts/model_install|activate|rollback.py, training/eval.py (+ roadsentinel/evaluation.py), training/make_manifest.py, training/check_dataset.py, docs/MODEL_INTEGRATION.md. Tested with fake loader/predictor only.
- calibration: scripts/calibrate_camera.py (fit + validate against known speeds), docs/CALIBRATION.md; speeds "orientativ" until validated. Dataset: LABELING_GUIDE, DATA_CARD_TEMPLATE.

## Phase 3 and 4: see docs/FINAL_STATUS.md
Done: account recovery, retention, patrol workflow, camera edit, response-time stats (+UI), readiness/metrics/ops status, backup/restore (verified locally), latency measurement, authorization matrix and hostile-input tests, demo script, OPERATIONS/LIMITS/SETUP/PRESENTATION docs, README/HANDOFF/API/SECURITY corrections, idle/absolute session limits.
Not done: rules/zones management from the UI (needs config sync), archive saved searches/export, operator QoL (claim/lock, handover, j/k, density), API unification notes. Reasons in FINAL_STATUS.

## Phase 5: DONE. Final numbers are in docs/FINAL_STATUS.md. Resume point if work continues: the "Not done" table there.

## Decisions / ambiguities
- Short-name login (`admin`/`operator`) removed (server + UI); mock mode password is `mock-only-demo`.
- Operators enroll TOTP in the secure PWA (the police UI shows a message); no enrollment screen added to frontend/.
- DB check constraint on evidence.redaction extended (migration 0007) instead of mapping `off` onto another value.

## Known issues / unverified
- Docker/compose/stack, GitHub CI execution, Railway, real models, real cameras: UNVERIFIED.
- CSP enforcement during the walk was applied via the preview server header; not independently probed with a deliberately violating page.
