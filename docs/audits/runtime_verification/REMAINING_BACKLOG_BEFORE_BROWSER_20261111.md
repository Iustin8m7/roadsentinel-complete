# Remaining features master backlog — after real login recovery

Updated2026-11-10. Login is FIXED and VERIFIED on the existing integration, not a pending task. Password unchanged; MFA enabled. Both selected fixture flows pass in disposable resources; broader feature completeness remains PARTIAL. Historical backlog retained in runtime_verification/REMAINING_BACKLOG_BEFORE_RECOVERY.md. Rough estimates below are not delivery commitments.

## Delivered prerequisites

Narrow NOLOGIN RLS lookup repair,0022 backup/restore-rehearsed live upgrade, partial/idempotent seed, real four-role login/QR enrollment, permissions, recovery-code acknowledgement, empty-dashboard loading, dedicated runtime and safe startup helper. No database reset or password replacement.

## Next ten tasks in order

### B01 Complete recorded journey in Chromium
Priority P0; requirements A10,A12,A14,A15,A23; rough estimate 2–4 days.
Current: HTTP upload/analysis/first promotion and API export work; browser rejection/note/playback work. Missing one browser-only upload→analysis→first promotion→approval→export→archive journey.
Owners: `frontend/e2e/mission-review.mjs;frontend/src/pages/VideoAnalysisPage.tsx;backend/tests/test_mission_vertical.py`.
Implementation: Extend the current harness with two MFA-authenticated contexts and native file upload; assert persisted result, archive lookup and downloaded package hashes.
First small test: Start with one browser file upload and assert201 plus the owned recording card.
Authorization/failure constraints: Do not access another tenant media; invalid role, duplicate promotion and missing clip must remain denied.
Definition of done: Entire supported recorded workflow passes in Chromium with recorded/synthetic labels and real persistence.
Suggested Codex sub-prompt: Implement B01 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B02 Crash-safe evidence and retained restart
Priority P0; requirements A10,A11,A19,A23,A33; rough estimate 3–6 days.
Current: Orderly persistence and live auth restart are proven. Abrupt ciphertext/DB commit interruption and reopened feature case after process restart remain unverified.
Owners: `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;backend/app/services/offline_video_storage.py`.
Implementation: Add durable pending-object bookkeeping or transactional reconciliation for only newly owned media; inject faults before/after file+DB commit, restart, verify one alert and intact authorized evidence.
First small test: Fault-inject the first promotion ciphertext write in a disposable DB.
Authorization/failure constraints: Never delete pre-existing files; simulate storage outage, rollback and duplicate retry; bound reconciliation pages.
Definition of done: No leaked orphan media, duplicate decisions or inaccessible committed evidence after repeated interruptions.
Suggested Codex sub-prompt: Implement B02 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B03 Positive managed camera incident
Priority P0; requirements A05,A10,A11,A16,A24; rough estimate 3–5 days plus lawful fixture.
Current: Moving model replay has zero eligible incidents. Recorded synthetic positive and signed live control/preview are independently verified.
Owners: `roadsentinel/pipeline.py;roadsentinel/rules.py;backend/tests/test_managed_live_runtime.py`.
Implementation: Obtain an authorized annotated fixture that triggers a supported non-speed rule; run actual managed inference and signed bounded event media through operator case review/export. If using synthetic tracks, keep explicit separate SYNTHETIC TEST proof.
First small test: Verify candidate interval/geometry on a licensed clip before adding managed assertions.
Authorization/failure constraints: Never reduce thresholds solely to force a result, invent calibration or relabel replay as external live.
Definition of done: At least one explainable model-derived managed-source candidate persists with correct revision/source/encrypted media and human decision.
Suggested Codex sub-prompt: Implement B03 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B04 Two-admin browser control editor
Priority P1; requirements A04,A16,A24; rough estimate 2–4 days.
Current: Browser registration+preview and real API draft/validation/independent approval/activation/revision2 pass. End-to-end browser editing/approval/rollback remains.
Owners: `frontend/src/components/CameraControlPanel.tsx;frontend/e2e/camera-control-runtime.mjs;backend/app/services/camera_config.py`.
Implementation: Extend existing component/harness with separate reviewer session, JSON geometry validation, expected revision conflicts and explicit active/applied badges.
First small test: Create one draft via the UI and compare backend version contents.
Authorization/failure constraints: Self approval403, invalid polygon, unapproved activation, stale revision and cross-tenant camera must fail.
Definition of done: Two browser identities configure, approve, activate, observe ACK and rollback with audited history.
Suggested Codex sub-prompt: Implement B04 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B05 Multi-camera soak and worker recovery
Priority P0; requirements A03,A24,A33; rough estimate 3–6 days.
Current: Single-source reconnect/stale expiry/re-enable and duplicate worker refusal pass; two-camera sustained capacity and abrupt worker death not measured.
Owners: `roadsentinel/live.py;roadsentinel/remote_config.py;backend/app/services/camera_control.py`.
Implementation: Run two controlled replay sources with bounded memory/queue counters; crash one worker; observe expiry and reassignment without affecting other camera.
First small test: Measure baseline process RSS/CPU for one and two10-minute sources on hardware with adequate headroom.
Authorization/failure constraints: No unrelated process termination, unbounded retry, stale healthy image or duplicate event flood.
Definition of done: Document measured capacity/backpressure/loss; one-camera failure stays isolated and all resources close.
Suggested Codex sub-prompt: Implement B05 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B06 External-source authorization and SSRF
Priority P1; requirements A03,A20,A24,A31; rough estimate 2–5 days plus external permission.
Current: EXTERNALLY BLOCKED: no source-specific processing/record/store/export authorization. Discovery catalog does not grant rights.
Owners: `roadsentinel/consent.py;roadsentinel/sources.py;backend/app/services/camera_control.py;cameras/romanian-source-registry.json`.
Implementation: Secure written scope and approved endpoint, then add controlled DNS/redirect/allowlist threat tests before permitted live validation.
First small test: Review one owner-issued authorization without retrieving stream media.
Authorization/failure constraints: No private-IP redirect, metadata access, token scraping, TLS bypass or recording beyond scope.
Definition of done: Documented permission plus stable authorized stream and negative SSRF tests; otherwise remains blocked.
Suggested Codex sub-prompt: Implement B06 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B07 Original upload retention and quotas
Priority P1; requirements A10,A20,A23; rough estimate 3–5 days.
Current: Encrypted media and evidence retention paths exist; total tenant quotas, canceled-job/intermediate expiry and long-term hold behavior remain incomplete.
Owners: `backend/app/services/offline_video_storage.py;backend/app/services/retention.py;backend/app/api/offline_video.py`.
Implementation: Add explicit per-tenant byte/job quotas and reversible retention scheduling, with legal holds and bounded cleanup on own fixtures.
First small test: Test quota refusal before persisting a new temporary upload.
Authorization/failure constraints: Held evidence cannot expire; interrupted cleanup cannot leak decrypted material or affect another tenant.
Definition of done: Bounded usage and documented policy; expiry/hold/cancel tests pass without touching existing user media.
Suggested Codex sub-prompt: Implement B07 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B08 Representative evaluation and model governance
Priority P1; requirements A02,A04,A06,A07,A08,A09,A21,A22; rough estimate 1–3 weeks plus labeled data.
Current: EXTERNAL DATA BLOCKER: no representative annotated incident set or accepted target metrics. Timing/counts are not accuracy.
Owners: `models/registry.json;training;roadsentinel/rules.py;docs/LIMITS.md`.
Implementation: Collect licensed labeled day/night/rain/occlusion clips; measure precision/recall/false alerts per hour and count error by scene; review model/ruleset activation.
First small test: Define one annotated obstruction dataset and freeze hashes/expected intervals.
Authorization/failure constraints: No uncalibrated legal speed claim, persistent person identity or silent model fallback.
Definition of done: Reproducible independent metrics with confidence/limitations and approved deployment thresholds.
Suggested Codex sub-prompt: Implement B08 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B09 Secure PWA HTTPS/patrol acceptance
Priority P1; requirements A01,A13,A17,A27,A28,A29; rough estimate 2–5 days.
Current: PWA9 unit tests, lint/type/build pass; actual HTTPS installation/patrol/push/accessibility journey not run this time.
Owners: `secure-pwa/src;deploy;frontend/e2e/pwa-walk.mjs`.
Implementation: Use test-owned trusted local TLS origin, real MFA, role-specific patrol assignment and reconnect/session handling; no public secrets in service worker cache.
First small test: Authenticate a patrol fixture via real PWA QR/TOTP under test TLS.
Authorization/failure constraints: No camera/admin privilege, evidence caching, generic push detail leakage or cross-tenant assignment.
Definition of done: Installable authenticated PWA supports actual scoped tasks and negative/security/browser checks.
Suggested Codex sub-prompt: Implement B09 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

### B10 Deployment, keys, audit custody and legal review
Priority P2; requirements A18,A19,A20,A26,A27,A30,A32,A35; rough estimate 1–3 weeks plus organizational owners.
Current: Local backup restore rehearsed; no production KMS/HSM, external audit custody, OIDC/FIDO2, DPIA/legal approval or production deploy proof.
Owners: `deploy;backend/app/core/crypto.py;backend/app/core/audit_anchor.py;docs/ARCHITECTURE_TARGET.md`.
Implementation: Separate scoped projects: isolated restore/deploy drill, external key provider contract, independent audit anchor, approved IdP and legal processing policies.
First small test: Run deploy/readiness/restore on a new cluster without originals, or define a mock KMS contract test first.
Authorization/failure constraints: No production compliance/admissibility claim; external enforcement remains disabled/operator record only.
Definition of done: Explicitly approved production acceptance with restorable backups, key custody and independent audit/organizational decisions.
Suggested Codex sub-prompt: Implement B10 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

## Every mandatory category — current gap/next acceptance

### A01 Product/interfaces
Status **PARTIAL**; priority P1. Owners/tests: `frontend/src/App.tsx;secure-pwa/src;backend/app/main.py`; `backend/tests/test_contract_api.py`.
Next: Secure backend authoritative; legacy architecture table contradicts current architecture. PWA browser not exercised.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A02 Detection/tracking
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `roadsentinel/detector.py;roadsentinel/pipeline.py;models/registry.json`; `backend/tests/test_mission_vertical.py`.
Next: Actual inference on licensed-derived synthetic frozen fixture; no incident accuracy measurement.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A03 Adapters/rights
Status **TESTED SYNTHETIC ONLY**; priority P0. Owners/tests: `roadsentinel/sources.py;roadsentinel/consent.py;roadsentinel/replay.py`; `tests/test_sources.py;tests/test_consent.py`.
Next: Local adapters tested. External rights not established; no remote media fetched.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A04 Geometry/calibration
Status **TESTED SYNTHETIC ONLY**; priority P1. Owners/tests: `roadsentinel/geometry.py;backend/app/services/camera_config.py`; `tests/test_rules_rates.py`.
Next: Synthetic geometry is not a calibrated real road. No speed certification.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A05 Rule thresholds
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `roadsentinel/rules.py;backend/app/services/offline_analysis.py`; `tests/test_rules.py;tests/test_mission_vertical.py`.
Next: Frozen-frame model tracks produce nine candidates; this is not street incident validation.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A06 Critical event types
Status **TESTED SYNTHETIC ONLY**; priority P1. Owners/tests: `roadsentinel/rules.py;backend/app/core/catalog.py`; `tests/test_rules.py`.
Next: Wrong way/pedestrian/crash/object production precision and recall remain unverified.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A07 High event types
Status **TESTED SYNTHETIC ONLY**; priority P1. Owners/tests: `roadsentinel/rules.py`; `tests/test_rules.py`.
Next: Stopped/offline candidate bridge implemented. Physical speed and near miss remain unvalidated.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A08 Medium event types
Status **TESTED SYNTHETIC ONLY**; priority P2. Owners/tests: `roadsentinel/rules.py;roadsentinel/rates.py`; `tests/test_rules_rates.py`.
Next: Sampling constraints matter; no operational validation.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A09 Information/offline rules
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/services/offline_analysis.py`; `backend/tests/test_mission_vertical.py`.
Next: Line counts stay analytics; only obstruction/queue eligible for explicit recorded review.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A10 Evidence assembly
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;roadsentinel/pipeline.py`; `backend/tests/test_mission_vertical.py;backend/tests/test_evidence_integrity.py`.
Next: HTTP media + encryption verified for recorded fixture; crash orphan cleanup remains open.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A11 Signed ingestion
Status **PARTIAL**; priority P0. Owners/tests: `roadsentinel/sink.py;backend/app/api/ingest.py;backend/app/services/ingest_auth.py`; `backend/tests/test_ingest_auth.py;backend/tests/test_ingest_idempotency.py`.
Next: Use final execution ledger for test-level outcomes; managed fencing newly added.
Limits: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A12 Operator queue
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `frontend/src/store/data.ts;backend/app/api/contract.py`; `backend/tests/test_contract_api.py`.
Next: API exercised; new UI source labels compile. Full candidate promotion browser journey not verified.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A13 Decisions/patrol
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/api/contract.py;backend/app/api/patrol.py`; `backend/tests/test_mission_vertical.py;backend/tests/test_patrol_stats.py`.
Next: Actual HTTP reject tested for recorded fixture. Signs/enforcement remain action labels.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A14 Archive/saved searches
Status **PARTIAL**; priority P1. Owners/tests: `backend/app/services/search.py;backend/app/api/contract.py`; `backend/tests/test_pagination.py`.
Next: Tenant-filtered parser and keyset paging exist; browser retrieval of new candidate not yet demonstrated.
Limits: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A15 Investigation/export
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py`; `backend/tests/test_evidence_integrity.py`.
Next: Basic case-note/license-grant/four-eyes export/hash verification passed; next bookmark, legal hold, revoked grant, tampering and browser export.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A16 Camera administration
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/api/camera_control.py;backend/app/services/camera_config.py;frontend/src/components/CameraControlPanel.tsx`; `backend/tests/test_managed_live_runtime.py;frontend/e2e/camera-control-runtime.mjs`.
Next: Config creation/approval/activation passed via authenticated APIs, registration and preview via browser. Next automate the entire configuration editor and approval in two independent browser contexts.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A17 Clients/accessibility
Status **PARTIAL**; priority P2. Owners/tests: `frontend/src;secure-pwa/src`; `frontend/src/store/auth.test.ts`.
Next: Frontend build and 15 tests pass. PWA browser and accessibility acceptance remain unverified.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A18 Authentication/MFA/RLS
Status **VERIFIED REAL END-TO-END**; priority P0. Owners/tests: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`; `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Next: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limits: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### A19 Keys/audit
Status **PARTIAL**; priority P1. Owners/tests: `backend/app/core/crypto.py;backend/app/core/audit.py;backend/app/core/audit_anchor.py`; `backend/tests/test_crypto.py;backend/tests/test_audit.py`.
Next: AES-GCM and hash chain exist. Local checkpoint is not independent external custody.
Limits: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A20 Privacy/legal
Status **PARTIAL**; priority P0. Owners/tests: `roadsentinel/redaction.py;roadsentinel/consent.py;backend/app/services/retention.py`; `tests/test_privacy_defaults.py;backend/tests/test_retention.py`.
Next: Heuristic redaction is not anonymization. No legal/DPIA sign-off or enforcement integration.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A21 Model governance
Status **PARTIAL**; priority P1. Owners/tests: `roadsentinel/models.py;models/registry.json;training`; `tests/test_models.py`.
Next: Stock model hash known; external configurable model path added. No representative evaluated activation.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A22 Real accuracy
Status **EXTERNALLY BLOCKED**; priority P1. Owners/tests: `docs/LIMITS.md;models/reports`; `tests/test_evaluation.py`.
Next: No labeled representative data/approved target metrics. Counts not ground truth.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A23 Offline jobs
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `backend/app/api/offline_video.py;backend/app/services/offline_analysis.py;backend/app/models/offline_video.py`; `backend/tests/test_mission_vertical.py;backend/tests/test_offline_video_authz.py`.
Next: Upload/crop/job/candidates/media/review tested over HTTP. Restart/browser/retention matrix incomplete.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A24 Live worker
Status **VERIFIED REAL INPUT PARTIAL**; priority P0. Owners/tests: `roadsentinel/remote_config.py;roadsentinel/live.py;roadsentinel/pipeline.py;backend/app/api/camera_worker.py`; `backend/tests/test_managed_live_runtime.py;tests/test_remote_config.py`.
Next: Real managed replay, duplicate lease refusal, revision 1 to 2, outage recovery, disable/re-enable passed. Next provide lawful positive live event and multi-camera soak.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A25 Contracts
Status **PARTIAL**; priority P0. Owners/tests: `backend/app/schemas/contract.py;frontend/src/lib/adapters.ts;API.md`; `backend/tests/test_contract_api.py`.
Next: Legacy/secure contract coexist. New origin stored in details; labels added conservatively, unknown source disclosed.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A26 Migrations/seed
Status **VERIFIED REAL END-TO-END**; priority P0. Owners/tests: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`; `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Next: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limits: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### A27 Install/readiness
Status **PARTIAL**; priority P1. Owners/tests: `deploy/docker-compose.yml;frontend/vite.config.ts;backend/app/api/health.py`; `backend/tests/test_ops_and_authz.py`.
Next: Current proxy correct. Compose not executed. Readiness does not mean a camera is online.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A28 Testing/CI
Status **PARTIAL**; priority P1. Owners/tests: `backend/tests;tests;frontend/e2e;.github/workflows/ci.yml`; `TEST_EXECUTION_LEDGER.md`.
Next: Local execution evidence only; no GitHub CI execution or push.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A29 Legacy boundaries
Status **PARTIAL**; priority P1. Owners/tests: `roadsentinel/server.py;web;README.md`; `tests/test_api.py`.
Next: Legacy batch destructive semantics remain isolated; not used for mission E2E.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A30 Optional AI/telemetry
Status **IMPLEMENTED UNVERIFIED**; priority P2. Owners/tests: `roadsentinel/vlm.py;roadsentinel/tracking.py`; `tests/test_privacy_defaults.py`.
Next: External VLM and W&B not enabled in mission; no external data transmission test.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A31 Romanian source catalog
Status **PARTIAL**; priority P1. Owners/tests: `cameras/romanian-source-registry.json;backend/app/services/camera_discovery.py`; `backend/tests/test_camera_discovery.py`.
Next: Catalog restored from original source. Candidates remain ingestion-disabled; no rights or availability claim.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A32 Optional scope
Status **NOT APPLICABLE / OPTIONAL**; priority P3. Owners/tests: `docs/LIMITS.md;README.md`; `not applicable`.
Next: Fog/ice/plate/facial/enforcement/SSO not added. No automatic sanctions.
Limits: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A33 Reliability/backpressure
Status **PARTIAL**; priority P0. Owners/tests: `roadsentinel/live.py;backend/app/services/camera_control.py`; `tests/test_live.py;backend/tests/test_managed_heartbeat.py`.
Next: Critical queue overflow bounded; stale sequences no longer extend lease. Long soak/multi-camera absent.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A34 Honest presentation
Status **PARTIAL**; priority P1. Owners/tests: `frontend/src/lib/adapters.ts;frontend/src/pages/VideoAnalysisPage.tsx`; `frontend/src/store/auth.test.ts`.
Next: RECORDED/LOCAL REPLAY/SYNTHETIC source prefixes. No external live or accuracy badge inferred.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A35 Integrated guarantees
Status **PARTIAL**; priority P0. Owners/tests: `backend/app/models/camera_control.py;backend/app/models/casework.py;backend/app/models/investigation.py`; `backend/tests/test_isolation.py`.
Next: Tenant table inventory now derived after all models imported. Imported case/control paths need more end-to-end coverage.
Limits: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.
