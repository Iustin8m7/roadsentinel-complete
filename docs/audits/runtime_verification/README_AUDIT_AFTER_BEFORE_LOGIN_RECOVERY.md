# Post-integration README audit — after

The before audit and source snapshot are preserved. Inventory: 150 source paragraph/table criteria plus all 35 mandatory category checks. This is a broad source-grounded coverage review with functional evidence where executed; **it is not an assertion that every requirement or every transitively linked document was exhaustively acceptance-tested**. Remaining unknowns stay unverified.

## Delivered behavior and proof

- F1 PARTIAL: actual recorded upload/crop/YOLOX/ByteTrack/candidates → explicit canonical review promotion → encrypted keyframe/clip → authenticated browser display and duplicate resubmission → operator rejection via real HTTP. Frozen fixture is explicitly synthetic. No automatic live dispatch.
- F2 PARTIAL: actual local MJPEG recording replay → approved-fixture config → HMAC lease + ACK revision 1 → real pipeline inference/tracking → changing authenticated preview → stop after disable. Managed event/preview fencing and bounded queue are implemented. Full outage/reconfigure/browser/case acceptance remains open.
- Tests: 419 backend passed, 2 skipped; final new-flow regression 3 passed; pipeline 91; React 15; PWA 9. See exact ledger and failure history.
- Existing integration auth remains blocked by lookup owner without BYPASSRLS. Test authentication used actual MFA on disposable resources; no bypass introduced. Existing DB/credentials were preserved.
- Snapshot omissions repaired: common_passwords.txt, demo/local-UVC/Iasi source profiles, Romanian discovery registry and PWA tokens.css. Public candidates remain disabled. Additive 0021 reconciles two offline indexes; applied only to fresh mission DBs.
- README corrected authoritative API/evidence/optional telemetry/person-identity wording, added source-safe recorded review and managed worker limitations. Paragraph BEFORE anchors refer to README_BEFORE_SOURCE.txt.

## Category evidence and remaining acceptance

### REQ-0001 — RoadSentinel: AI traffic-camera monitoring that sends evidence-backed alerts to police operators and patrols. Hackathon project / 
Source: `docs/audits/README_BEFORE_SOURCE.txt:3-3`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0002 — What it does: 1. **Camera processing.** A YOLO detector with tracking can process configured camera sources and compute speed, har
Source: `docs/audits/README_BEFORE_SOURCE.txt:7-10`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0003 — Alert types: | Priority | Event | |---|---| | Critical | Wrong-way driving, pedestrian on road, probable crash, object on roadway 
Source: `docs/audits/README_BEFORE_SOURCE.txt:14-19`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0004 — Alert types: Definitions and sampling-rate limits: [docs/RULES.md](../RULES.md). All rules are tested on synthetic tracks only. 
Source: `docs/audits/README_BEFORE_SOURCE.txt:21-21`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0005 — Alert flow: - The system detects the event and attaches the clip, key frames, location, time, and the rule that fired. - The opera
Source: `docs/audits/README_BEFORE_SOURCE.txt:25-28`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0006 — Archive search: Investigators can use a Romanian/English keyword parser to create structured archive filters and save named search
Source: `docs/audits/README_BEFORE_SOURCE.txt:32-32`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0007 — Safeguards and limits: - A human makes the decision. The system alerts and prepares evidence; it never issues fines automatically.
Source: `docs/audits/README_BEFORE_SOURCE.txt:36-40`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0008 — Benefits: Faster response, fewer false alarms for operators, evidence prepared automatically, and statistics on where intervention
Source: `docs/audits/README_BEFORE_SOURCE.txt:44-44`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0009 — Architecture: The secure backend owns sessions, MFA (mandatory), tenant isolation, audit and evidence access. `frontend/` is the s
Source: `docs/audits/README_BEFORE_SOURCE.txt:54-60`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0010 — Start the secure backend and PWA locally: From the repository root, with Docker Compose v2.20+ and Python 3.12:
Source: `docs/audits/README_BEFORE_SOURCE.txt:64-64`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0011 — Start the secure backend and PWA locally: *(The Docker stack was not built or run when this branch was prepared; the supported ver
Source: `docs/audits/README_BEFORE_SOURCE.txt:71-73`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0012 — Start the secure backend and PWA locally: Use `RS_SEED_PASSWORD` from the generated, git-ignored `.env`. First login requires TOTP
Source: `docs/audits/README_BEFORE_SOURCE.txt:79-80`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0013 — Start the secure backend and PWA locally: For host development, the backend entrypoint is `uvicorn app.main:create_app --factory` 
Source: `docs/audits/README_BEFORE_SOURCE.txt:82-85`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0014 — Start each interface in development: Use Node.js 22 (vitest 5 needs >= 22.12). Run each command from the repository root in a sepa
Source: `docs/audits/README_BEFORE_SOURCE.txt:89-89`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0015 — Police operator UI (real backend; VITE_USE_MOCKS=1 gives labelled demo data): cd frontend npm ci npm run dev -- --port 5173 ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:93-96`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0016 — Secure PWA: host development API on http://127.0.0.1:8000: cd secure-pwa npm ci npm run dev -- --port 5174 ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:100-103`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0017 — Secure PWA: host development API on http://127.0.0.1:8000: The PWA development server serves the UI shell over HTTP. Secure sessio
Source: `docs/audits/README_BEFORE_SOURCE.txt:105-109`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0018 — Start the detector: For secure remote ingestion create a tenant service account and register its camera, then:
Source: `docs/audits/README_BEFORE_SOURCE.txt:120-120`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0019 — or one camera in the foreground: .venv/bin/python -m roadsentinel.pipeline cameras/demo-highway.yaml --live --no-wandb: Trust the 
Source: `docs/audits/README_BEFORE_SOURCE.txt:130-134`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0020 — Legacy standalone demo: `roadsentinel/server.py` and `web/` form a separate demo with a local event store, not the secure platform
Source: `docs/audits/README_BEFORE_SOURCE.txt:138-146`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0021 — How the prototype is built: | Step | Code | What it does | |---|---|---| | Detection + tracking | `roadsentinel/pipeline.py`, `roa
Source: `docs/audits/README_BEFORE_SOURCE.txt:150-160`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0022 — How the prototype is built: Demo data: Roboflow `supervision` sample clips (`scripts/download_data.sh`). The urban camera's calibr
Source: `docs/audits/README_BEFORE_SOURCE.txt:162-163`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0023 — Security foundation: Security details: [docs/SECURITY.md](../SECURITY.md) · [docs/THREAT_MODEL.md](../THREAT_MODEL.md) · [docs
Source: `docs/audits/README_BEFORE_SOURCE.txt:167-170`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0024 — Development logins (DEV ONLY): All seeded accounts share the password in `RS_SEED_PASSWORD` from your `.env` (random per machine).
Source: `docs/audits/README_BEFORE_SOURCE.txt:174-175`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0025 — Development logins (DEV ONLY): | Tenant | Accounts | |---|---| | RoadSentinel Platform | `sysadmin@roadsentinel.local` (system adm
Source: `docs/audits/README_BEFORE_SOURCE.txt:177-181`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0026 — Development logins (DEV ONLY): New accounts are created only through invitations (Users API, tenant admin) – there is no public re
Source: `docs/audits/README_BEFORE_SOURCE.txt:183-184`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0027 — Backend: needs a PostgreSQL 16 superuser URL; creates a throwaway database "rs_test": cd backend python -m venv .venv && . .venv/b
Source: `docs/audits/README_BEFORE_SOURCE.txt:200-206`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0028 — Backend: needs a PostgreSQL 16 superuser URL; creates a throwaway database "rs_test": In a new terminal, from the repository root:
Source: `docs/audits/README_BEFORE_SOURCE.txt:208-208`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0029 — Secure PWA: cd secure-pwa npm ci && npm run lint && npm run typecheck && npm test && npm run build ```
Source: `docs/audits/README_BEFORE_SOURCE.txt:212-214`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0030 — Secure PWA: CI (`.github/workflows/ci.yml`) defines jobs for the backend (real PostgreSQL), `secure-pwa/`, `frontend/`, the pipeli
Source: `docs/audits/README_BEFORE_SOURCE.txt:216-218`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0031 — RoadSentinel API contracts: This page documents two distinct contracts. The secure backend in `backend/` is authoritative for supp
Source: `API.md:3-6`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0032 — RoadSentinel API contracts: All dashboard endpoints use a session cookie set by `POST /api/login`. A `401` means "show the login s
Source: `API.md:8-9`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0033 — RoadSentinel API contracts: Two servers implement portions of this compatibility contract. **`backend/` is authoritative**; `roads
Source: `API.md:11-13`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0034 — RoadSentinel API contracts: The API descriptions through **Server configuration** below describe the legacy implementation unless 
Source: `API.md:15-17`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0035 — Auth: | Method | Path | Body | Returns | |---|---|---|---| | POST | `/api/login` | `{"operator": "ag. Popescu", "password": "..."}
Source: `API.md:21-25`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0036 — Auth: The operator name from the session is what the audit log records for every view and decision.
Source: `API.md:27-27`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0037 — Alerts: | Method | Path | Notes | |---|---|---| | GET | `/api/events?status=new&camera_id=demo-highway` | `Event[]`, undecided fir
Source: `API.md:31-37`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0038 — Alerts: `Event`:
Source: `API.md:39-39`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0039 — Alerts: - `priority`: `critical` | `high` | `medium` | `info` - `status`: `new` | `confirmed` | `rejected` - `vlm_status`: `pendin
Source: `API.md:57-61`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0040 — Alerts: `AuditEntry`:
Source: `API.md:63-63`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0041 — Alerts: `action` is one of `login`, `detected`, `viewed`, `confirmed`, `rejected`, `vlm_confirmed`, `vlm_rejected`, `vlm_uncertain
Source: `API.md:69-70`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0042 — Live updates: `GET /api/stream` is a Server-Sent Events stream:
Source: `API.md:74-74`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0043 — Live updates: Alerts carry an SSE `id`, so on reconnect the browser sends `Last-Event-ID` and alerts created in the gap are replay
Source: `API.md:83-84`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0044 — Search, stats, cameras, audit: | Method | Path | Notes | |---|---|---| | POST | `/api/search` | Body `{"q": "camioane oprite pe ac
Source: `API.md:88-100`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0045 — Search, stats, cameras, audit: `filter` fields: `event_types[]`, `object_classes[]`, `priorities[]`, `date_from`/`date_to` (local 
Source: `API.md:102-105`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0046 — Ingestion (pipeline → API, not for the UI): HMAC per service account; the pipeline uses `RS_API_URL`, `RS_INGEST_KEY_ID`, and `RS_
Source: `API.md:109-110`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0047 — Ingestion (pipeline → API, not for the UI): | Method | Path | Body | |---|---|---| | POST | `/api/ingest/events` | multipart: `eve
Source: `API.md:112-116`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0048 — Server configuration: | Variable | Purpose | |---|---| | `DATABASE_URL` | `postgresql+psycopg://...`; defaults to SQLite in `data/
Source: `API.md:120-126`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0049 — Server configuration: On Railway (`RAILWAY_ENVIRONMENT` is set) the server refuses to start without `DASHBOARD_PASSWORD`, `SECRET_
Source: `API.md:128-131`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0050 — Secure backend (`backend/`): Same paths and JSON. What changes for a client:
Source: `API.md:135-135`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0051 — Secure backend (`backend/`): | Topic | Secure backend | |---|---| | CSRF | Every `POST`/`PATCH`/`DELETE` needs header `X-CSRF-Toke
Source: `API.md:137-155`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0052 — Added in release/ready (secure backend only): | Area | Endpoint | Notes | |---|---|---| | Ingestion | `POST /api/ingest/events` | 
Source: `API.md:159-174`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0053 — Added in release/ready (secure backend only): Evidence rule: `POST /api/evidence/{id}/access {"variant":"original"}`, `/export` an
Source: `API.md:176-176`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0054 — RoadSentinel: handoff (state of `release/ready`): Read next: `docs/IMPLEMENTATION_PROGRESS.md` (what was done and how it was verif
Source: `HANDOFF.md:3-3`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0055 — What is where: | Folder | What | |---|---| | `backend/` | The product API (FastAPI, PostgreSQL with row-level security, MFA, signe
Source: `HANDOFF.md:6-16`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0056 — Decisions in force: * MFA is mandatory. `RS_MFA_EXEMPTION_ENABLED` exists for local demos only and is refused in production. * Dep
Source: `HANDOFF.md:19-24`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0057 — Run it: `docs/SETUP.md` (Linux, macOS, Windows). One command for a local demo with synthetic data: `python scripts/demo.py`.
Source: `HANDOFF.md:27-27`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0058 — Integrating the teammate's model: `docs/MODEL_INTEGRATION.md`.
Source: `HANDOFF.md:30-30`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0059 — Open questions for the owners: 1. Written permission from the webcam owner (WebcamRomania / Grand Hotel Traian) and the dataset li
Source: `HANDOFF.md:33-36`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0060 — RoadSentinel – Production target architecture (roadmap): > **Everything on this page is NOT implemented.** It describes how the ha
Source: `docs/ARCHITECTURE_TARGET.md:3-5`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0061 — Key management – NOT IMPLEMENTED: * Replace `EnvKeyProvider` with a `KeyProvider` backed by a KMS or HSM (HashiCorp Vault Transit,
Source: `docs/ARCHITECTURE_TARGET.md:9-16`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0062 — Identity – NOT IMPLEMENTED: * SSO via OpenID Connect against the police identity provider (Keycloak, Entra ID, national IdP),   wi
Source: `docs/ARCHITECTURE_TARGET.md:20-26`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0063 — Authorization – NOT IMPLEMENTED: * Externalize policies to OPA (Rego) or AWS Cedar, versioned and tested in CI; ABAC attributes   
Source: `docs/ARCHITECTURE_TARGET.md:30-32`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0064 — Network and platform – NOT IMPLEMENTED: * WAF and DDoS protection in front of Caddy; private connectivity (VPN / police network) f
Source: `docs/ARCHITECTURE_TARGET.md:36-41`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0065 — Monitoring and audit – NOT IMPLEMENTED: * SIEM export of audit and security events (syslog/CEF or OpenTelemetry), with alert rules
Source: `docs/ARCHITECTURE_TARGET.md:45-50`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0066 — GDPR and Directive (EU) 2016/680 – NOT IMPLEMENTED (organizational + technical): * Documented legal basis and purpose limitation p
Source: `docs/ARCHITECTURE_TARGET.md:54-64`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0067 — Limits (what this system is not, today): Written to be read by someone deciding whether to trust it. Items marked **measured** hav
Source: `docs/LIMITS.md:3-3`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0068 — Product: * It alerts and prepares evidence; **a human decides**. It issues no fines. "Dispatch patrol / warning sign / enforcement
Source: `docs/LIMITS.md:6-9`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0069 — Detection accuracy: nothing is validated: * No accuracy figure for any model on real footage exists in this repo. Earlier metrics 
Source: `docs/LIMITS.md:12-17`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0070 — Privacy and compliance (not legal advice): * **No claim of GDPR / Directive 2016/680 compliance is made.** No DPIA, legal basis or
Source: `docs/LIMITS.md:20-25`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0071 — Security: * MFA mandatory (TOTP + recovery codes). Demo exemption exists, is off by default and refused in production. * One API p
Source: `docs/LIMITS.md:28-31`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0072 — Process: * Bus factor: see docs/IMPLEMENTATION_PROGRESS.md and the audit report; weights, Railway access and prod credentials are 
Source: `docs/LIMITS.md:34-34`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0073 — Runtime choice and licenses: The supported local inference path is Megvii YOLOX-S in ONNX format, ONNX Runtime's CPU execution pro
Source: `docs/MODEL_INTEGRATION.md:5-11`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0074 — Runtime choice and licenses: No automatic download occurs at application startup. The expected local weight file is `models/yolox_
Source: `docs/MODEL_INTEGRATION.md:13-14`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0075 — Current local artifact: | Item | Value | |---|---| | Model | Megvii YOLOX-S, COCO, ONNX | | Source | [Official Megvii release](htt
Source: `docs/MODEL_INTEGRATION.md:18-28`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0076 — Current local artifact: Supervision 0.30.7 is pinned because 0.31 removed `sv.ByteTrack`. PyTorch and Ultralytics are not needed f
Source: `docs/MODEL_INTEGRATION.md:30-32`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0077 — Install: The dependencies are pinned in root `requirements.txt`. To install into this repository's venv:
Source: `docs/MODEL_INTEGRATION.md:36-36`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0078 — Install: For another machine, acquire the ONNX file from the official release URL above, verify that its SHA-256 matches the regis
Source: `docs/MODEL_INTEGRATION.md:42-44`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0079 — Run an authorized local video: The pipeline emits annotated video, optional JSONL detection records, per-class track counts, line-
Source: `docs/MODEL_INTEGRATION.md:53-56`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0080 — Run an authorized local video: For secure ingestion, set `RS_API_URL`, `RS_INGEST_KEY_ID` and `RS_INGEST_SECRET` for a local RoadS
Source: `docs/MODEL_INTEGRATION.md:58-61`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0081 — Registry and training status: `models/registry.json` records the stock YOLOX-S checksum and provenance as a `candidate`. It is not
Source: `docs/MODEL_INTEGRATION.md:65-69`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0082 — Registry and training status: No mAP, precision/recall, false-alert/hour or count-accuracy metric should be reported until an auth
Source: `docs/MODEL_INTEGRATION.md:71-74`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0083 — Rule definitions: Events come from `roadsentinel/rules.py`; whether an event becomes an **alert** is decided by `roadsentinel/aler
Source: `docs/RULES.md:3-7`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0084 — Rule definitions: | Type | Priority | Definition (thresholds in `cameras/<id>.yaml`, `thresholds:`) | Needs | |---|---|---|---| | 
Source: `docs/RULES.md:9-22`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0085 — Low-frame-rate sources: The defaults need ~5 samples per second. A slow live stream (e.g. 0.4–0.5 processed fps) never produces sp
Source: `docs/RULES.md:25-41`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0086 — RoadSentinel – Security: This document describes the security controls that are **implemented and tested** in this repository, how
Source: `docs/SECURITY.md:3-6`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0087 — Overview: | Area | Control | Where | Tests | |---|---|---|---| | Accounts | Invitation-only (no public sign-up), single-use hashed
Source: `docs/SECURITY.md:10-28`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0088 — Authentication: 1. `POST /api/auth/login` checks the password. Unknown accounts still run an Argon2 verification    against a dumm
Source: `docs/SECURITY.md:34-45`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0089 — Sessions and cookies: | Cookie | Content | Path | Lifetime | |---|---|---|---| | `__Secure-rs_access` | HS256 JWT `{sub, tid, sid,
Source: `docs/SECURITY.md:49-54`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0090 — Sessions and cookies: All are `Secure`, `SameSite=Strict`, and all but CSRF are `HttpOnly`. Every request re-loads the session row
Source: `docs/SECURITY.md:56-59`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0091 — Authorization and tenant isolation: * `app/core/policy.py` is the only place that maps roles → permissions. Routers depend on   `r
Source: `docs/SECURITY.md:63-80`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0092 — Encryption: * **Master keys** (`RS_MASTER_KEYS`, versioned) live behind the `KeyProvider` interface   (`EnvKeyProvider` today, KMS
Source: `docs/SECURITY.md:84-100`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0093 — Audit log: `entry_hash = SHA-256(canonical JSON of tenant_id, seq, timestamp, actor_id, action, resource_type, resource_id, ip, us
Source: `docs/SECURITY.md:104-110`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0094 — Audit log: Audited actions include: login success/failure/lockout, MFA success/failure/enrollment, recovery-code use, re-auth, log
Source: `docs/SECURITY.md:112-116`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0095 — Four-eyes approvals: `ApprovalRequest(kind = unblur | export)` needs a written justification (≥ 20 characters) and a case referenc
Source: `docs/SECURITY.md:120-124`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0096 — Frontend / PWA: * Cookies only; the SPA never sees a token. ESLint forbids `localStorage`,   `sessionStorage.setItem`, `eval`, `ne
Source: `docs/SECURITY.md:128-139`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0097 — Backend (needs a PostgreSQL 16 superuser URL; a throwaway DB "rs_test" is created): cd backend python -m venv .venv && .venv/bin/p
Source: `docs/SECURITY.md:145-149`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0098 — Frontend: cd secure-pwa && npm ci && npm test && npm run lint && npm run build ```
Source: `docs/SECURITY.md:152-153`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0099 — Frontend: Tests use dedicated roles (`rs_test_owner`, `rs_test_app`) so they never alter a dev database.
Source: `docs/SECURITY.md:155-155`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0100 — Known limitations (hackathon scope): * **Rate limiter is in-memory**: correct for one API process; use Redis when scaling out. * *
Source: `docs/SECURITY.md:159-184`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0101 — Setup (Linux, macOS, Windows): **Verified on Linux (Ubuntu 24.04) only.** The macOS and Windows commands are the equivalent ones b
Source: `docs/SETUP.md:3-3`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0102 — Prerequisites: * Python 3.12 (`uv` recommended), Node.js 22 (>= 22.12), PostgreSQL 16+ (the suite passed on 18.6; CI is configured
Source: `docs/SETUP.md:6-7`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0103 — PostgreSQL without Docker or root: | OS | How | |---|---| | Linux / macOS | `conda create -n rs-pg -c conda-forge postgresql -y`, 
Source: `docs/SETUP.md:10-13`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0104 — PostgreSQL without Docker or root: Use a **localhost-only** cluster with a throwaway password for development. Never reuse it.
Source: `docs/SETUP.md:15-15`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0105 — RoadSentinel – Threat model (STRIDE): Scope: the security foundation in this repository (API, database, evidence store, PWA, rever
Source: `docs/THREAT_MODEL.md:3-4`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0106 — Assets: | Asset | Why it matters | |---|---| | Evidence (clips/keyframes, original and redacted) | Personal data (faces, plates), 
Source: `docs/THREAT_MODEL.md:8-16`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0107 — Actors: * **Operator / patrol / admin / auditor** of a police unit (tenant) – legitimate, partly trusted. * **Malicious or curious
Source: `docs/THREAT_MODEL.md:20-25`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0108 — Trust boundaries: 1. Internet ↔ Caddy (TLS termination). 2. Caddy ↔ API (internal network). 3. API ↔ DB (internal `db` network, re
Source: `docs/THREAT_MODEL.md:36-38`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0109 — Threats and mitigations: Phase numbers refer to the implementation phases (0 skeleton, 1 authentication, 2 authorization & isolati
Source: `docs/THREAT_MODEL.md:42-43`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0110 — S – Spoofing: | Threat | Mitigation | Phase | |---|---|---| | Password guessing / credential stuffing | Argon2id, min length + com
Source: `docs/THREAT_MODEL.md:47-55`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0111 — T – Tampering: | Threat | Mitigation | Phase | |---|---|---| | CSRF on state-changing endpoints | SameSite=Strict + double-submit 
Source: `docs/THREAT_MODEL.md:59-68`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0112 — R – Repudiation: | Threat | Mitigation | Phase | |---|---|---| | "I never viewed that evidence" | Every signed URL issuance and ev
Source: `docs/THREAT_MODEL.md:72-77`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0113 — I – Information disclosure: | Threat | Mitigation | Phase | |---|---|---| | Cross-tenant data access (IDOR) | RLS FORCE + restrict
Source: `docs/THREAT_MODEL.md:81-93`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0114 — D – Denial of service: | Threat | Mitigation | Phase | |---|---|---| | Login/MFA flooding | Rate limits (429 + Retry-After) | 1 | 
Source: `docs/THREAT_MODEL.md:97-102`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0115 — D – Denial of service: Residual: no WAF / global DDoS protection (see roadmap).
Source: `docs/THREAT_MODEL.md:104-104`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0116 — E – Elevation of privilege: | Threat | Mitigation | Phase | |---|---|---| | Operator performs admin actions | Central permission m
Source: `docs/THREAT_MODEL.md:108-115`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0117 — Residual risks: See "Known limitations" in [SECURITY.md](../SECURITY.md) and the roadmap in [ARCHITECTURE_TARGET.md](ARCHITECTURE_TAR
Source: `docs/THREAT_MODEL.md:119-120`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0118 — Romanian HLS adapter status — 2026-11-07: The configured-source layer now recognizes HLS master playlists, selects variants within
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:5-11`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0119 — 2026-11-07 physical camera availability update: The code now accepts explicit `device:N` UVC input through the existing YOLOX-S ON
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:15-22`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0120 — 2026-11-07 physical camera availability update: Last verified: 2026-11-06 (local CPU run)
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:24-24`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0121 — Runtime and provenance: - Detector: Megvii YOLOX-S COCO, ONNX; official release artifact from the [Megvii YOLOX release](https://g
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:28-32`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0122 — Input and rights: Input was the recorded Wikimedia Commons file [Street traffic.webm](https://commons.wikimedia.org/wiki/File:Stre
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:36-36`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0123 — Reproduction and observed results: Command (camera config was a local temporary test config; no source URL or credentials):
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:40-40`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0124 — Reproduction and observed results: The command completed with exit code 0. It processed 105 sampled frames across 34.9 seconds (so
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:48-48`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0125 — Reproduction and observed results: - 1,085 tracked observations and 67 unique tracks. - Track counts by class: bus 13, car 32, tru
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:50-54`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0126 — Reproduction and observed results: The tracker/class totals and line-crossing measurements are pipeline outputs, not labeled groun
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:56-56`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0127 — Current acceptance boundary: Verified: actual official weights loaded; real vehicle boxes/classes/confidences produced; ByteTrack 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:60-60`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0128 — Local live-replay vertical slice (2026-11-06): The integration test served the licensed clip continuously from a loopback-only MJP
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:64-69`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0129 — Local live-replay vertical slice (2026-11-06): Run from `backend/` (requires the locally approved sample/model, `.venv`, Node 22, 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:71-72`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0130 — Local live-replay vertical slice (2026-11-06): Latest result: **1 passed** (2026-11-06). The loopback source served 10 FPS; the CP
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:80-83`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0131 — Local live-replay vertical slice (2026-11-06): At persistence, latency p50/p95/p99 was 84.49/99.41/103.85 ms and peak RSS was 346.
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:85-89`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0132 — Authenticated annotated frame evidence (2026-11-06): The preview path now publishes redacted, annotated JPEG frames through the ex
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:93-97`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0133 — Authenticated annotated frame evidence (2026-11-06): Bounded real-model E2E command and result:
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:99-99`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0134 — Authenticated annotated frame evidence (2026-11-06): Result: **1 passed**. The browser test waited for successful natural image di
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:108-114`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0135 — Authenticated annotated frame evidence (2026-11-06): At the E2E telemetry snapshot for this run: 63 processed frames, 315 detectio
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:116-119`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0136 — Authenticated annotated frame evidence (2026-11-06): This is one recorded San Francisco scene on one CPU machine. It does not vali
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:121-127`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0137 — Repeat after camera-catalog UI change (2026-11-06): The actual-model full E2E was run again after adding the Romanian read-only di
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:131-131`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0138 — Repeat after camera-catalog UI change (2026-11-06): Exit code 0, **1 passed**. The persisted telemetry snapshot reported 64 proces
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:140-145`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0139 — Repeat after camera-catalog UI change (2026-11-06): The browser image and overlays are preserved locally at `data/vision/evidence/
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:147-151`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0140 — Repeat after camera-catalog UI change (2026-11-06): The final catalog-inclusive browser run passed after correcting its expected c
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:153-158`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0141 — Repeat after camera-catalog UI change (2026-11-06): After moving the catalog module out of the repository's ignored `data/` path, 
Source: `docs/YOLO_REAL_INFERENCE_REPORT.md:160-166`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0142 — 5-minute security demo (for judges): Preparation (before the demo):
Source: `scripts/demo_security.md:3-3`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0143 — 5-minute security demo (for judges): Open https://localhost (trust Caddy's local certificate). The dev password for every seeded a
Source: `scripts/demo_security.md:11-14`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0144 — 5-minute security demo (for judges): Shortcut for the terminal: `alias dc='docker compose --env-file .env -f deploy/docker-compose
Source: `scripts/demo_security.md:16-16`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0145 — 5-minute security demo (for judges): ---
Source: `scripts/demo_security.md:18-18`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0146 — 1. Unit B cannot see Unit A (≈ 1 min): 1. Browser A (`operator.a@roadsentinel.local`): open any alert, copy its URL (`/alerts/<id>
Source: `scripts/demo_security.md:22-29`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0147 — 2. Audit tampering is detected (≈ 1 min): 1. `auditor.a` → Audit → **Verify integrity** → ✔ chain intact. 2. Terminal: `dc run --r
Source: `scripts/demo_security.md:33-38`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0148 — 3. Unblur needs a second person, and it is audited (≈ 1.5 min): 1. `operator.a`: open a critical alert → evidence is **blurred**, 
Source: `scripts/demo_security.md:42-50`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0149 — 4. The database only holds ciphertext (≈ 45 s): Point out the `F1` (field) and `RSE1` (file) headers followed by random bytes: AES
Source: `scripts/demo_security.md:60-62`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### REQ-0150 — 5. Installable PWA with generic push (≈ 45 s): 1. In Chrome/Edge: install icon in the address bar → RoadSentinel opens as a standa
Source: `scripts/demo_security.md:66-73`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `See ARCHITECTURE_AND_CONTRACT_MAP.md`. Test/evidence: `See TEST_EXECUTION_LEDGER.md`; `No direct current-run acceptance proof`.
Next acceptance: Execute concrete acceptance behavior; historical documentation is not current-run evidence. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A01 — Product/interfaces
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `frontend/src/App.tsx;secure-pwa/src;backend/app/main.py`. Test/evidence: `backend/tests/test_contract_api.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Secure backend authoritative; legacy architecture table contradicts current architecture. PWA browser not exercised.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A02 — Detection/tracking
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `roadsentinel/detector.py;roadsentinel/pipeline.py;models/registry.json`. Test/evidence: `backend/tests/test_mission_vertical.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Actual inference on licensed-derived synthetic frozen fixture; no incident accuracy measurement.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A03 — Adapters/rights
Source: `README.md + linked specs:1-218`. Category: **TESTED SYNTHETIC ONLY**; priority P0.
Owner: `roadsentinel/sources.py;roadsentinel/consent.py;roadsentinel/replay.py`. Test/evidence: `tests/test_sources.py;tests/test_consent.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Local adapters tested. External rights not established; no remote media fetched.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A04 — Geometry/calibration
Source: `README.md + linked specs:1-218`. Category: **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/geometry.py;backend/app/services/camera_config.py`. Test/evidence: `tests/test_rules_rates.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Synthetic geometry is not a calibrated real road. No speed certification.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A05 — Rule thresholds
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `roadsentinel/rules.py;backend/app/services/offline_analysis.py`. Test/evidence: `tests/test_rules.py;tests/test_mission_vertical.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Frozen-frame model tracks produce nine candidates; this is not street incident validation.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A06 — Critical event types
Source: `README.md + linked specs:1-218`. Category: **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/rules.py;backend/app/core/catalog.py`. Test/evidence: `tests/test_rules.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Wrong way/pedestrian/crash/object production precision and recall remain unverified.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A07 — High event types
Source: `README.md + linked specs:1-218`. Category: **TESTED SYNTHETIC ONLY**; priority P1.
Owner: `roadsentinel/rules.py`. Test/evidence: `tests/test_rules.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Stopped/offline candidate bridge implemented. Physical speed and near miss remain unvalidated.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A08 — Medium event types
Source: `README.md + linked specs:1-218`. Category: **TESTED SYNTHETIC ONLY**; priority P2.
Owner: `roadsentinel/rules.py;roadsentinel/rates.py`. Test/evidence: `tests/test_rules_rates.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Sampling constraints matter; no operational validation.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A09 — Information/offline rules
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/services/offline_analysis.py`. Test/evidence: `backend/tests/test_mission_vertical.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Line counts stay analytics; only obstruction/queue eligible for explicit recorded review.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A10 — Evidence assembly
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/services/offline_promotion.py;backend/app/services/evidence.py;roadsentinel/pipeline.py`. Test/evidence: `backend/tests/test_mission_vertical.py;backend/tests/test_evidence_integrity.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: HTTP media + encryption verified for recorded fixture; crash orphan cleanup remains open.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A11 — Signed ingestion
Source: `README.md + linked specs:1-218`. Category: **IMPLEMENTED UNVERIFIED**; priority P0.
Owner: `roadsentinel/sink.py;backend/app/api/ingest.py;backend/app/services/ingest_auth.py`. Test/evidence: `backend/tests/test_ingest_auth.py;backend/tests/test_ingest_idempotency.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Use final execution ledger for test-level outcomes; managed fencing newly added.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A12 — Operator queue
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `frontend/src/store/data.ts;backend/app/api/contract.py`. Test/evidence: `backend/tests/test_contract_api.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: API exercised; new UI source labels compile. Full candidate promotion browser journey not verified.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A13 — Decisions/patrol
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/contract.py;backend/app/api/patrol.py`. Test/evidence: `backend/tests/test_mission_vertical.py;backend/tests/test_patrol_stats.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Actual HTTP reject tested for recorded fixture. Signs/enforcement remain action labels.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A14 — Archive/saved searches
Source: `README.md + linked specs:1-218`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `backend/app/services/search.py;backend/app/api/contract.py`. Test/evidence: `backend/tests/test_pagination.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Tenant-filtered parser and keyset paging exist; browser retrieval of new candidate not yet demonstrated.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A15 — Investigation/export
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py`. Test/evidence: `backend/tests/test_evidence_integrity.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Imported API/UI exist. Approval-to-export manifest verification of promoted incident not proven in this mission.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A16 — Camera administration
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/app/api/camera_control.py;backend/app/services/camera_config.py;frontend/src/components/CameraControlPanel.tsx`. Test/evidence: `backend/tests/test_managed_live_runtime.py`; `vertical-release.log; pipeline-release.log`.
Next acceptance: Managed runtime fixture tests do not prove two-admin UI approval workflow.. Managed approval is fixture-owned; outages, reconfiguration, export and live browser remain unverified.

### A17 — Clients/accessibility
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P2.
Owner: `frontend/src;secure-pwa/src`. Test/evidence: `frontend/src/store/auth.test.ts`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Frontend build and 15 tests pass. PWA browser and accessibility acceptance remain unverified.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A18 — Authentication/MFA/RLS
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/app/services/auth.py;backend/app/db.py;backend/app/bootstrap.py;backend/app/services/seed.py`. Test/evidence: `backend/tests/test_auth.py;backend/tests/test_seed.py;backend/tests/test_isolation.py`; `backend-release.log; TEST_EXECUTION_LEDGER.md`.
Next acceptance: Disposable DB authenticates with mandatory MFA. Existing integration owner BYPASSRLS=false remains blocker; existing DB untouched.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A19 — Keys/audit
Source: `README.md + linked specs:1-218`. Category: **IMPLEMENTED UNVERIFIED**; priority P1.
Owner: `backend/app/core/crypto.py;backend/app/core/audit.py;backend/app/core/audit_anchor.py`. Test/evidence: `backend/tests/test_crypto.py;backend/tests/test_audit.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: AES-GCM and hash chain exist. Local checkpoint is not independent external custody.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A20 — Privacy/legal
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `roadsentinel/redaction.py;roadsentinel/consent.py;backend/app/services/retention.py`. Test/evidence: `tests/test_privacy_defaults.py;backend/tests/test_retention.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Heuristic redaction is not anonymization. No legal/DPIA sign-off or enforcement integration.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A21 — Model governance
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `roadsentinel/models.py;models/registry.json;training`. Test/evidence: `tests/test_models.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Stock model hash known; external configurable model path added. No representative evaluated activation.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A22 — Real accuracy
Source: `README.md + linked specs:1-218`. Category: **EXTERNALLY BLOCKED**; priority P1.
Owner: `docs/LIMITS.md;models/reports`. Test/evidence: `tests/test_evaluation.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: No labeled representative data/approved target metrics. Counts not ground truth.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A23 — Offline jobs
Source: `README.md + linked specs:1-218`. Category: **VERIFIED REAL INPUT PARTIAL**; priority P0.
Owner: `backend/app/api/offline_video.py;backend/app/services/offline_analysis.py;backend/app/models/offline_video.py`. Test/evidence: `backend/tests/test_mission_vertical.py;backend/tests/test_offline_video_authz.py`; `vertical-release.log; screenshots/recorded-review.png`.
Next acceptance: Upload/crop/job/candidates/media/review tested over HTTP. Restart/browser/retention matrix incomplete.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A24 — Live worker
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `roadsentinel/remote_config.py;roadsentinel/live.py;roadsentinel/pipeline.py;backend/app/api/camera_worker.py`. Test/evidence: `backend/tests/test_managed_live_runtime.py;tests/test_remote_config.py`; `vertical-release.log; pipeline-release.log`.
Next acceptance: Actual latest outcomes in managed-live and backend-final logs. Do not treat test-owned approval rows as admin acceptance.. Managed approval is fixture-owned; outages, reconfiguration, export and live browser remain unverified.

### A25 — Contracts
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/app/schemas/contract.py;frontend/src/lib/adapters.ts;API.md`. Test/evidence: `backend/tests/test_contract_api.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Legacy/secure contract coexist. New origin stored in details; labels added conservatively, unknown source disclosed.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A26 — Migrations/seed
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/alembic;backend/app/services/seed.py`. Test/evidence: `backend/tests/test_isolation.py;backend/tests/test_seed.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Fresh cluster tested through 0021. Existing integration not migrated or backed up during mission.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A27 — Install/readiness
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `deploy/docker-compose.yml;frontend/vite.config.ts;backend/app/api/health.py`. Test/evidence: `backend/tests/test_ops_and_authz.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Current proxy correct. Compose not executed. Readiness does not mean a camera is online.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A28 — Testing/CI
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `backend/tests;tests;frontend/e2e;.github/workflows/ci.yml`. Test/evidence: `TEST_EXECUTION_LEDGER.md`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Local execution evidence only; no GitHub CI execution or push.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A29 — Legacy boundaries
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `roadsentinel/server.py;web;README.md`. Test/evidence: `tests/test_api.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Legacy batch destructive semantics remain isolated; not used for mission E2E.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A30 — Optional AI/telemetry
Source: `README.md + linked specs:1-218`. Category: **IMPLEMENTED UNVERIFIED**; priority P2.
Owner: `roadsentinel/vlm.py;roadsentinel/tracking.py`. Test/evidence: `tests/test_privacy_defaults.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: External VLM and W&B not enabled in mission; no external data transmission test.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A31 — Romanian source catalog
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `cameras/romanian-source-registry.json;backend/app/services/camera_discovery.py`. Test/evidence: `backend/tests/test_camera_discovery.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Catalog restored from original source. Candidates remain ingestion-disabled; no rights or availability claim.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A32 — Optional scope
Source: `README.md + linked specs:1-218`. Category: **NOT APPLICABLE / OPTIONAL**; priority P3.
Owner: `docs/LIMITS.md;README.md`. Test/evidence: `not applicable`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Fog/ice/plate/facial/enforcement/SSO not added. No automatic sanctions.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A33 — Reliability/backpressure
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `roadsentinel/live.py;backend/app/services/camera_control.py`. Test/evidence: `tests/test_live.py;backend/tests/test_managed_heartbeat.py`; `vertical-release.log; pipeline-release.log`.
Next acceptance: Critical queue overflow bounded; stale sequences no longer extend lease. Long soak/multi-camera absent.. Managed approval is fixture-owned; outages, reconfiguration, export and live browser remain unverified.

### A34 — Honest presentation
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P1.
Owner: `frontend/src/lib/adapters.ts;frontend/src/pages/VideoAnalysisPage.tsx`. Test/evidence: `frontend/src/store/auth.test.ts`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: RECORDED/LOCAL REPLAY/SYNTHETIC source prefixes. No external live or accuracy badge inferred.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

### A35 — Integrated guarantees
Source: `README.md + linked specs:1-218`. Category: **PARTIAL**; priority P0.
Owner: `backend/app/models/camera_control.py;backend/app/models/casework.py;backend/app/models/investigation.py`. Test/evidence: `backend/tests/test_isolation.py`; `TEST_EXECUTION_LEDGER.md`.
Next acceptance: Tenant table inventory now derived after all models imported. Imported case/control paths need more end-to-end coverage.. Coverage inventory; unverified behavior is not promoted to passing status by code presence.

## Unclosed P0 gates

Existing integration auth; full first-promotion browser journey from upload; export revocation/tamper/hold/browser cases; crash/restart durability and orphan cleanup; longer stream recovery/soak; approved revision change/rollback; multi-camera bounds; existing-data migration backup/restore validation. External live is blocked by missing documented rights. No real-world accuracy, legal admissibility or production-readiness claim is made.
## Additional executed acceptance: export and source recovery

After the earlier checkpoint, real HTTP case export uncovered two integration defects: CaseError/ExportError were not registered with the application error mapper (not-ready export answered 500), and approval API approve/deny/revoke did not call the existing export-job transition hook. app.main now registers the existing domain response mapping; app.api.unblur connects on_approval_decided. No policy was bypassed. The expanded real-model test adds a case observation, records the fixture's explicit CC BY 3.0 license through the existing admin grant API, requests export, observes not-ready 409, obtains independent admin approval, generates/downloads the encrypted package through signed authenticated access, and verifies the canonical manifest digest and all member hashes using verify_package. Package remains unsigned: hash integrity is not independent legal custody. **14 passed in 17.29 s** with the approvals suite (case-export-release.log).

The managed test now forcibly interrupts only sockets belonging to its controlled replay server and temporarily refuses reconnection. It observes authoritative reconnecting health, expiry of stale preview (404), restoration of actual frames and healthy state, then stops the worker on disable. **1 passed in 14.70 s** (managed-recovery.log). This does not establish external-live availability or multi-camera capacity. Approved configuration state is still fixture-created; actual two-admin UI activation and revision change remain unverified.

The full original-suite checkpoint was 419 passed + 2 skipped; backend-final-proof.log is the subsequent full run including these added assertions. Consult its final summary before using it as release evidence. Docs checker now works without Git metadata; snapshot omissions and quoted relative links were corrected, with 0 broken links in 85 Markdown files at that checkpoint. README source snapshot is README_BEFORE_SOURCE.txt.

## Final checked release snapshot

`backend-final-proof.log`: **419 passed, 2 skipped, 15 warnings in 135.04 s**, including the added real-model/HTTP/Chromium/export/recovery assertions. `dedicated-runtime.log`: **5 passed in 27.91 s** in `/tmp/rsint-venv` (independent of original venv, OpenCV 4.12.0.88). `requirements.integration-test.txt` records the reproduced dependency set. `pipeline-release.log`: **91 passed**; React **15**, PWA **9**, both typechecks/builds passed. Core changed services Ruff passed; original/imported whole-tree style debt remains unclaimed. `docs-check-final.log`: **0 broken links in 85 Markdown files**.

Full case export and controlled source recovery are now passed local acceptance components, as described in the preceding appendix. Remaining P0 acceptance is actual existing-integration authentication/rollout, complete browser first-creation and case/export interaction, retained-state service restart/crash cleanup, real approved-revision UI change/rollback, multi-camera bounds, broader permission/grant/tamper/hold cases and representative moving incident positives/negatives. These prevent marking either complete against the full mission. External live remains BLOCKED pending rights.

Final original-source recheck: 307 primary and 301 review source files unchanged relative to the recorded late baseline. No original worktree mutation command, Git commit/init/push/remote mutation, or original database write was performed. Existing integration DB and protected credentials were not modified. Source changes have not been restarted into the preserved integration API process.
