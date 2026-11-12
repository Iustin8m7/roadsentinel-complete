# Destination changelog — reviewed main47e3e85

Source delta:60 files/33 commits. This selected destination manifest covers82 source/config/doc/intentional public assets, including integration-specific hardening and regressions. Generated audit reports/logs/screenshots are additional segregated artifacts. [Exact pre/post SHA, mode and size](destination-changes.json); original preimages are in `backups/`.

| Destination | Action | Purpose / user-visible behavior |
|---|---|---|
| `.gitignore` | MODIFIED | Private integration paths retained alongside upstream ignore additions |
| `API.md` | MODIFIED | Documents authenticated catalogue, managed creation, fenced recording, media ranges and timing JSON. |
| `INTEGRATION_HANDOFF.md` | MODIFIED | Links the incremental handoff while preserving historical reports. |
| `INTEGRATION_MANIFEST.json` | MODIFIED | Adds pinned incremental provenance without replacing original snapshot inventory. |
| `README.md` | MODIFIED | Describes delivered incremental behavior and explicit controlled-test limits. |
| `backend/app/api/camera_control.py` | MODIFIED | Authenticated configuration catalogue |
| `backend/app/api/cameras.py` | MODIFIED | Managed UI onboarding defaults, duplicate409 and scope-gated recording listing. |
| `backend/app/api/contract.py` | MODIFIED | Authenticated encrypted streaming byte ranges and current recording-grant enforcement. |
| `backend/app/api/ingest.py` | MODIFIED | Managed whole-recording lease/revision and record-scope checks. |
| `backend/app/schemas/contract.py` | MODIFIED | Nullable existing camera source-kind serialization; no schema migration. |
| `backend/app/schemas/ops.py` | MODIFIED | Backward-compatible optional managed creation field. |
| `backend/app/services/camera_config.py` | MODIFIED | Authoritative editor bounds/defaults/rule capabilities |
| `backend/app/services/http_range.py` | ADDED | Bounded validated single-range parsing/slicing without plaintext temp files. |
| `backend/app/services/offline_promotion.py` | MODIFIED | Persist actual encoded output FPS alongside existing clip-start provenance. |
| `backend/tests/camera_browser.py` | MODIFIED | Real source/visual/recording tasks on owned ports and protected per-role session state. |
| `backend/tests/test_browser_complete_journey.py` | MODIFIED | Moving real model, public responsive page, measured playback, one-page PDF and case/export/restart assertions. |
| `backend/tests/test_incremental_security.py` | ADDED | Catalogue policy, managed creation/duplicate/cross-tenant and encrypted range regressions. |
| `backend/tests/test_managed_live_runtime.py` | MODIFIED | Actual UI source/grant/visual authoring, scoped recording playback/history, moving worker ACK/recovery and revocation. |
| `docs/audits/README_COVERAGE_MATRIX.csv` | MODIFIED | Preserves all185 original rows and appends8 independently labelled source requirements. |
| `docs/audits/REMAINING_FEATURES_MASTER_BACKLOG.md` | MODIFIED | Removes delivered editor/onboarding from missing-work claims; retains real deployment/field/timing gaps. |
| `frontend/e2e/camera-control-runtime.mjs` | MODIFIED | Repeatable actual Chromium author/reviewer/worker/recording/history/event actions, no fake backend responses. |
| `frontend/e2e/complete-recorded.mjs` | MODIFIED | Repeatable actual Chromium upload/inference/review/export, public/print and evidence timing assertions. |
| `frontend/public/fonts/Overpass-LICENSE.txt` | ADDED | Overpass font assets and OFL licence |
| `frontend/public/fonts/Overpass-Latin.woff2` | ADDED | Overpass font assets and OFL licence |
| `frontend/public/fonts/Overpass-LatinExt.woff2` | ADDED | Overpass font assets and OFL licence |
| `frontend/public/landing/LICENSE.md` | ADDED | Explicit CC BY3.0 attribution and derivative/privacy/accuracy limitations. |
| `frontend/public/landing/alerta-viteza.jpg` | ADDED | Public demonstration media |
| `frontend/public/landing/alerta-viteza.mp4` | ADDED | Public demonstration media |
| `frontend/public/landing/ambuteiaj.jpg` | ADDED | Public demonstration media |
| `frontend/public/landing/distanta.jpg` | ADDED | Public demonstration media |
| `frontend/public/landing/provenance.json` | ADDED | Source/model/output hashes for deliberately public licensed derivatives. |
| `frontend/public/landing/viteza.jpg` | ADDED | Public demonstration media |
| `frontend/src/App.tsx` | MODIFIED | Public landing route alongside secure app route tree |
| `frontend/src/components/ActivityReport.tsx` | ADDED | A4 printed loaded-data report |
| `frontend/src/components/AuditVerification.tsx` | MODIFIED | Romanian audit verification UI |
| `frontend/src/components/CameraAuthorizationForms.tsx` | ADDED | Source-reference and processing-grant forms |
| `frontend/src/components/CameraControlPanel.tsx` | MODIFIED | Editor/source/grant integration and revision lifecycle |
| `frontend/src/components/CasePanels.tsx` | MODIFIED | Romanian case panels and destructive confirmations |
| `frontend/src/components/CaseWorkspace.tsx` | MODIFIED | Casework respects visibility, decisions and approval |
| `frontend/src/components/ClipModal.tsx` | MODIFIED | Removes fabricated capture-clock thumbnails for legacy clips lacking exact metadata. |
| `frontend/src/components/ConfigEditor.tsx` | ADDED | Visual polygon/direction/calibration/rules editor |
| `frontend/src/components/EvidencePlayer.tsx` | MODIFIED | Correct default real-speed playback and clip failure UX |
| `frontend/src/components/IasiMap.tsx` | MODIFIED | Honest map demo/source labels |
| `frontend/src/components/TacticalMap.tsx` | MODIFIED | Remove fabricated patrol layer |
| `frontend/src/hooks/index.ts` | MODIFIED | Reviewed queue ordering and no blocking clip overlay |
| `frontend/src/index.css` | MODIFIED | One-page print isolation CSS |
| `frontend/src/layouts/AppLayout.tsx` | MODIFIED | Dismissible load/mutation failure and nonblocking startup |
| `frontend/src/lib/adapters.ts` | MODIFIED | Honest camera names/statuses and audit roles |
| `frontend/src/lib/alertSummary.test.ts` | ADDED | Focused upstream utility/state regression cases |
| `frontend/src/lib/alertSummary.ts` | ADDED | Romanian plain-language summary builder |
| `frontend/src/lib/api.test.ts` | MODIFIED | Source-kind LIVE/replay and actual nullable API/permission compatibility regressions. |
| `frontend/src/lib/cameraConfig.test.ts` | ADDED | Focused upstream utility/state regression cases |
| `frontend/src/lib/cameraConfig.ts` | ADDED | Client geometry/capability validation and undo/redo history |
| `frontend/src/lib/cameraControl.test.ts` | ADDED | Focused upstream utility/state regression cases |
| `frontend/src/lib/cameraControl.ts` | MODIFIED | Canonical camera editor/client operations |
| `frontend/src/lib/cases.test.ts` | ADDED | Case exports and archive request regressions |
| `frontend/src/lib/cases.ts` | MODIFIED | Plain case/export verification errors and bounded package size |
| `frontend/src/lib/constants.ts` | MODIFIED | Romanian operator terminology |
| `frontend/src/lib/demo.test.ts` | ADDED | Demo review and real-age regressions |
| `frontend/src/lib/demo.ts` | MODIFIED | Rejected-state precedence, actual ages and bounded clip preloading |
| `frontend/src/lib/evidenceTiming.test.ts` | ADDED | Boundary/irregular encoded-offset/missing metadata regressions. |
| `frontend/src/lib/evidenceTiming.ts` | ADDED | Validates actual event offset/cadence rather than guessing midpoint/30FPS. |
| `frontend/src/lib/iasi.test.ts` | ADDED | Focused upstream utility/state regression cases |
| `frontend/src/lib/iasi.ts` | MODIFIED | Demonstration stock camera labels |
| `frontend/src/pages/AlertDetailPage.tsx` | MODIFIED | Plain-language summary and truthful case/evidence labels |
| `frontend/src/pages/ArchivePage.tsx` | MODIFIED | Demo labels and exact camera history filter |
| `frontend/src/pages/AuditPage.tsx` | MODIFIED | Plain audit wording and honest actor roles |
| `frontend/src/pages/CamerasPage.tsx` | MODIFIED | Camera onboarding/editor/recording/placeholder/history actions |
| `frontend/src/pages/DashboardPage.tsx` | MODIFIED | Accurate loaded KPIs and reviewed queue |
| `frontend/src/pages/LandingPage.css` | ADDED | Responsive landing and whole step connectors |
| `frontend/src/pages/LandingPage.tsx` | ADDED | Public explanatory landing/demo interaction |
| `frontend/src/pages/LoginPage.tsx` | MODIFIED | Honest prototype subtitle and removal of dead remember checkbox |
| `frontend/src/pages/StatsPage.tsx` | MODIFIED | Loaded-data denominators and one-page activity report |
| `frontend/src/store/data.test.ts` | ADDED | Focused upstream utility/state regression cases |
| `frontend/src/store/data.ts` | MODIFIED | Server-backed review state and bounded preload coordination |
| `frontend/src/types/index.ts` | MODIFIED | Retains integrated telemetry and adds optional source/cadence/offset fields. |
| `roadsentinel/pipeline.py` | MODIFIED | Fresh detector boxes and highlighted candidate rendering |
| `roadsentinel/sink.py` | MODIFIED | Signs current managed epoch/revision for recording uploads. |
| `scripts/check_docs.py` | MODIFIED | Checks current docs without Git metadata; excludes only frozen source/preimage archive link roots. |
| `scripts/verify-integration.py` | MODIFIED | Unique guarded DB/evidence roots, focused incremental suite and explicit schema/role proof. |
| `tests/test_clip_timebase.py` | ADDED | Actual encoded3/10/25FPS duration and missing/dropped timestamp regressions. |
| `tests/test_pipeline_boxes.py` | ADDED | Fresh-coordinate and outline regressions |

## Compatibility and retained state

No package manifest/lockfile/model registry or migration was replaced. Existing independent source discovery, offline video jobs/heatmap, worker controls, authentication/MFA, casework, approvals, archive/saved searches, encrypted evidence/audit and PWA routes remain. The source Settings wording change was superseded by the existing stronger integrated page and therefore is not a modified destination file.

Original media/weights/credentials/DBs/worktrees were not overwritten. Existing integration DB had no migration, seed or fixture write; native browser authentication creates legitimate sessions/audit. New camera/media/case/fault scenarios used owned disposable databases. Controlled source media is explicitly licensed/synthetic/replay as appropriate.

The port fixes native default playback1×, editor clipping/null-cutoff, bounded media loading/ranges, managed recording authorization, exact camera history and metadata-based event positioning. It does not certify exact irregular PTS, model incident accuracy, external camera consent or production deployment.

Late repair: `roadsentinel/pipeline.py` cancels/counts unaccepted work on managed SIGTERM, retaining accepted evidence. `backend/tests/camera_browser.py` rejects accidental second API lifecycles while workers run; `test_managed_live_runtime.py` sends all post-start revision/rollback/Stop tasks to the same API. Corrected real Chromium/worker rerun passes without weakening exit-code0 assertions.
