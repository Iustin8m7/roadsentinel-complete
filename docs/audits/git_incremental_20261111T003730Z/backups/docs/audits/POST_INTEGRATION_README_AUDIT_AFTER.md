> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Post-integration README audit — after runtime recovery

Updated 2026-11-10T13:10:51.595733+00:00. The historical BEFORE inventory remains unchanged. All185 IDs remain in the coverage matrix:150 source paragraph/table criteria and35 category checks. This is source coverage plus scoped executed acceptance, not185 passed feature tests. Full transitive specification acceptance, representative accuracy and production/legal readiness remain unproved.

## Current verdict

- Existing 5175/8003/55446 login: PASS; four Unit A roles enrolled, normal operator MFA challenge, protected requests, reload/restart/logout verified.
- Feature1: selected real-model synthetic-recorded fixture journey passes, including actual UI rejection/case note and independently approved hash-verified HTTP export. Broader feature PARTIAL.
- Feature2: actual UI registration, two-admin API approval, real worker lease/ACK/changing browser preview, revision2, duplicate refusal, outage recovery and disable/re-enable pass. Broader feature PARTIAL; zero eligible live events and no external live rights.
- Fresh backend422 passed/2 opt-in skipped; pipeline213; React19; PWA9; both builds/lints pass. Reproducible independent fresh-cluster auth+flows44 passed.
- Exact current reports: INTEGRATED_LOGIN_RECOVERY_REPORT.md, ACTUAL_BROWSER_LOGIN_EVIDENCE.md, FULL_INTEGRATION_E2E_VALIDATION.md, TEST_EXECUTION_LEDGER.md.

Status totals: {"EXTERNALLY BLOCKED": 1, "IMPLEMENTED UNVERIFIED": 137, "NOT APPLICABLE / OPTIONAL": 1, "PARTIAL": 27, "TESTED SYNTHETIC ONLY": 5, "VERIFIED REAL END-TO-END": 4, "VERIFIED REAL INPUT PARTIAL": 10}.

The earlier after-audit is preserved at runtime_verification/README_AUDIT_AFTER_BEFORE_LOGIN_RECOVERY.md. Historical blocked-auth statements in older documents are superseded by the current reports.

### REQ-0001 — RoadSentinel: AI traffic-camera monitoring that sends evidence-backed alerts to police operators and patrols. Hackathon project / 
Source: `docs/audits/README_BEFORE_SOURCE.txt:3-3`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0002 — What it does: 1. **Camera processing.** A YOLO detector with tracking can process configured camera sources and compute speed, har
Source: `docs/audits/README_BEFORE_SOURCE.txt:7-10`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0003 — Alert types: | Priority | Event | |---|---| | Critical | Wrong-way driving, pedestrian on road, probable crash, object on roadway 
Source: `docs/audits/README_BEFORE_SOURCE.txt:14-19`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0004 — Alert types: Definitions and sampling-rate limits: docs/RULES.md. All rules are tested on synthetic tracks only. 
Source: `docs/audits/README_BEFORE_SOURCE.txt:21-21`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0005 — Alert flow: - The system detects the event and attaches the clip, key frames, location, time, and the rule that fired. - The opera
Source: `docs/audits/README_BEFORE_SOURCE.txt:25-28`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0006 — Archive search: Investigators can use a Romanian/English keyword parser to create structured archive filters and save named search
Source: `docs/audits/README_BEFORE_SOURCE.txt:32-32`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0007 — Safeguards and limits: - A human makes the decision. The system alerts and prepares evidence; it never issues fines automatically.
Source: `docs/audits/README_BEFORE_SOURCE.txt:36-40`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0008 — Benefits: Faster response, fewer false alarms for operators, evidence prepared automatically, and statistics on where intervention
Source: `docs/audits/README_BEFORE_SOURCE.txt:44-44`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0009 — Architecture: The secure backend owns sessions, MFA (mandatory), tenant isolation, audit and evidence access. `frontend/` is the s
Source: `docs/audits/README_BEFORE_SOURCE.txt:54-60`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0010 — Start the secure backend and PWA locally: From the repository root, with Docker Compose v2.20+ and Python 3.12:
Source: `docs/audits/README_BEFORE_SOURCE.txt:64-64`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0011 — Start the secure backend and PWA locally: *(The Docker stack was not built or run when this branch was prepared; the supported ver
Source: `docs/audits/README_BEFORE_SOURCE.txt:71-73`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0012 — Start the secure backend and PWA locally: Use `RS_SEED_PASSWORD` from the generated, git-ignored `.env`. First login requires TOTP
Source: `docs/audits/README_BEFORE_SOURCE.txt:79-80`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0013 — Start the secure backend and PWA locally: For host development, the backend entrypoint is `uvicorn app.main:create_app --factory` 
Source: `docs/audits/README_BEFORE_SOURCE.txt:82-85`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0014 — Start each interface in development: Use Node.js 22 (vitest 5 needs >= 22.12). Run each command from the repository root in a sepa
Source: `docs/audits/README_BEFORE_SOURCE.txt:89-89`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0015 — Police operator UI (real backend; VITE_USE_MOCKS=1 gives labelled demo data): cd frontend npm ci npm run dev -- --port 5173 ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:93-96`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0016 — Secure PWA: host development API on http://127.0.0.1:8000: cd secure-pwa npm ci npm run dev -- --port 5174 ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:100-103`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0017 — Secure PWA: host development API on http://127.0.0.1:8000: The PWA development server serves the UI shell over HTTP. Secure sessio
Source: `docs/audits/README_BEFORE_SOURCE.txt:105-109`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0018 — Start the detector: For secure remote ingestion create a tenant service account and register its camera, then:
Source: `docs/audits/README_BEFORE_SOURCE.txt:120-120`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0019 — or one camera in the foreground: .venv/bin/python -m roadsentinel.pipeline cameras/demo-highway.yaml --live --no-wandb: Trust the 
Source: `docs/audits/README_BEFORE_SOURCE.txt:130-134`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0020 — Legacy standalone demo: `roadsentinel/server.py` and `web/` form a separate demo with a local event store, not the secure platform
Source: `docs/audits/README_BEFORE_SOURCE.txt:138-146`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0021 — How the prototype is built: | Step | Code | What it does | |---|---|---| | Detection + tracking | `roadsentinel/pipeline.py`, `roa
Source: `docs/audits/README_BEFORE_SOURCE.txt:150-160`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0022 — How the prototype is built: Demo data: Roboflow `supervision` sample clips (`scripts/download_data.sh`). The urban camera's calibr
Source: `docs/audits/README_BEFORE_SOURCE.txt:162-163`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0023 — Security foundation: Security details: docs/SECURITY.md · docs/THREAT_MODEL.md · [docs
Source: `docs/audits/README_BEFORE_SOURCE.txt:167-170`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0024 — Development logins (DEV ONLY): All seeded accounts share the password in `RS_SEED_PASSWORD` from your `.env` (random per machine).
Source: `docs/audits/README_BEFORE_SOURCE.txt:174-175`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0025 — Development logins (DEV ONLY): | Tenant | Accounts | |---|---| | RoadSentinel Platform | `sysadmin@roadsentinel.local` (system adm
Source: `docs/audits/README_BEFORE_SOURCE.txt:177-181`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0026 — Development logins (DEV ONLY): New accounts are created only through invitations (Users API, tenant admin) – there is no public re
Source: `docs/audits/README_BEFORE_SOURCE.txt:183-184`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0027 — Backend: needs a PostgreSQL 16 superuser URL; creates a throwaway database "rs_test": cd backend python -m venv .venv && . .venv/b
Source: `docs/audits/README_BEFORE_SOURCE.txt:200-206`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0028 — Backend: needs a PostgreSQL 16 superuser URL; creates a throwaway database "rs_test": In a new terminal, from the repository root:
Source: `docs/audits/README_BEFORE_SOURCE.txt:208-208`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0029 — Secure PWA: cd secure-pwa npm ci && npm run lint && npm run typecheck && npm test && npm run build ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:212-214`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0030 — Secure PWA: CI (`.github/workflows/ci.yml`) defines jobs for the backend (real PostgreSQL), `secure-pwa/`, `frontend/`, the pipeli
Source: `docs/audits/README_BEFORE_SOURCE.txt:216-218`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0031 — RoadSentinel API contracts: This page documents two distinct contracts. The secure backend in `backend/` is authoritative for supp
Source: `API.md:3-6`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0032 — RoadSentinel API contracts: All dashboard endpoints use a session cookie set by `POST /api/login`. A `401` means "show the login s
Source: `API.md:8-9`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0033 — RoadSentinel API contracts: Two servers implement portions of this compatibility contract. **`backend/` is authoritative**; `roads
Source: `API.md:11-13`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0034 — RoadSentinel API contracts: The API descriptions through **Server configuration** below describe the legacy implementation unless 
Source: `API.md:15-17`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0035 — Auth: | Method | Path | Body | Returns | |---|---|---|---| | POST | `/api/login` | `{"operator": "ag. Popescu", "password": "..."}
Source: `API.md:21-25`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0036 — Auth: The operator name from the session is what the audit log records for every view and decision.
Source: `API.md:27-27`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0037 — Alerts: | Method | Path | Notes | |---|---|---| | GET | `/api/events?status=new&camera_id=demo-highway` | `Event[]`, undecided fir
Source: `API.md:31-37`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0038 — Alerts: `Event`:
Source: `API.md:39-39`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0039 — Alerts: - `priority`: `critical` | `high` | `medium` | `info` - `status`: `new` | `confirmed` | `rejected` - `vlm_status`: `pendin
Source: `API.md:57-61`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0040 — Alerts: `AuditEntry`:
Source: `API.md:63-63`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0041 — Alerts: `action` is one of `login`, `detected`, `viewed`, `confirmed`, `rejected`, `vlm_confirmed`, `vlm_rejected`, `vlm_uncertain
Source: `API.md:69-70`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0042 — Live updates: `GET /api/stream` is a Server-Sent Events stream:
Source: `API.md:74-74`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0043 — Live updates: Alerts carry an SSE `id`, so on reconnect the browser sends `Last-Event-ID` and alerts created in the gap are replay
Source: `API.md:83-84`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0044 — Search, stats, cameras, audit: | Method | Path | Notes | |---|---|---| | POST | `/api/search` | Body `{"q": "camioane oprite pe ac
Source: `API.md:88-100`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0045 — Search, stats, cameras, audit: `filter` fields: `event_types[]`, `object_classes[]`, `priorities[]`, `date_from`/`date_to` (local 
Source: `API.md:102-105`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0046 — Ingestion (pipeline → API, not for the UI): HMAC per service account; the pipeline uses `RS_API_URL`, `RS_INGEST_KEY_ID`, and `RS_
Source: `API.md:109-110`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0047 — Ingestion (pipeline → API, not for the UI): | Method | Path | Body | |---|---|---| | POST | `/api/ingest/events` | multipart: `eve
Source: `API.md:112-116`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0048 — Server configuration: | Variable | Purpose | |---|---| | `DATABASE_URL` | `postgresql+psycopg://...`; defaults to SQLite in `data/
Source: `API.md:120-126`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0049 — Server configuration: On Railway (`RAILWAY_ENVIRONMENT` is set) the server refuses to start without `DASHBOARD_PASSWORD`, `SECRET_
Source: `API.md:128-131`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0050 — Secure backend (`backend/`): Same paths and JSON. What changes for a client:
Source: `API.md:135-135`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0051 — Secure backend (`backend/`): | Topic | Secure backend | |---|---| | CSRF | Every `POST`/`PATCH`/`DELETE` needs header `X-CSRF-Toke
Source: `API.md:137-155`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0052 — Added in release/ready (secure backend only): | Area | Endpoint | Notes | |---|---|---| | Ingestion | `POST /api/ingest/events` | 
Source: `API.md:159-174`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0053 — Added in release/ready (secure backend only): Evidence rule: `POST /api/evidence/{id}/access {"variant":"original"}`, `/export` an
Source: `API.md:176-176`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0054 — RoadSentinel: handoff (state of `release/ready`): Read next: `docs/IMPLEMENTATION_PROGRESS.md` (what was done and how it was verif
Source: `HANDOFF.md:3-3`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0055 — What is where: | Folder | What | |---|---| | `backend/` | The product API (FastAPI, PostgreSQL with row-level security, MFA, signe
Source: `HANDOFF.md:6-16`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0056 — Decisions in force: * MFA is mandatory. `RS_MFA_EXEMPTION_ENABLED` exists for local demos only and is refused in production. * Dep
Source: `HANDOFF.md:19-24`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0057 — Run it: `docs/SETUP.md` (Linux, macOS, Windows). One command for a local demo with synthetic data: `python scripts/demo.py`.
Source: `HANDOFF.md:27-27`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0058 — Integrating the teammate's model: `docs/MODEL_INTEGRATION.md`.
Source: `HANDOFF.md:30-30`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0059 — Open questions for the owners: 1. Written permission from the webcam owner (WebcamRomania / Grand Hotel Traian) and the dataset li
Source: `HANDOFF.md:33-36`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0060 — RoadSentinel – Production target architecture (roadmap): > **Everything on this page is NOT implemented.** It describes how the ha
Source: `docs/ARCHITECTURE_TARGET.md:3-5`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0061 — Key management – NOT IMPLEMENTED: * Replace `EnvKeyProvider` with a `KeyProvider` backed by a KMS or HSM (HashiCorp Vault Transit,
Source: `docs/ARCHITECTURE_TARGET.md:9-16`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0062 — Identity – NOT IMPLEMENTED: * SSO via OpenID Connect against the police identity provider (Keycloak, Entra ID, national IdP),   wi
Source: `docs/ARCHITECTURE_TARGET.md:20-26`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0063 — Authorization – NOT IMPLEMENTED: * Externalize policies to OPA (Rego) or AWS Cedar, versioned and tested in CI; ABAC attributes   
Source: `docs/ARCHITECTURE_TARGET.md:30-32`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0064 — Network and platform – NOT IMPLEMENTED: * WAF and DDoS protection in front of Caddy; private connectivity (VPN / police network) f
Source: `docs/ARCHITECTURE_TARGET.md:36-41`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0065 — Monitoring and audit – NOT IMPLEMENTED: * SIEM export of audit and security events (syslog/CEF or OpenTelemetry), with alert rules
Source: `docs/ARCHITECTURE_TARGET.md:45-50`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0066 — GDPR and Directive (EU) 2016/680 – NOT IMPLEMENTED (organizational + technical): * Documented legal basis and purpose limitation p
Source: `docs/ARCHITECTURE_TARGET.md:54-64`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0067 — Limits (what this system is not, today): Written to be read by someone deciding whether to trust it. Items marked **measured** hav
Source: `docs/LIMITS.md:3-3`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0068 — Product: * It alerts and prepares evidence; **a human decides**. It issues no fines. "Dispatch patrol / warning sign / enforcement
Source: `docs/LIMITS.md:6-9`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0069 — Detection accuracy: nothing is validated: * No accuracy figure for any model on real footage exists in this repo. Earlier metrics 
Source: `docs/LIMITS.md:12-17`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0070 — Privacy and compliance (not legal advice): * **No claim of GDPR / Directive 2016/680 compliance is made.** No DPIA, legal basis or
Source: `docs/LIMITS.md:20-25`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0071 — Security: * MFA mandatory (TOTP + recovery codes). Demo exemption exists, is off by default and refused in production. * One API p
Source: `docs/LIMITS.md:28-31`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0072 — Process: * Bus factor: see docs/IMPLEMENTATION_PROGRESS.md and the audit report; weights, Railway access and prod credentials are 
Source: `docs/LIMITS.md:34-34`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0073 — Runtime choice and licenses: The supported local inference path is Megvii YOLOX-S in ONNX format, ONNX Runtime's CPU execution pro
Source: `docs/MODEL_INTEGRATION.md:5-11`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0074 — Runtime choice and licenses: No automatic download occurs at application startup. The expected local weight file is `models/yolox_
Source: `docs/MODEL_INTEGRATION.md:13-14`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0075 — Current local artifact: | Item | Value | |---|---| | Model | Megvii YOLOX-S, COCO, ONNX | | Source | [Official Megvii release](htt
Source: `docs/MODEL_INTEGRATION.md:18-28`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0076 — Current local artifact: Supervision 0.30.7 is pinned because 0.31 removed `sv.ByteTrack`. PyTorch and Ultralytics are not needed f
Source: `docs/MODEL_INTEGRATION.md:30-32`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0077 — Install: The dependencies are pinned in root `requirements.txt`. To install into this repository's venv:
Source: `docs/MODEL_INTEGRATION.md:36-36`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0078 — Install: For another machine, acquire the ONNX file from the official release URL above, verify that its SHA-256 matches the regis
Source: `docs/MODEL_INTEGRATION.md:42-44`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0079 — Run an authorized local video: The pipeline emits annotated video, optional JSONL detection records, per-class track counts, line-
Source: `docs/MODEL_INTEGRATION.md:53-56`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0080 — Run an authorized local video: For secure ingestion, set `RS_API_URL`, `RS_INGEST_KEY_ID` and `RS_INGEST_SECRET` for a local RoadS
Source: `docs/MODEL_INTEGRATION.md:58-61`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0081 — Registry and training status: `models/registry.json` records the stock YOLOX-S checksum and provenance as a `candidate`. It is not
Source: `docs/MODEL_INTEGRATION.md:65-69`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0082 — Registry and training status: No mAP, precision/recall, false-alert/hour or count-accuracy metric should be reported until an auth
Source: `docs/MODEL_INTEGRATION.md:71-74`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0083 — Rule definitions: Events come from `roadsentinel/rules.py`; whether an event becomes an **alert** is decided by `roadsentinel/aler
Source: `docs/RULES.md:3-7`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0084 — Rule definitions: | Type | Priority | Definition (thresholds in `cameras/<id>.yaml`, `thresholds:`) | Needs | |---|---|---|---| | 
Source: `docs/RULES.md:9-22`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0085 — Low-frame-rate sources: The defaults need ~5 samples per second. A slow live stream (e.g. 0.4–0.5 processed fps) never produces sp
Source: `docs/RULES.md:25-41`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0086 — RoadSentinel – Security: This document describes the security controls that are **implemented and tested** in this repository, how
Source: `docs/SECURITY.md:3-6`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0087 — Overview: | Area | Control | Where | Tests | |---|---|---|---| | Accounts | Invitation-only (no public sign-up), single-use hashed
Source: `docs/SECURITY.md:10-28`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0088 — Authentication: 1. `POST /api/auth/login` checks the password. Unknown accounts still run an Argon2 verification    against a dumm
Source: `docs/SECURITY.md:34-45`. **VERIFIED REAL END-TO-END**; priority P1.
Owner: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`. Tests: `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Evidence: `docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limit: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### REQ-0089 — Sessions and cookies: | Cookie | Content | Path | Lifetime | |---|---|---|---| | `__Secure-rs_access` | HS256 JWT `{sub, tid, sid,
Source: `docs/SECURITY.md:49-54`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0090 — Sessions and cookies: All are `Secure`, `SameSite=Strict`, and all but CSRF are `HttpOnly`. Every request re-loads the session row
Source: `docs/SECURITY.md:56-59`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0091 — Authorization and tenant isolation: * `app/core/policy.py` is the only place that maps roles → permissions. Routers depend on   `r
Source: `docs/SECURITY.md:63-80`. **VERIFIED REAL END-TO-END**; priority P1.
Owner: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`. Tests: `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Evidence: `docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limit: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### REQ-0092 — Encryption: * **Master keys** (`RS_MASTER_KEYS`, versioned) live behind the `KeyProvider` interface   (`EnvKeyProvider` today, KMS
Source: `docs/SECURITY.md:84-100`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0093 — Audit log: `entry_hash = SHA-256(canonical JSON of tenant_id, seq, timestamp, actor_id, action, resource_type, resource_id, ip, us
Source: `docs/SECURITY.md:104-110`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0094 — Audit log: Audited actions include: login success/failure/lockout, MFA success/failure/enrollment, recovery-code use, re-auth, log
Source: `docs/SECURITY.md:112-116`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0095 — Four-eyes approvals: `ApprovalRequest(kind = unblur | export)` needs a written justification (≥ 20 characters) and a case referenc
Source: `docs/SECURITY.md:120-124`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0096 — Frontend / PWA: * Cookies only; the SPA never sees a token. ESLint forbids `localStorage`,   `sessionStorage.setItem`, `eval`, `ne
Source: `docs/SECURITY.md:128-139`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0097 — Backend (needs a PostgreSQL 16 superuser URL; a throwaway DB "rs_test" is created): cd backend python -m venv .venv && .venv/bin/p
Source: `docs/SECURITY.md:145-149`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0098 — Frontend: cd secure-pwa && npm ci && npm test && npm run lint && npm run build ```
Source: `docs/SECURITY.md:152-153`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0099 — Frontend: Tests use dedicated roles (`rs_test_owner`, `rs_test_app`) so they never alter a dev database.
Source: `docs/SECURITY.md:155-155`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0100 — Known limitations (hackathon scope): * **Rate limiter is in-memory**: correct for one API process; use Redis when scaling out. * *
Source: `docs/SECURITY.md:159-184`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0101 — Setup (Linux, macOS, Windows): **Verified on Linux (Ubuntu 24.04) only.** The macOS and Windows commands are the equivalent ones b
Source: `docs/SETUP.md:3-3`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0102 — Prerequisites: * Python 3.12 (`uv` recommended), Node.js 22 (>= 22.12), PostgreSQL 16+ (the suite passed on 18.6; CI is configured
Source: `docs/SETUP.md:6-7`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0103 — PostgreSQL without Docker or root: | OS | How | |---|---| | Linux / macOS | `conda create -n rs-pg -c conda-forge postgresql -y`, 
Source: `docs/SETUP.md:10-13`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0104 — PostgreSQL without Docker or root: Use a **localhost-only** cluster with a throwaway password for development. Never reuse it.
Source: `docs/SETUP.md:15-15`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0105 — RoadSentinel – Threat model (STRIDE): Scope: the security foundation in this repository (API, database, evidence store, PWA, rever
Source: `docs/THREAT_MODEL.md:3-4`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0106 — Assets: | Asset | Why it matters | |---|---| | Evidence (clips/keyframes, original and redacted) | Personal data (faces, plates), 
Source: `docs/THREAT_MODEL.md:8-16`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0107 — Actors: * **Operator / patrol / admin / auditor** of a police unit (tenant) – legitimate, partly trusted. * **Malicious or curious
Source: `docs/THREAT_MODEL.md:20-25`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0108 — Trust boundaries: 1. Internet ↔ Caddy (TLS termination). 2. Caddy ↔ API (internal network). 3. API ↔ DB (internal `db` network, re
Source: `docs/THREAT_MODEL.md:36-38`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0109 — Threats and mitigations: Phase numbers refer to the implementation phases (0 skeleton, 1 authentication, 2 authorization & isolati
Source: `docs/THREAT_MODEL.md:42-43`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0110 — S – Spoofing: | Threat | Mitigation | Phase | |---|---|---| | Password guessing / credential stuffing | Argon2id, min length + com
Source: `docs/THREAT_MODEL.md:47-55`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0111 — T – Tampering: | Threat | Mitigation | Phase | |---|---|---| | CSRF on state-changing endpoints | SameSite=Strict + double-submit 
Source: `docs/THREAT_MODEL.md:59-68`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0112 — R – Repudiation: | Threat | Mitigation | Phase | |---|---|---| | "I never viewed that evidence" | Every signed URL issuance and ev
Source: `docs/THREAT_MODEL.md:72-77`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0113 — I – Information disclosure: | Threat | Mitigation | Phase | |---|---|---| | Cross-tenant data access (IDOR) | RLS FORCE + restrict
Source: `docs/THREAT_MODEL.md:81-93`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0114 — D – Denial of service: | Threat | Mitigation | Phase | |---|---|---| | Login/MFA flooding | Rate limits (429 + Retry-After) | 1 | 
Source: `docs/THREAT_MODEL.md:97-102`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0115 — D – Denial of service: Residual: no WAF / global DDoS protection (see roadmap).
Source: `docs/THREAT_MODEL.md:104-104`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0116 — E – Elevation of privilege: | Threat | Mitigation | Phase | |---|---|---| | Operator performs admin actions | Central permission m
Source: `docs/THREAT_MODEL.md:108-115`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0117 — Residual risks: See "Known limitations" in SECURITY.md and the roadmap in [ARCHITECTURE_TARGET.md](ARCHITECTURE_TAR
Source: `docs/THREAT_MODEL.md:119-120`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0118 — Romanian HLS adapter status — 2026-11-07: The configured-source layer now recognizes HLS master playlists, selects variants within
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:5-11`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0119 — 2026-11-07 physical camera availability update: The code now accepts explicit `device:N` UVC input through the existing YOLOX-S ON
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:15-22`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0120 — 2026-11-07 physical camera availability update: Last verified: 2026-11-06 (local CPU run)
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:24-24`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0121 — Runtime and provenance: - Detector: Megvii YOLOX-S COCO, ONNX; official release artifact from the [Megvii YOLOX release](https://g
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:28-32`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0122 — Input and rights: Input was the recorded Wikimedia Commons file [Street traffic.webm](https://commons.wikimedia.org/wiki/File:Stre
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:36-36`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0123 — Reproduction and observed results: Command (camera config was a local temporary test config; no source URL or credentials):
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:40-40`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0124 — Reproduction and observed results: The command completed with exit code 0. It processed 105 sampled frames across 34.9 seconds (so
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:48-48`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0125 — Reproduction and observed results: - 1,085 tracked observations and 67 unique tracks. - Track counts by class: bus 13, car 32, tru
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:50-54`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0126 — Reproduction and observed results: The tracker/class totals and line-crossing measurements are pipeline outputs, not labeled groun
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:56-56`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0127 — Current acceptance boundary: Verified: actual official weights loaded; real vehicle boxes/classes/confidences produced; ByteTrack 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:60-60`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0128 — Local live-replay vertical slice (2026-11-06): The integration test served the licensed clip continuously from a loopback-only MJP
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:64-69`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0129 — Local live-replay vertical slice (2026-11-06): Run from `backend/` (requires the locally approved sample/model, `.venv`, Node 22, 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:71-72`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0130 — Local live-replay vertical slice (2026-11-06): Latest result: **1 passed** (2026-11-06). The loopback source served 10 FPS; the CP
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:80-83`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0131 — Local live-replay vertical slice (2026-11-06): At persistence, latency p50/p95/p99 was 84.49/99.41/103.85 ms and peak RSS was 346.
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:85-89`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0132 — Authenticated annotated frame evidence (2026-11-06): The preview path now publishes redacted, annotated JPEG frames through the ex
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:93-97`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0133 — Authenticated annotated frame evidence (2026-11-06): Bounded real-model E2E command and result:
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:99-99`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0134 — Authenticated annotated frame evidence (2026-11-06): Result: **1 passed**. The browser test waited for successful natural image di
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:108-114`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0135 — Authenticated annotated frame evidence (2026-11-06): At the E2E telemetry snapshot for this run: 63 processed frames, 315 detectio
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:116-119`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0136 — Authenticated annotated frame evidence (2026-11-06): This is one recorded San Francisco scene on one CPU machine. It does not vali
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:121-127`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0137 — Repeat after camera-catalog UI change (2026-11-06): The actual-model full E2E was run again after adding the Romanian read-only di
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:131-131`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0138 — Repeat after camera-catalog UI change (2026-11-06): Exit code 0, **1 passed**. The persisted telemetry snapshot reported 64 proces
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:140-145`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0139 — Repeat after camera-catalog UI change (2026-11-06): The browser image and overlays are preserved locally at `data/vision/evidence/
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:147-151`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0140 — Repeat after camera-catalog UI change (2026-11-06): The final catalog-inclusive browser run passed after correcting its expected c
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:153-158`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0141 — Repeat after camera-catalog UI change (2026-11-06): After moving the catalog module out of the repository's ignored `data/` path, 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:160-166`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0142 — 5-minute security demo (for judges): Preparation (before the demo):
Source: `scripts/demo_security.md:3-3`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0143 — 5-minute security demo (for judges): Open https://localhost (trust Caddy's local certificate). The dev password for every seeded a
Source: `scripts/demo_security.md:11-14`. **PARTIAL**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md;docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Four existing Unit A roles + repeat operator challenge pass on A. Unit B and platform hashes match; their browser enrollments were not performed. HTTPS production deployment and broader workflows remain unverified.

### REQ-0144 — 5-minute security demo (for judges): Shortcut for the terminal: `alias dc='docker compose --env-file .env -f deploy/docker-compose
Source: `scripts/demo_security.md:16-16`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0145 — 5-minute security demo (for judges): ---
Source: `scripts/demo_security.md:18-18`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0146 — 1. Unit B cannot see Unit A (≈ 1 min): 1. Browser A (`operator.a@roadsentinel.local`): open any alert, copy its URL (`/alerts/<id>
Source: `scripts/demo_security.md:22-29`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0147 — 2. Audit tampering is detected (≈ 1 min): 1. `auditor.a` → Audit → **Verify integrity** → ✔ chain intact. 2. Terminal: `dc run --r
Source: `scripts/demo_security.md:33-38`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0148 — 3. Unblur needs a second person, and it is audited (≈ 1.5 min): 1. `operator.a`: open a critical alert → evidence is **blurred**, 
Source: `scripts/demo_security.md:42-50`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0149 — 4. The database only holds ciphertext (≈ 45 s): Point out the `F1` (field) and `RSE1` (file) headers followed by random bytes: AES
Source: `scripts/demo_security.md:60-62`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0150 — 5. Installable PWA with generic push (≈ 45 s): 1. In Chrome/Edge: install icon in the address bar → RoadSentinel opens as a standa
Source: `scripts/demo_security.md:66-73`. **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Tests: `See TEST_EXECUTION_LEDGER.md`.
Evidence: `No direct current-run criterion-level acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A01 — Product/interfaces
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `frontend/src/App.tsx;secure-pwa/src;backend/app/main.py`. Tests: `backend/tests/test_contract_api.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Secure backend authoritative; legacy architecture table contradicts current architecture. PWA browser not exercised.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A02 — Detection/tracking
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `roadsentinel/detector.py;roadsentinel/pipeline.py;models/registry.json`. Tests: `backend/tests/test_mission_vertical.py`.
Evidence: `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Actual inference on licensed-derived synthetic frozen fixture; no incident accuracy measurement.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A03 — Adapters/rights
Source: `README.md + linked specs:1-218`. **TESTED SYNTHETIC ONLY**; priority P0.
Owner: `roadsentinel/sources.py;roadsentinel/consent.py;roadsentinel/replay.py`. Tests: `tests/test_sources.py;tests/test_consent.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Local adapters tested. External rights not established; no remote media fetched.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A04 — Geometry/calibration
Source: `README.md + linked specs:1-218`. **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/geometry.py;backend/app/services/camera_config.py`. Tests: `tests/test_rules_rates.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Synthetic geometry is not a calibrated real road. No speed certification.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A05 — Rule thresholds
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `roadsentinel/rules.py;backend/app/services/offline_analysis.py`. Tests: `tests/test_rules.py;tests/test_mission_vertical.py`.
Evidence: `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Frozen-frame model tracks produce nine candidates; this is not street incident validation.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A06 — Critical event types
Source: `README.md + linked specs:1-218`. **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/rules.py;backend/app/core/catalog.py`. Tests: `tests/test_rules.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Wrong way/pedestrian/crash/object production precision and recall remain unverified.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A07 — High event types
Source: `README.md + linked specs:1-218`. **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/rules.py`. Tests: `tests/test_rules.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Stopped/offline candidate bridge implemented. Physical speed and near miss remain unvalidated.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A08 — Medium event types
Source: `README.md + linked specs:1-218`. **TESTED SYNTHETIC ONLY**; priority P2.
Owner: `roadsentinel/rules.py;roadsentinel/rates.py`. Tests: `tests/test_rules_rates.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Sampling constraints matter; no operational validation.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A09 — Information/offline rules
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/services/offline_analysis.py`. Tests: `backend/tests/test_mission_vertical.py`.
Evidence: `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Line counts stay analytics; only obstruction/queue eligible for explicit recorded review.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A10 — Evidence assembly
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;roadsentinel/pipeline.py`. Tests: `backend/tests/test_mission_vertical.py;backend/tests/test_evidence_integrity.py`.
Evidence: `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: HTTP media + encryption verified for recorded fixture; crash orphan cleanup remains open.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A11 — Signed ingestion
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P0.
Owner: `roadsentinel/sink.py;backend/app/api/ingest.py;backend/app/services/ingest_auth.py`. Tests: `backend/tests/test_ingest_auth.py;backend/tests/test_ingest_idempotency.py`.
Evidence: `docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md`.
Next acceptance: Use final execution ledger for test-level outcomes; managed fencing newly added.
Limit: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A12 — Operator queue
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `frontend/src/store/data.ts;backend/app/api/contract.py`. Tests: `backend/tests/test_contract_api.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: API exercised; new UI source labels compile. Full candidate promotion browser journey not verified.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A13 — Decisions/patrol
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/contract.py;backend/app/api/patrol.py`. Tests: `backend/tests/test_mission_vertical.py;backend/tests/test_patrol_stats.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Actual HTTP reject tested for recorded fixture. Signs/enforcement remain action labels.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A14 — Archive/saved searches
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `backend/app/services/search.py;backend/app/api/contract.py`. Tests: `backend/tests/test_pagination.py`.
Evidence: `docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md`.
Next acceptance: Tenant-filtered parser and keyset paging exist; browser retrieval of new candidate not yet demonstrated.
Limit: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A15 — Investigation/export
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py`. Tests: `backend/tests/test_evidence_integrity.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Basic case-note/license-grant/four-eyes export/hash verification passed; next bookmark, legal hold, revoked grant, tampering and browser export.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A16 — Camera administration
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/camera_control.py;backend/app/services/camera_config.py;frontend/src/components/CameraControlPanel.tsx`. Tests: `backend/tests/test_managed_live_runtime.py;frontend/e2e/camera-control-runtime.mjs`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Config creation/approval/activation passed via authenticated APIs, registration and preview via browser. Next automate the entire configuration editor and approval in two independent browser contexts.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A17 — Clients/accessibility
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P2.
Owner: `frontend/src;secure-pwa/src`. Tests: `frontend/src/store/auth.test.ts`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Frontend build and 15 tests pass. PWA browser and accessibility acceptance remain unverified.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A18 — Authentication/MFA/RLS
Source: `README.md + linked specs:1-218`. **VERIFIED REAL END-TO-END**; priority P0.
Owner: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`. Tests: `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Evidence: `docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limit: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### A19 — Keys/audit
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `backend/app/core/crypto.py;backend/app/core/audit.py;backend/app/core/audit_anchor.py`. Tests: `backend/tests/test_crypto.py;backend/tests/test_audit.py`.
Evidence: `docs/audits/TEST_EXECUTION_LEDGER.md;docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md`.
Next acceptance: AES-GCM and hash chain exist. Local checkpoint is not independent external custody.
Limit: Targeted backend regression suites passed on B; not a full production threat assessment or complete archive browser acceptance.

### A20 — Privacy/legal
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P0.
Owner: `roadsentinel/redaction.py;roadsentinel/consent.py;backend/app/services/retention.py`. Tests: `tests/test_privacy_defaults.py;backend/tests/test_retention.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Heuristic redaction is not anonymization. No legal/DPIA sign-off or enforcement integration.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A21 — Model governance
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `roadsentinel/models.py;models/registry.json;training`. Tests: `tests/test_models.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Stock model hash known; external configurable model path added. No representative evaluated activation.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A22 — Real accuracy
Source: `README.md + linked specs:1-218`. **EXTERNALLY BLOCKED**; priority P1.
Owner: `docs/LIMITS.md;models/reports`. Tests: `tests/test_evaluation.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: No labeled representative data/approved target metrics. Counts not ground truth.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A23 — Offline jobs
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/offline_video.py;backend/app/services/offline_analysis.py;backend/app/models/offline_video.py`. Tests: `backend/tests/test_mission_vertical.py;backend/tests/test_offline_video_authz.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Upload/crop/job/candidates/media/review tested over HTTP. Restart/browser/retention matrix incomplete.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A24 — Live worker
Source: `README.md + linked specs:1-218`. **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `roadsentinel/remote_config.py;roadsentinel/live.py;roadsentinel/pipeline.py;backend/app/api/camera_worker.py`. Tests: `backend/tests/test_managed_live_runtime.py;tests/test_remote_config.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Real managed replay, duplicate lease refusal, revision 1 to 2, outage recovery, disable/re-enable passed. Next provide lawful positive live event and multi-camera soak.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A25 — Contracts
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P0.
Owner: `backend/app/schemas/contract.py;frontend/src/lib/adapters.ts;API.md`. Tests: `backend/tests/test_contract_api.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Legacy/secure contract coexist. New origin stored in details; labels added conservatively, unknown source disclosed.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A26 — Migrations/seed
Source: `README.md + linked specs:1-218`. **VERIFIED REAL END-TO-END**; priority P0.
Owner: `backend/app/services/lookup_roles.py;backend/app/services/seed.py;backend/app/db.py;frontend/src/store/auth.ts`. Tests: `backend/tests/test_lookup_ownership.py;backend/tests/test_seed.py;backend/tests/test_auth.py;frontend/e2e/live-login-recovery.mjs`.
Evidence: `docs/audits/INTEGRATED_LOGIN_RECOVERY_REPORT.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Keep forced-RLS lookup, partial seed, password/MFA/CSRF negative tests in release checks.
Limit: Verified existing development runtime A and fresh disposable PostgreSQL B through 0022. Not production certification or external IdP coverage.

### A27 — Install/readiness
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `deploy/docker-compose.yml;frontend/vite.config.ts;backend/app/api/health.py`. Tests: `backend/tests/test_ops_and_authz.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Current proxy correct. Compose not executed. Readiness does not mean a camera is online.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A28 — Testing/CI
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `backend/tests;tests;frontend/e2e;.github/workflows/ci.yml`. Tests: `TEST_EXECUTION_LEDGER.md`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Local execution evidence only; no GitHub CI execution or push.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A29 — Legacy boundaries
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `roadsentinel/server.py;web;README.md`. Tests: `tests/test_api.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Legacy batch destructive semantics remain isolated; not used for mission E2E.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A30 — Optional AI/telemetry
Source: `README.md + linked specs:1-218`. **IMPLEMENTED UNVERIFIED**; priority P2.
Owner: `roadsentinel/vlm.py;roadsentinel/tracking.py`. Tests: `tests/test_privacy_defaults.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: External VLM and W&B not enabled in mission; no external data transmission test.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A31 — Romanian source catalog
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `cameras/romanian-source-registry.json;backend/app/services/camera_discovery.py`. Tests: `backend/tests/test_camera_discovery.py`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Catalog restored from original source. Candidates remain ingestion-disabled; no rights or availability claim.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A32 — Optional scope
Source: `README.md + linked specs:1-218`. **NOT APPLICABLE / OPTIONAL**; priority P3.
Owner: `docs/LIMITS.md;README.md`. Tests: `not applicable`.
Evidence: `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Fog/ice/plate/facial/enforcement/SSO not added. No automatic sanctions.
Limit: Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A33 — Reliability/backpressure
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P0.
Owner: `roadsentinel/live.py;backend/app/services/camera_control.py`. Tests: `tests/test_live.py;backend/tests/test_managed_heartbeat.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Critical queue overflow bounded; stale sequences no longer extend lease. Long soak/multi-camera absent.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A34 — Honest presentation
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P1.
Owner: `frontend/src/lib/adapters.ts;frontend/src/pages/VideoAnalysisPage.tsx`. Tests: `frontend/src/store/auth.test.ts`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: RECORDED/LOCAL REPLAY/SYNTHETIC source prefixes. No external live or accuracy badge inferred.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.

### A35 — Integrated guarantees
Source: `README.md + linked specs:1-218`. **PARTIAL**; priority P0.
Owner: `backend/app/models/camera_control.py;backend/app/models/casework.py;backend/app/models/investigation.py`. Tests: `backend/tests/test_isolation.py`.
Evidence: `docs/audits/FULL_INTEGRATION_E2E_VALIDATION.md;docs/audits/ACTUAL_BROWSER_LOGIN_EVIDENCE.md`.
Next acceptance: Tenant table inventory now derived after all models imported. Imported case/control paths need more end-to-end coverage.
Limit: Actual model/HTTP/Chromium fixture flows verified on B; existing password/MFA/dashboard verified on A. Synthetic frozen positive is not a genuine incident; no external live source, soak or complete restart/export browser coverage.
