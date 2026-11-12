# Remaining features master backlog

Updated 2026-11-10T00:29:57.896553+00:00. Estimates below are rough engineering estimates, not delivery commitments. Both selected vertical slices retain unverified gates.

## B01 Finish existing integration authentication
- Priority P0; requirements A18,A26; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `backend/app/bootstrap.py; scripts/repair-integration-dev-auth.sh`.
- First testable action: Take a restorable integration-only backup, verify current DB/process identity, restore lookup-owner role via guarded script, inspect hashes and complete real MFA login. Do not seed blindly.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B02 Recorded promotion browser and authorization matrix
- Priority P0; requirements A10,A12,A18,A23; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `frontend/src/components/OfflinePromotion.tsx;backend/tests/test_mission_vertical.py`.
- First testable action: Run two tenants and operator/admin/patrol/auditor over real HTTP/Chromium; candidate submission, duplicate clicks, media, decision, archive and restart must retain the same event.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B03 Managed control configuration lifecycle
- Priority P0; requirements A16,A24,A33; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `roadsentinel/remote_config.py;backend/app/services/camera_control.py`.
- First testable action: Exercise actual two-admin config creation/approval/activation through API/UI, then require ACK and event revision matching across an approved change and rollback.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B04 Camera outage recovery and multi-camera resources
- Priority P0; requirements A03,A24,A33; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `roadsentinel/live.py;roadsentinel/pipeline.py;backend/tests/test_managed_live_runtime.py`.
- First testable action: Single-source interruption/reconnecting/expired-preview/recovery now passes. Next measure bounded threads, queues, memory and duplicate evidence across two cameras and a longer outage.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B05 Evidence transaction crash recovery
- Priority P0; requirements A10,A11,A19; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `backend/app/services/evidence.py;backend/app/services/offline_promotion.py`.
- First testable action: Fault-inject between ciphertext writes and DB commit; register only test-owned pending objects, remove on rollback or reconcile durable journal; never delete pre-existing evidence.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B06 Promoted case export and approvals
- Priority P0; requirements A15,A19; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py`.
- First testable action: Basic promoted-candidate note/license-grant/independent-approval/package/hash path now passes. Next add bookmarks, legal hold, grant revocation, tamper negatives and browser export.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B07 Offline temporal rules and timebase validation
- Priority P1; requirements A04,A05,A09,A23; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `backend/app/services/offline_analysis.py;roadsentinel/rules.py`.
- First testable action: Add moving/occluded/shake/outside-zone negatives and stable event intervals under PTS shifts/sample changes; preserve analytics-only crossings and do not relax dwell for demo.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B08 Retention and upload quotas
- Priority P1; requirements A10,A20,A23; rough complexity 2–5 days.
- Current state: PARTIAL / UNVERIFIED. Owners: `backend/app/services/offline_video_storage.py;backend/app/services/retention.py`.
- First testable action: Define bounded original/intermediate/job retention and per-tenant quotas with legal hold and interrupted-job recovery; run cleanup solely on fresh fixtures.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B09 Representative model evaluation and governance
- Priority P1; requirements A02,A21,A22; rough complexity 1–3 weeks plus external dependencies.
- Current state: PARTIAL / UNVERIFIED. Owners: `models/registry.json;training;docs/LIMITS.md`.
- First testable action: Obtain licensed labeled multi-condition footage and approved metrics; measure precision/recall/false alerts/hour/count errors; activate only reviewed hashes. External approval needed.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## B10 Secure PWA and deployment/restore acceptance
- Priority P1; requirements A17,A27,A28,A29; rough complexity 1–3 weeks plus external dependencies.
- Current state: PARTIAL / UNVERIFIED. Owners: `secure-pwa;deploy;docs/OPERATIONS.md`.
- First testable action: Locked install/build and real HTTPS MFA/patrol/accessibility/push browser checks, then backup/restore drill on independent resources. No original DB mutation.
- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.
- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.
- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.

## Remaining category-specific acceptance

- A01 Product/interfaces (P1): Secure backend authoritative; legacy architecture table contradicts current architecture. PWA browser not exercised. Owners `frontend/src/App.tsx;secure-pwa/src;backend/app/main.py`; next tests `backend/tests/test_contract_api.py`.
- A02 Detection/tracking (P0): Actual inference on licensed-derived synthetic frozen fixture; no incident accuracy measurement. Owners `roadsentinel/detector.py;roadsentinel/pipeline.py;models/registry.json`; next tests `backend/tests/test_mission_vertical.py`.
- A03 Adapters/rights (P0): Local adapters tested. External rights not established; no remote media fetched. Owners `roadsentinel/sources.py;roadsentinel/consent.py;roadsentinel/replay.py`; next tests `tests/test_sources.py;tests/test_consent.py`.
- A04 Geometry/calibration (P1): Synthetic geometry is not a calibrated real road. No speed certification. Owners `roadsentinel/geometry.py;backend/app/services/camera_config.py`; next tests `tests/test_rules_rates.py`.
- A05 Rule thresholds (P0): Frozen-frame model tracks produce nine candidates; this is not street incident validation. Owners `roadsentinel/rules.py;backend/app/services/offline_analysis.py`; next tests `tests/test_rules.py;tests/test_mission_vertical.py`.
- A06 Critical event types (P1): Wrong way/pedestrian/crash/object production precision and recall remain unverified. Owners `roadsentinel/rules.py;backend/app/core/catalog.py`; next tests `tests/test_rules.py`.
- A07 High event types (P1): Stopped/offline candidate bridge implemented. Physical speed and near miss remain unvalidated. Owners `roadsentinel/rules.py`; next tests `tests/test_rules.py`.
- A08 Medium event types (P2): Sampling constraints matter; no operational validation. Owners `roadsentinel/rules.py;roadsentinel/rates.py`; next tests `tests/test_rules_rates.py`.
- A09 Information/offline rules (P0): Line counts stay analytics; only obstruction/queue eligible for explicit recorded review. Owners `backend/app/services/offline_analysis.py`; next tests `backend/tests/test_mission_vertical.py`.
- A10 Evidence assembly (P0): HTTP media + encryption verified for recorded fixture; crash orphan cleanup remains open. Owners `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;roadsentinel/pipeline.py`; next tests `backend/tests/test_mission_vertical.py;backend/tests/test_evidence_integrity.py`.
- A11 Signed ingestion (P0): Use final execution ledger for test-level outcomes; managed fencing newly added. Owners `roadsentinel/sink.py;backend/app/api/ingest.py;backend/app/services/ingest_auth.py`; next tests `backend/tests/test_ingest_auth.py;backend/tests/test_ingest_idempotency.py`.
- A12 Operator queue (P0): API exercised; new UI source labels compile. Full candidate promotion browser journey not verified. Owners `frontend/src/store/data.ts;backend/app/api/contract.py`; next tests `backend/tests/test_contract_api.py`.
- A13 Decisions/patrol (P0): Actual HTTP reject tested for recorded fixture. Signs/enforcement remain action labels. Owners `backend/app/api/contract.py;backend/app/api/patrol.py`; next tests `backend/tests/test_mission_vertical.py;backend/tests/test_patrol_stats.py`.
- A14 Archive/saved searches (P1): Tenant-filtered parser and keyset paging exist; browser retrieval of new candidate not yet demonstrated. Owners `backend/app/services/search.py;backend/app/api/contract.py`; next tests `backend/tests/test_pagination.py`.
- A15 Investigation/export (P0): Imported API/UI exist. Basic promoted-incident export and manifest verification passed; broader revocation/hold/browser cases remain. Owners `backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py`; next tests `backend/tests/test_evidence_integrity.py`.
- A16 Camera administration (P0): Managed runtime fixture tests do not prove two-admin UI approval workflow. Owners `backend/app/api/camera_control.py;backend/app/services/camera_config.py;frontend/src/components/CameraControlPanel.tsx`; next tests `backend/tests/test_managed_live_runtime.py`.
- A17 Clients/accessibility (P2): Frontend build and 15 tests pass. PWA browser and accessibility acceptance remain unverified. Owners `frontend/src;secure-pwa/src`; next tests `frontend/src/store/auth.test.ts`.
- A18 Authentication/MFA/RLS (P0): Disposable DB authenticates with mandatory MFA. Existing integration owner BYPASSRLS=false remains blocker; existing DB untouched. Owners `backend/app/services/auth.py;backend/app/db.py;backend/app/bootstrap.py;backend/app/services/seed.py`; next tests `backend/tests/test_auth.py;backend/tests/test_seed.py;backend/tests/test_isolation.py`.
- A19 Keys/audit (P1): AES-GCM and hash chain exist. Local checkpoint is not independent external custody. Owners `backend/app/core/crypto.py;backend/app/core/audit.py;backend/app/core/audit_anchor.py`; next tests `backend/tests/test_crypto.py;backend/tests/test_audit.py`.
- A20 Privacy/legal (P0): Heuristic redaction is not anonymization. No legal/DPIA sign-off or enforcement integration. Owners `roadsentinel/redaction.py;roadsentinel/consent.py;backend/app/services/retention.py`; next tests `tests/test_privacy_defaults.py;backend/tests/test_retention.py`.
- A21 Model governance (P1): Stock model hash known; external configurable model path added. No representative evaluated activation. Owners `roadsentinel/models.py;models/registry.json;training`; next tests `tests/test_models.py`.
- A22 Real accuracy (P1): No labeled representative data/approved target metrics. Counts not ground truth. Owners `docs/LIMITS.md;models/reports`; next tests `tests/test_evaluation.py`.
- A23 Offline jobs (P0): Upload/crop/job/candidates/media/review tested over HTTP. Restart/browser/retention matrix incomplete. Owners `backend/app/api/offline_video.py;backend/app/services/offline_analysis.py;backend/app/models/offline_video.py`; next tests `backend/tests/test_mission_vertical.py;backend/tests/test_offline_video_authz.py`.
- A24 Live worker (P0): Actual latest outcomes in managed-live and backend-final logs. Do not treat test-owned approval rows as admin acceptance. Owners `roadsentinel/remote_config.py;roadsentinel/live.py;roadsentinel/pipeline.py;backend/app/api/camera_worker.py`; next tests `backend/tests/test_managed_live_runtime.py;tests/test_remote_config.py`.
- A25 Contracts (P0): Legacy/secure contract coexist. New origin stored in details; labels added conservatively, unknown source disclosed. Owners `backend/app/schemas/contract.py;frontend/src/lib/adapters.ts;API.md`; next tests `backend/tests/test_contract_api.py`.
- A26 Migrations/seed (P0): Fresh cluster tested through 0021. Existing integration not migrated or backed up during mission. Owners `backend/alembic;backend/app/services/seed.py`; next tests `backend/tests/test_isolation.py;backend/tests/test_seed.py`.
- A27 Install/readiness (P1): Current proxy correct. Compose not executed. Readiness does not mean a camera is online. Owners `deploy/docker-compose.yml;frontend/vite.config.ts;backend/app/api/health.py`; next tests `backend/tests/test_ops_and_authz.py`.
- A28 Testing/CI (P1): Local execution evidence only; no GitHub CI execution or push. Owners `backend/tests;tests;frontend/e2e;.github/workflows/ci.yml`; next tests `TEST_EXECUTION_LEDGER.md`.
- A29 Legacy boundaries (P1): Legacy batch destructive semantics remain isolated; not used for mission E2E. Owners `roadsentinel/server.py;web;README.md`; next tests `tests/test_api.py`.
- A30 Optional AI/telemetry (P2): External VLM and W&B not enabled in mission; no external data transmission test. Owners `roadsentinel/vlm.py;roadsentinel/tracking.py`; next tests `tests/test_privacy_defaults.py`.
- A31 Romanian source catalog (P1): Catalog restored from original source. Candidates remain ingestion-disabled; no rights or availability claim. Owners `cameras/romanian-source-registry.json;backend/app/services/camera_discovery.py`; next tests `backend/tests/test_camera_discovery.py`.
- A32 Optional scope (P3): Fog/ice/plate/facial/enforcement/SSO not added. No automatic sanctions. Owners `docs/LIMITS.md;README.md`; next tests `not applicable`.
- A33 Reliability/backpressure (P0): Critical queue overflow bounded; stale sequences no longer extend lease. Long soak/multi-camera absent. Owners `roadsentinel/live.py;backend/app/services/camera_control.py`; next tests `tests/test_live.py;backend/tests/test_managed_heartbeat.py`.
- A34 Honest presentation (P1): RECORDED/LOCAL REPLAY/SYNTHETIC source prefixes. No external live or accuracy badge inferred. Owners `frontend/src/lib/adapters.ts;frontend/src/pages/VideoAnalysisPage.tsx`; next tests `frontend/src/store/auth.test.ts`.
- A35 Integrated guarantees (P0): Tenant table inventory now derived after all models imported. Imported case/control paths need more end-to-end coverage. Owners `backend/app/models/camera_control.py;backend/app/models/casework.py;backend/app/models/investigation.py`; next tests `backend/tests/test_isolation.py`.

## External and optional work
Production KMS/HSM, independent audit custody, approved DPIA/legal basis/retention, SSO, approved push devices, real external camera rights and representative data remain externally blocked. Fog/ice, plate/facial recognition and real enforcement are not scope defaults. No automatic enforcement should be inferred from action labels.