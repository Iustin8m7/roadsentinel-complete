# Future feature implementation prompts — after fresh browser verification

These ten tasks are FUTURE work. Browser login and selected recorded/local replay journeys have already passed; preserve them. For every task write only inside roadsentinel-integration or new uniquely identified disposable resources. Never mutate either original tree/database, GitHub, current credentials/MFA, accepted evidence or operator decisions. Keep FORCE RLS, HMAC, CSRF, consent, encryption and human review. Begin with the small test, implement against canonical services, rerun relevant real browser/DB/model/security checks, and distinguish actual moving inference from synthetic stimuli and external field validation.



### B01 Source authorization and complete camera UI
Priority **P0**; README IDs A03,A04,A16,A20,A24; rough effort 2–4 days.
Current: Browser register/JSON revisions/independent approval/Start/ACK/rollback now pass. Adoption, exact source reference and rights grants still require actual admin API setup; no visual polygon editor.
Exact owners: `frontend/src/components/CameraControlPanel.tsx; backend/app/api/camera_control.py; backend/app/services/camera_config.py`.
Implementation: Add form fields for source kind/reference, provider/basis/scope/time/retention/export, using existing canonical routes; add image-coordinate zone/line editor producing the same validated version JSON.
First small acceptance: Browser-create one grant and independently approved revision without fixture API setup.
Security/failure constraints: Self approval, invalid/crossed polygons, cross-tenant and expired grant denied; active worker stops on revocation.
Definition of done: A new camera reaches real ACK and moving preview with all onboarding through authorized UI.
Reusable Codex prompt: Implement B01 in roadsentinel-integration only. Start with the small acceptance above, extend the canonical services/routes, preserve originals/DBs/GitHub, FORCE RLS, MFA, consent, CSRF and encryption, and record actual browser/DB evidence. Do not relabel synthetic/replay as field validation.

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

