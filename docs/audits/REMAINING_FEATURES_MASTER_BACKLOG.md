# Remaining features master backlog — after fresh Chromium execution

Updated2026-11-11. Existing native login/MFA is VERIFIED. Selected recorded and local replay browser journeys pass; full product coverage remains partial. Historical backlog preserved at runtime_verification/REMAINING_BACKLOG_BEFORE_BROWSER_20261111.md. Estimates below are rough, not delivery commitments.

Delivered since the prior backlog: full recorded UI upload/model/candidate/promotion/reject/note/bookmark/independent export/download, actual OS restart/archive; browser camera JSON edit/independent approval/Start/revisions/rollback, changing preview and source-health UI; model-derived synthetic-zone signed event/encrypted media/review/export; natural lease expiry; narrowly scoped worker environment and private scratch. Do not schedule these already-passed subflows as missing.


Incremental update (main47e3e85): the visual editor/source-rights/recording/history/report upgrades now have fresh controlled Chromium evidence. [Final incremental verdict](git_incremental_20261111T003730Z/GITHUB_INTEGRATION_FINAL_VERDICT.md). The following prioritized order supersedes treating B01 as wholly missing:

| Order | Work | First small test |
|---|---|---|
| 1 | B02 encrypted crash-retry spool | Fail between staging/commit, restart and prove one alert/no plaintext orphan |
| 2 | B03 quotas/retention/cancel | Reject one over-quota upload before unbounded temporary storage |
| 3 | B11 exact media timing/offsets | Encode irregular PTS and a boundary candidate, assert actual event offset in viewer |
| 4 | B05 independent incident/count labels | Acquire one authorized labelled obstruction interval before evaluating |
| 5 | B06 external rights/network threats | Review one documented provider authorization before source access |
| 6 | B07 HTTPS PWA/patrol | Fresh MFA patrol session on a test-owned trusted TLS origin |
| 7 | B04 multi-camera/soak | Measure one-camera10-minute CPU/RSS/drop baseline, then a second source |
| 8 | B08 browser/a11y and large reports | Check mobile editor keyboard/focus and30-camera print output without lost totals |
| 9 | B09/B10 deployment/key/anchor controls | Restore an owned encrypted backup and verify a test-owned key rotation |
| 10 | B01 legacy adoption/profile UI | Adopt one owned legacy camera without silently enabling it |

## Detailed work items (stable historical IDs)

### B01 Remaining deployment/adoption UI (partial follow-up, not the delivered editor)
Priority **P2**; README IDs A03,A04,A16,A20,A24; rough effort 1–3 days.
Current after incremental main47e3e85: new managed camera creation, source/grant form, visual polygon/line/rules editor, immutable revision, distinct approval, real worker ACK, recording tile playback and exact server-side history PASS on controlled licensed replay. These are delivered and must not be scheduled again as missing. Existing legacy adoption and installation of an allowlisted local worker profile remain explicit engineering/admin actions; generic external self-service onboarding is not approved.
Exact owners: `frontend/src/components/CameraControlPanel.tsx; backend/app/services/camera_workers.py; backend/app/api/camera_control.py`.
First small acceptance: expose a clearly confirmed adoption action for one owned legacy camera, preserving prior media and requiring fresh source/grant/reviewer gates.
Definition of done: safe adoption/profile provisioning with cross-tenant/SSRF/permission negatives, no arbitrary server paths or camera credentials exposed. See [incremental decisions](git_incremental_20261111T003730Z/GITHUB_SEMANTIC_MERGE_DECISIONS.md).

### B02 Encrypted retry staging and crash-safe cleanup
Priority **P0**; README IDs A10,A11,A19,A20,A24,A33; rough effort 2–4 days.
Current: Private per-worker scratch, bounded frame/upload queues and immediate cancellation on revocation pass. Redacted intermediate keyframes/clips are not encrypted/expired locally; interrupted staging/DB-commit matrix is incomplete.
Exact owners: `roadsentinel/pipeline.py; roadsentinel/live.py; roadsentinel/media.py; backend/app/services/evidence.py`.
Implementation: Use an owned encrypted bounded spool with per-event state, explicit byte/age quota, retry identity and cleanup only after authoritative acceptance or owned expiry; preserve canonical evidence and legal holds.
First small acceptance: Inject one failure between encrypted file staging and DB commit, then retry/restart and assert one alert plus no plaintext orphan.
Security/failure constraints: Never unlink pre-existing data or a path outside the owned staging root; retries cannot produce duplicate alerts/audit decisions.
Definition of done: Bounded encrypted staging survives retries, cancels safely and cleans only owned artifacts under crash/restart tests.
Reusable Codex prompt: Implement B02 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B03 Upload quota, cancellation and retention
Priority **P1**; README IDs A10,A20,A23,A33; rough effort 3–5 days.
Current: Actual upload/crop/model/output/heatmap/reload, corrupt-media refusal and network failure now pass. Chunked resume is unsupported; tenant-wide byte/job quotas and comprehensive canceled-job expiry remain incomplete.
Exact owners: `backend/app/api/offline_video.py; backend/app/services/offline_video_storage.py; backend/app/services/offline_analysis.py; frontend/src/pages/VideoAnalysisPage.tsx`.
Implementation: Enforce quotas before persistent writes, implement supported resumable contract only if required, reconcile cancellation/recovery and policy-based original/intermediate retention.
First small acceptance: Reject one quota-exceeding upload before consuming an unbounded temporary file.
Security/failure constraints: Held evidence cannot expire; adversarial chunks, interrupted cleanup and another tenant must be isolated.
Definition of done: Bounded uploads/jobs, truthful progress and tested retention/hold/cancel behavior.
Reusable Codex prompt: Implement B03 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B04 Two-camera capacity and long soak
Priority **P1**; README IDs A03,A24,A27,A33; rough effort 2–5 days.
Current: Single-source genuine moving preview, conflicting worker denial, source outage, natural90s lease expiry, fresh epoch, revision rollback and disable pass. Two-camera sustained load is NOT RUN.
Exact owners: `roadsentinel/live.py; roadsentinel/remote_config.py; backend/app/services/camera_workers.py`.
Implementation: Run two isolated replay sources for a controlled duration on hardware with headroom; measure CPU/RSS/drop/queue/latency and crash only one worker.
First small acceptance: Measure one-camera10-minute baseline before adding a second.
Security/failure constraints: No synthetic FPS, stale healthy preview, unbounded queue or impact on another camera; requested FPS is a ceiling, delivered FPS must remain explicit.
Definition of done: Measured resource limits/backpressure and isolated recovery with no leak or duplicate lease.
Reusable Codex prompt: Implement B04 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B05 Representative incident and counting evaluation
Priority **P1**; README IDs A02,A04,A05,A06,A07,A08,A09,A21,A22; rough effort 1–3 weeks plus licensed labels.
Current: Real moving inference/counts and synthetic-positive incident workflows pass. No representative precision/recall/false-alert rate or metrological speed ground truth exists.
Exact owners: `training; roadsentinel/rules.py; models/registry.json; docs/LIMITS.md`.
Implementation: Freeze licensed annotated day/night/rain/occlusion intervals and model/rule/calibration hashes; evaluate per-scene counts, fragmentation and false alerts/hour, then review activation.
First small acceptance: Acquire one authorized independently labelled obstruction clip and define acceptance before inference.
Security/failure constraints: Synthetic pixels/geometry must stay TEST; no fines, uncalibrated physical speed or invented labels.
Definition of done: Reproducible independent evaluation with explicit uncertainty and field acceptance owners.
Reusable Codex prompt: Implement B05 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B06 Authorized external source and network threat validation
Priority **P1**; README IDs A03,A20,A24,A31; rough effort 2–5 days plus external authorization.
Current: EXTERNALLY BLOCKED: no source-specific automation/process/record/store/export rights. LOCAL RECORDED REPLAY is verified and clearly labelled.
Exact owners: `roadsentinel/consent.py; roadsentinel/sources.py; backend/app/services/camera_control.py; cameras`.
Implementation: Obtain documented provider scope/timeframe and approved endpoint, then test DNS/redirect/allowlist/size/deadline behavior using controlled servers before any permitted external run.
First small acceptance: Review one actual provider authorization without accessing video.
Security/failure constraints: No public-page permission inference, private metadata redirects, token scraping or TLS bypass.
Definition of done: Stable explicitly authorized source plus controlled SSRF negative tests and lawful retention/export scope.
Reusable Codex prompt: Implement B06 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B07 Real HTTPS secure PWA and patrol assignment
Priority **P1**; README IDs A01,A13,A17,A27,A28,A29; rough effort 2–4 days.
Current: PWA9 tests/lint/type/build pass; four roles pass main React Chromium. Installed HTTPS/PWA patrol/push/reconnect is NOT RUN.
Exact owners: `secure-pwa/src; deploy; backend/app/api/patrol.py`.
Implementation: Use test-owned trusted TLS origin and actual MFA; create operator patrol assignment, inspect only permitted patrol state changes, reconnect/logout and cache isolation.
First small acceptance: Authenticate one fresh patrol browser context through the PWA and fetch its assigned task.
Security/failure constraints: No admin controls, evidence secret cache, sensitive generic push payload or cross-tenant task access.
Definition of done: Installable app performs scoped real tasks and secure offline/session transitions.
Reusable Codex prompt: Implement B07 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B08 Browser edge states and accessibility
Priority **P2**; README IDs A12,A14,A17,A18,A25,A34; rough effort 2–4 days.
Current: Fresh login/MFA/logout/new tab/refresh and tested critical dialogs pass; exhaustive expiry, keyboard/mobile/accessibility audit not run.
Exact owners: `frontend/e2e; frontend/src/pages; frontend/src/store/auth.ts`.
Implementation: Add deterministic expired-session, stale revision, slow upload, permission change and keyboard focus journeys; keep errors visible and role navigation truthful.
First small acceptance: Expire an isolated browser session and assert re-authentication without stale protected content.
Security/failure constraints: Never bypass MFA/CSRF or treat forbidden403 as server500; no cross-tenant flash.
Definition of done: Meaningful browser assertions across supported screen sizes and access/error states.
Reusable Codex prompt: Implement B08 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B09 Complete case/retention browser security matrix
Priority **P2**; README IDs A10,A14,A15,A19,A20; rough effort 2–4 days.
Current: Recorded browser note/bookmark/independent approval/download, ZIP hash/tamper verification and OS restart pass; managed-source case export is API verified.
Exact owners: `frontend/src/components/CaseWorkspace.tsx; backend/app/api/investigation.py; backend/app/api/casework.py; backend/app/services/retention.py`.
Implementation: Repeat camera case/export through the browser; exercise legal hold/release/retention/expired link/stale case revisions and complete multi-role boundaries.
First small acceptance: Download one managed-source package via browser after independent approval.
Security/failure constraints: Requester cannot approve own sensitive export; held evidence and revoked grants remain protected.
Definition of done: Browser and DB evidence covers both origins, retention/hold and denied exports without integrity regression.
Reusable Codex prompt: Implement B09 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

### B10 Deployment, key custody and external identity
Priority **P2**; README IDs A18,A19,A20,A26,A27,A30,A32,A35; rough effort 1–3 weeks plus organizational owners.
Current: Narrow lookup repair, restorable native migration backup/rehearsal, real MFA and local security checks pass. No production KMS/HSM, external audit anchor, OIDC/FIDO2, independent legal approval or production scale proof.
Exact owners: `deploy; backend/app/core; docs/ARCHITECTURE_TARGET.md`.
Implementation: Split into approved scoped projects: isolated restore/deploy drill, external key provider, immutable audit custody, organization IdP and processing/DPIA review.
First small acceptance: Run one entirely disposable backup/restore/readiness drill with existing FORCE RLS.
Security/failure constraints: No production/admissibility/compliance claim; dispatch/sign/fines remain human decision records.
Definition of done: Explicit production acceptance with key/identity/backup custody and legal/operational sign-off.
Reusable Codex prompt: Implement B10 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

## Every mandatory category — retained coverage inventory

These35 entries preserve source coverage. Detailed executed gates are F1-01–21 and F2-01–23 in the two current browser reports; full source paragraph inventory remains README_COVERAGE_MATRIX.csv.

| ID | Product area | Current category status | Evidence / next owner |
|---|---|---|---|
| A01 | Product/interfaces | PARTIAL | TEST_EXECUTION_LEDGER.md |
| A02 | Detection/tracking | VERIFIED REAL INPUT PARTIAL | FEATURE_1_REAL_BROWSER_E2E.md |
| A03 | Adapters/rights | VERIFIED REAL INPUT PARTIAL | FEATURE_2_REAL_BROWSER_E2E.md |
| A04 | Geometry/calibration | VERIFIED REAL INPUT PARTIAL | FEATURE_2_REAL_BROWSER_E2E.md |
| A05 | Rule thresholds | VERIFIED REAL INPUT PARTIAL | vertical-release.log; screenshots/recorded-review.png |
| A06 | Critical event types | TESTED SYNTHETIC ONLY | TEST_EXECUTION_LEDGER.md |
| A07 | High event types | TESTED SYNTHETIC ONLY | TEST_EXECUTION_LEDGER.md |
| A08 | Medium event types | TESTED SYNTHETIC ONLY | TEST_EXECUTION_LEDGER.md |
| A09 | Information/offline rules | VERIFIED REAL INPUT PARTIAL | vertical-release.log; screenshots/recorded-review.png |
| A10 | Evidence assembly | VERIFIED REAL INPUT PARTIAL | FEATURE_1_REAL_BROWSER_E2E.md |
| A11 | Signed ingestion | PARTIAL | docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md |
| A12 | Operator queue | VERIFIED REAL INPUT PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A13 | Decisions/patrol | VERIFIED REAL INPUT PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A14 | Archive/saved searches | PARTIAL | docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md |
| A15 | Investigation/export | VERIFIED REAL INPUT PARTIAL | FEATURE_1_REAL_BROWSER_E2E.md |
| A16 | Camera administration | VERIFIED REAL INPUT PARTIAL | FEATURE_2_REAL_BROWSER_E2E.md |
| A17 | Clients/accessibility | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A18 | Authentication/MFA/RLS | VERIFIED REAL END-TO-END | REAL_BROWSER_AUTH_MFA_VERIFICATION.md |
| A19 | Keys/audit | PARTIAL | docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md |
| A20 | Privacy/legal | PARTIAL | TEST_EXECUTION_LEDGER.md |
| A21 | Model governance | PARTIAL | TEST_EXECUTION_LEDGER.md |
| A22 | Real accuracy | EXTERNALLY BLOCKED | TEST_EXECUTION_LEDGER.md |
| A23 | Offline jobs | VERIFIED REAL INPUT PARTIAL | FEATURE_1_REAL_BROWSER_E2E.md |
| A24 | Live worker | VERIFIED REAL INPUT PARTIAL | FEATURE_2_REAL_BROWSER_E2E.md |
| A25 | Contracts | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A26 | Migrations/seed | VERIFIED REAL END-TO-END | docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A27 | Install/readiness | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A28 | Testing/CI | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A29 | Legacy boundaries | PARTIAL | TEST_EXECUTION_LEDGER.md |
| A30 | Optional AI/telemetry | IMPLEMENTED UNVERIFIED | TEST_EXECUTION_LEDGER.md |
| A31 | Romanian source catalog | PARTIAL | TEST_EXECUTION_LEDGER.md |
| A32 | Optional scope | NOT APPLICABLE / OPTIONAL | TEST_EXECUTION_LEDGER.md |
| A33 | Reliability/backpressure | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A34 | Honest presentation | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |
| A35 | Integrated guarantees | PARTIAL | docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md |


### B11 Exact irregular-frame chronology and event-position labels
Priority **P1**; README A10,A19,A23,A24,A34; rough effort2–4 days. Current: default1× and encoded3/10/25FPS/real browser duration regressions pass. Live CFR clips use observed aggregate span; per-gap PTS is not preserved. Late incremental repair removed midpoint/30FPS guesses: new live media includes encoded event offset/FPS, offline promotion includes output FPS, and missing legacy metadata disables precise jump/step controls. Thumbnails show clip-relative time. Exact irregular inter-frame PTS is still not preserved.
Owners: `roadsentinel/pipeline.py::clip_fps/write_clip`, `frontend/src/components/EvidencePlayer.tsx`, `frontend/src/lib/adapters.ts`, `backend/app/services/offline_promotion.py`.
Retain the delivered clip start/event-offset/frame-cadence provenance and add a supported timestamp-aware encoder with per-frame PTS instead of aggregate CFR. Existing encrypted immutable evidence must remain unchanged; any derived replacement requires transformation provenance and its own hash.
First acceptance: an event at0.5s with missing pre-roll displays and seeks0.5s, not the clip midpoint; an irregular0,.1,.8,1s frame sequence preserves its PTS. Test corrupt/missing timestamps, sampled FPS, source boundaries and independently verified export hashes. No legal chronology/metrology certification claim.
