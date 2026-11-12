# Future implementation prompts — not implemented

Each task below is future work. Existing integrated login is already verified and must not be reset. Read the current recovery/E2E reports first. Preserve original roots/databases, mandatory MFA, FORCE RLS, audit, encryption, CSRF, consent and localhost binding. Use only integration code and new owned disposable resources. Never push GitHub.

## Task B01 Complete recorded journey in Chromium
Priority P0; requirements A10,A12,A14,A15,A23; rough estimate 2–4 days.
Current: HTTP upload/analysis/first promotion and API export work; browser rejection/note/playback work. Missing one browser-only upload→analysis→first promotion→approval→export→archive journey.
Owners: `frontend/e2e/mission-review.mjs;frontend/src/pages/VideoAnalysisPage.tsx;backend/tests/test_mission_vertical.py`.
Implementation: Extend the current harness with two MFA-authenticated contexts and native file upload; assert persisted result, archive lookup and downloaded package hashes.
First small test: Start with one browser file upload and assert201 plus the owned recording card.
Authorization/failure constraints: Do not access another tenant media; invalid role, duplicate promotion and missing clip must remain denied.
Definition of done: Entire supported recorded workflow passes in Chromium with recorded/synthetic labels and real persistence.
Suggested Codex sub-prompt: Implement B01 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B02 Crash-safe evidence and retained restart
Priority P0; requirements A10,A11,A19,A23,A33; rough estimate 3–6 days.
Current: Orderly persistence and live auth restart are proven. Abrupt ciphertext/DB commit interruption and reopened feature case after process restart remain unverified.
Owners: `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;backend/app/services/offline_video_storage.py`.
Implementation: Add durable pending-object bookkeeping or transactional reconciliation for only newly owned media; inject faults before/after file+DB commit, restart, verify one alert and intact authorized evidence.
First small test: Fault-inject the first promotion ciphertext write in a disposable DB.
Authorization/failure constraints: Never delete pre-existing files; simulate storage outage, rollback and duplicate retry; bound reconciliation pages.
Definition of done: No leaked orphan media, duplicate decisions or inaccessible committed evidence after repeated interruptions.
Suggested Codex sub-prompt: Implement B02 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B03 Positive managed camera incident
Priority P0; requirements A05,A10,A11,A16,A24; rough estimate 3–5 days plus lawful fixture.
Current: Moving model replay has zero eligible incidents. Recorded synthetic positive and signed live control/preview are independently verified.
Owners: `roadsentinel/pipeline.py;roadsentinel/rules.py;backend/tests/test_managed_live_runtime.py`.
Implementation: Obtain an authorized annotated fixture that triggers a supported non-speed rule; run actual managed inference and signed bounded event media through operator case review/export. If using synthetic tracks, keep explicit separate SYNTHETIC TEST proof.
First small test: Verify candidate interval/geometry on a licensed clip before adding managed assertions.
Authorization/failure constraints: Never reduce thresholds solely to force a result, invent calibration or relabel replay as external live.
Definition of done: At least one explainable model-derived managed-source candidate persists with correct revision/source/encrypted media and human decision.
Suggested Codex sub-prompt: Implement B03 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B04 Two-admin browser control editor
Priority P1; requirements A04,A16,A24; rough estimate 2–4 days.
Current: Browser registration+preview and real API draft/validation/independent approval/activation/revision2 pass. End-to-end browser editing/approval/rollback remains.
Owners: `frontend/src/components/CameraControlPanel.tsx;frontend/e2e/camera-control-runtime.mjs;backend/app/services/camera_config.py`.
Implementation: Extend existing component/harness with separate reviewer session, JSON geometry validation, expected revision conflicts and explicit active/applied badges.
First small test: Create one draft via the UI and compare backend version contents.
Authorization/failure constraints: Self approval403, invalid polygon, unapproved activation, stale revision and cross-tenant camera must fail.
Definition of done: Two browser identities configure, approve, activate, observe ACK and rollback with audited history.
Suggested Codex sub-prompt: Implement B04 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B05 Multi-camera soak and worker recovery
Priority P0; requirements A03,A24,A33; rough estimate 3–6 days.
Current: Single-source reconnect/stale expiry/re-enable and duplicate worker refusal pass; two-camera sustained capacity and abrupt worker death not measured.
Owners: `roadsentinel/live.py;roadsentinel/remote_config.py;backend/app/services/camera_control.py`.
Implementation: Run two controlled replay sources with bounded memory/queue counters; crash one worker; observe expiry and reassignment without affecting other camera.
First small test: Measure baseline process RSS/CPU for one and two10-minute sources on hardware with adequate headroom.
Authorization/failure constraints: No unrelated process termination, unbounded retry, stale healthy image or duplicate event flood.
Definition of done: Document measured capacity/backpressure/loss; one-camera failure stays isolated and all resources close.
Suggested Codex sub-prompt: Implement B05 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B06 External-source authorization and SSRF
Priority P1; requirements A03,A20,A24,A31; rough estimate 2–5 days plus external permission.
Current: EXTERNALLY BLOCKED: no source-specific processing/record/store/export authorization. Discovery catalog does not grant rights.
Owners: `roadsentinel/consent.py;roadsentinel/sources.py;backend/app/services/camera_control.py;cameras/romanian-source-registry.json`.
Implementation: Secure written scope and approved endpoint, then add controlled DNS/redirect/allowlist threat tests before permitted live validation.
First small test: Review one owner-issued authorization without retrieving stream media.
Authorization/failure constraints: No private-IP redirect, metadata access, token scraping, TLS bypass or recording beyond scope.
Definition of done: Documented permission plus stable authorized stream and negative SSRF tests; otherwise remains blocked.
Suggested Codex sub-prompt: Implement B06 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B07 Original upload retention and quotas
Priority P1; requirements A10,A20,A23; rough estimate 3–5 days.
Current: Encrypted media and evidence retention paths exist; total tenant quotas, canceled-job/intermediate expiry and long-term hold behavior remain incomplete.
Owners: `backend/app/services/offline_video_storage.py;backend/app/services/retention.py;backend/app/api/offline_video.py`.
Implementation: Add explicit per-tenant byte/job quotas and reversible retention scheduling, with legal holds and bounded cleanup on own fixtures.
First small test: Test quota refusal before persisting a new temporary upload.
Authorization/failure constraints: Held evidence cannot expire; interrupted cleanup cannot leak decrypted material or affect another tenant.
Definition of done: Bounded usage and documented policy; expiry/hold/cancel tests pass without touching existing user media.
Suggested Codex sub-prompt: Implement B07 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B08 Representative evaluation and model governance
Priority P1; requirements A02,A04,A06,A07,A08,A09,A21,A22; rough estimate 1–3 weeks plus labeled data.
Current: EXTERNAL DATA BLOCKER: no representative annotated incident set or accepted target metrics. Timing/counts are not accuracy.
Owners: `models/registry.json;training;roadsentinel/rules.py;docs/LIMITS.md`.
Implementation: Collect licensed labeled day/night/rain/occlusion clips; measure precision/recall/false alerts per hour and count error by scene; review model/ruleset activation.
First small test: Define one annotated obstruction dataset and freeze hashes/expected intervals.
Authorization/failure constraints: No uncalibrated legal speed claim, persistent person identity or silent model fallback.
Definition of done: Reproducible independent metrics with confidence/limitations and approved deployment thresholds.
Suggested Codex sub-prompt: Implement B08 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B09 Secure PWA HTTPS/patrol acceptance
Priority P1; requirements A01,A13,A17,A27,A28,A29; rough estimate 2–5 days.
Current: PWA9 unit tests, lint/type/build pass; actual HTTPS installation/patrol/push/accessibility journey not run this time.
Owners: `secure-pwa/src;deploy;frontend/e2e/pwa-walk.mjs`.
Implementation: Use test-owned trusted local TLS origin, real MFA, role-specific patrol assignment and reconnect/session handling; no public secrets in service worker cache.
First small test: Authenticate a patrol fixture via real PWA QR/TOTP under test TLS.
Authorization/failure constraints: No camera/admin privilege, evidence caching, generic push detail leakage or cross-tenant assignment.
Definition of done: Installable authenticated PWA supports actual scoped tasks and negative/security/browser checks.
Suggested Codex sub-prompt: Implement B09 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.

## Task B10 Deployment, keys, audit custody and legal review
Priority P2; requirements A18,A19,A20,A26,A27,A30,A32,A35; rough estimate 1–3 weeks plus organizational owners.
Current: Local backup restore rehearsed; no production KMS/HSM, external audit custody, OIDC/FIDO2, DPIA/legal approval or production deploy proof.
Owners: `deploy;backend/app/core/crypto.py;backend/app/core/audit_anchor.py;docs/ARCHITECTURE_TARGET.md`.
Implementation: Separate scoped projects: isolated restore/deploy drill, external key provider contract, independent audit anchor, approved IdP and legal processing policies.
First small test: Run deploy/readiness/restore on a new cluster without originals, or define a mock KMS contract test first.
Authorization/failure constraints: No production compliance/admissibility claim; external enforcement remains disabled/operator record only.
Definition of done: Explicitly approved production acceptance with restorable backups, key custody and independent audit/organizational decisions.
Suggested Codex sub-prompt: Implement B10 in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.

Execution instruction: implement the stated first test and missing behavior using existing services; run meaningful positive/negative model/API/browser checks as applicable; record exact input/DB/source provenance, failures and remaining acceptance. Do not mark a code-only change complete.
