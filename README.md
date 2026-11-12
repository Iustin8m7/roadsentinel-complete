# RoadSentinel

AI traffic-camera monitoring that sends evidence-backed alerts to police operators and patrols. Hackathon project / prototype: see [docs/LIMITS.md](docs/LIMITS.md) for what is and is not validated.

## What it does

1. **Camera processing.** A YOLO detector with tracking can process configured camera sources and compute speed, hard braking, lane changes, and following distance. The code path exists, but the model has not been validated on representative authorized footage; see [docs/LIMITS.md](docs/LIMITS.md).
2. **Configurable rules.** Each police unit defines zones (emergency lane, crosswalk, one-way street) and thresholds (speed, dwell time). A matched rule produces a typed, explainable, repeatable event.
3. **VLM verification (optional, off by default).** When enabled (`RS_EXTERNAL_AI=frames` + API key; frames then leave the server) a vision-language model can add a description. It is not part of the default product and nothing in the UI claims an AI confirmation.
4. **Operator alert.** Alerts reach the dispatch dashboard and the patrol app, sorted by severity.

## Alert types

| Priority | Event |
|---|---|
| Critical | Wrong-way driving, pedestrian on road, object on roadway |
| High, human review required | Possible collision interaction (calibrated two-vehicle approach and sustained stop; contact unproven) |
| High | Very high speed, vehicle stopped in emergency lane / on the road, near-miss |
| Medium | Hard braking, tailgating, dangerous lane changes |
| Info | Congestion |

Definitions and sampling-rate limits: [docs/RULES.md](docs/RULES.md). Behavior rules were historically tested on synthetic tracks. The integration now also exercises recorded obstruction candidates using real YOLOX/ByteTrack detections on explicitly synthetic frozen licensed imagery; this does not validate real-world incident accuracy. **Not implemented:** road conditions (fog, ice).

## Alert flow

- The system creates a review candidate with the rule, source time and protected evidence. It attaches a map location only when approved source or filming-location provenance exists; unknown locations remain unlocated.
- The operator reviews the case and confirms or rejects it.
- On confirmation the operator records the action (dispatch patrol, warning sign, enforcement). Only *patrol assignment with status updates* has a workflow behind it; signs and enforcement are labels in the audit log.
- Everything goes to an audit log: who saw it, what they decided, when.

## Archive search

Investigators can use a Romanian/English keyword parser to create structured archive filters and save named searches to their own account. Saved searches retain normalized filters, not the original query text. This is not semantic natural-language understanding; review the query interpretation before relying on the results.

## Safeguards and limits

- A human makes the decision. The system alerts and prepares evidence; it never issues fines automatically.
- Video-measured speed is unvalidated and camera-dependent; treat it as orientative triage only. Fines require metrologically certified equipment.
- No facial recognition or persistent person identity tracking. Short-lived scene tracks may support configured pedestrian safety rules; they do not identify a person.
- GDPR and the Police Directive (EU 2016/680) require a legal basis, limited purpose, role-based access and short retention. This repository provides role-based access, tenant isolation, audited access, configurable retention with legal hold and heuristic redaction **on by default**. It makes **no compliance claim**: no DPIA, legal basis or retention schedule has been approved (docs/LIMITS.md).
- Field validation: accuracy must be measured on real cameras at night, in rain, and in dense traffic before operational use.

## Benefits

Faster response, fewer false alarms for operators, evidence prepared automatically, and statistics on where interventions are needed (speed cameras, traffic lights, patrols).

## Architecture

```text
camera → pipeline (roadsentinel/) → secure backend (backend/) → police UI (frontend/)
                                      │                    └→ secure PWA (secure-pwa/)
                                      └→ PostgreSQL + encrypted evidence
```

The secure backend owns sessions, MFA (mandatory), tenant isolation, audit and evidence access.
`frontend/` is the separate operator client, `secure-pwa/` is the bundled patrol/auditor/admin client,
and Compose currently serves the PWA at `https://localhost`; run the operator client separately.
Both supported clients use the secure backend's compatibility contract. `web/` and
`roadsentinel/server.py` are deprecated legacy demo code and must not be used for operational data.
The root `Dockerfile` and `railway.json` still describe that legacy demo. See [API.md](API.md),
[HANDOFF.md](HANDOFF.md) and [docs/SETUP.md](docs/SETUP.md).

### Start the secure backend and PWA locally

From the repository root, with Docker Compose v2.20+ and Python 3.12:

```bash
python3 scripts/gen_dev_secrets.py
docker compose --env-file .env -f deploy/docker-compose.yml up --build
```

*(The Docker stack was not built or run when this branch was prepared; the supported verified path is [docs/SETUP.md](docs/SETUP.md).)* Open **https://localhost** and trust Caddy's local development certificate. Compose starts
PostgreSQL 16, migrations, FastAPI (`backend/`), the secure PWA (`secure-pwa/`, service name
`frontend`) and Caddy. Seed accounts in a second terminal:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml exec backend python scripts/seed.py
```

Use `RS_SEED_PASSWORD` from the generated, git-ignored `.env`. First login requires TOTP
enrollment (mandatory); new users come from invitations. Never use the seeded accounts in production. For a laptop demo with synthetic data run `python scripts/demo.py`.

For host development, the backend entrypoint is `uvicorn app.main:create_app --factory`
from `backend/` with dependencies in `requirements.lock`. It requires a migrated PostgreSQL
database, restricted runtime role and the `RS_*` settings described in [security docs](docs/SECURITY.md).
The Compose setup above supplies these automatically and keeps the database internal.

### Start each interface in development

Use Node.js 22 (vitest 5 needs >= 22.12). Run each command from the repository root in a separate terminal:

```bash
# Police operator UI (real backend; VITE_USE_MOCKS=1 gives labelled demo data)
cd frontend
npm ci
npm run dev -- --port 5173
```

```bash
# Secure PWA: host development API on http://127.0.0.1:8000
cd secure-pwa
npm ci
npm run dev -- --port 5174
```

The PWA development server serves the UI shell over HTTP. Secure session cookies require
a trusted HTTPS origin: use the Compose-served PWA at https://localhost for the
ready-to-run secure login flow, or configure a trusted TLS proxy for host development.
`secure-pwa/vite.config.ts` proxies `/api` to port 8000 for a separately configured host
backend; Compose does not publish that port.

### Start the detector

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
scripts/download_data.sh
.venv/bin/python -m roadsentinel.pipeline cameras/demo-highway.yaml --no-wandb --max-seconds 10
```

For secure remote ingestion create a tenant service account and register its camera, then:

```bash
export RS_API_URL=https://localhost
export RS_INGEST_KEY_ID='<service-key-id>'
export RS_INGEST_SECRET='<secret-shown-once>'
.venv/bin/python -m roadsentinel.live cameras/demo-highway.yaml        # supervised, restarts with backoff
# or one camera in the foreground: .venv/bin/python -m roadsentinel.pipeline cameras/demo-highway.yaml --live --no-wandb
```

Trust the local TLS CA on the pipeline machine; do not disable certificate validation. The endpoint is
`POST /api/ingest/events`, HMAC-SHA256 over the exact multipart bytes. Redaction is **on** (`full`); to store
unblurred frames you must set `RS_REDACTION=off` **and** `RS_ALLOW_UNREDACTED=1`, and the evidence is then labelled
FĂRĂ REDACTARE. A camera whose `video` is a network URL refuses to run until `source_consent` is filled in its yaml.
Detector weights come from the model registry: [docs/MODEL_INTEGRATION.md](docs/MODEL_INTEGRATION.md).

### Legacy standalone demo

`roadsentinel/server.py` and `web/` form a separate demo with a local event store, not the
secure platform. Leave `RS_API_URL` unset and run `scripts/run_demo.sh` after installing
the detector dependencies above; it downloads clips and serves http://localhost:8000.
For only its API/dashboard on this baseline, run `.venv/bin/uvicorn roadsentinel.server:app`.
The legacy `web/` code is frozen and is not part of the supported secure platform.
Batch processing in this legacy demo replaces the camera's events, decisions and audit
trail. Keep it separate from operational data. Optional VLM/search credentials and the
legacy Railway deployment settings are described in [API.md](API.md); the root Dockerfile
and `railway.json` deploy this legacy server, not `backend/`.

## How the prototype is built

| Step | Code | What it does |
|---|---|---|
| Detection + tracking | `roadsentinel/pipeline.py`, `roadsentinel/detector.py` | YOLOX-S ONNX + ByteTrack; CPU inference and sampled-frame replay are supported. The checked local model produced real vehicle boxes, class labels, tracks and line counts on licensed recorded traffic footage; see [the inference report](docs/YOLO_REAL_INFERENCE_REPORT.md). Do not interpret this as external live-camera or incident-accuracy validation. |
| Speed | `roadsentinel/geometry.py`, `rules.py` | Homography from 4 road points to metres; speed = least-squares slope over 1 s |
| Rules | `roadsentinel/rules.py`, `cameras/*.yaml` | Zones, thresholds and enabled rules per camera; each alert records the exact threshold crossed |
| Evidence | `backend/app/services/evidence.py`, `offline_promotion.py`, `roadsentinel/pipeline.py` | Tenant-encrypted protected evidence in the secure backend; bounded clips and redacted keyframes. Pipeline staging is separate from authoritative encrypted storage. |
| VLM check (off by default) | `roadsentinel/vlm.py` | Optional: Claude looks at the clip frames and writes a one-line Romanian description; never enabled implicitly |
| Search | `backend/app/services/search.py` | Keyword parser (Romanian/English) → structured filter → SQL; not language understanding |
| API + dashboard | `backend/app/api/`, `frontend/`, `secure-pwa/` | Secure login/MFA, tenant-scoped alert queue, review, audit and HMAC ingestion. `roadsentinel/server.py` and `web/` remain legacy only. |
| Storage | `roadsentinel/store.py`, `media.py`, `sink.py` | SQLAlchemy (SQLite or Postgres), media on disk or S3 bucket, local or remote ingestion |
| Experiment log | `roadsentinel/tracking.py` | Optional W&B integration; mission runs use `--no-wandb`. Review outbound data policy before enabling external telemetry. |

Demo data: Roboflow `supervision` sample clips (`scripts/download_data.sh`). The urban camera's calibration is
approximate, so only rules that don't need an exact speed are enabled there.

## Security foundation

Security details: [docs/SECURITY.md](docs/SECURITY.md) ·
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) ·
[docs/ARCHITECTURE_TARGET.md](docs/ARCHITECTURE_TARGET.md) (roadmap) ·
[demo script](scripts/demo_security.md).

### Development logins (DEV ONLY)

New development accounts use `RS_SEED_PASSWORD` from the local environment. Repeated seeding
preserves existing passwords, roles and MFA. Every new account must enroll TOTP on first login
(QR code + 8 recovery codes). The verified integrated5175/8003 login and private credential
locations are documented in [the operator quickstart](docs/audits/OPERATOR_DEMO_QUICKSTART.md).

| Tenant | Accounts |
|---|---|
| RoadSentinel Platform | `sysadmin@roadsentinel.local` (system admin: creates police units) |
| Unit A – Highway Patrol North | `admin.a@`, `operator.a@`, `patrol.a@`, `auditor.a@roadsentinel.local` |
| Unit B – City Traffic South | `admin.b@`, `operator.b@`, `patrol.b@`, `auditor.b@roadsentinel.local` |

New accounts are created only through invitations (Users API, tenant admin) – there is no
public registration.

### Useful commands

```bash
alias dc='docker compose --env-file .env -f deploy/docker-compose.yml'
dc exec backend python -m app.cli rotate-tenant-key --tenant unit-a   # new DEK version
dc exec backend python -m app.cli verify-audit --tenant unit-a        # check the hash chain
dc run --rm migrate python scripts/audit_tamper_demo.py --tenant unit-a
dc exec backend python -m app.cli demo-alert --tenant unit-a          # generic push demo
```

### Run the tests

```bash
# Backend: needs a PostgreSQL 16 superuser URL; creates a throwaway database "rs_test"
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.lock pytest httpx ruff black mypy
export RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/postgres
pytest                     # isolation, encryption, audit, four-eyes, auth, headers
ruff check app alembic tests && black --check app alembic tests && mypy
```

In a new terminal, from the repository root:

```bash
# Secure PWA
cd secure-pwa
npm ci && npm run lint && npm run typecheck && npm test && npm run build
```

CI (`.github/workflows/ci.yml`) defines jobs for the backend (real PostgreSQL), `secure-pwa/`, `frontend/`, the pipeline tests, repo checks (secret scan, docs links), gitleaks and a Docker stack smoke test. **This branch's CI has not been run on GitHub** (see docs/FINAL_STATUS.md for what was run locally). Deploys are manual and gated on a green run. CodeQL runs separately in
`.github/workflows/codeql.yml` and retains SARIF as artifacts; code scanning upload is
disabled for compatibility with this private repository's settings.

## Integrated recorded review and managed workers

Recorded analysis remains at `/app/analiza-video`. Eligible completed obstruction/queue candidates can be explicitly submitted by an authorized operator with a review reason. They become canonical pending alerts with `origin=recorded_upload`, model/run/PTS provenance and encrypted redacted evidence; they are never silently presented as current live incidents. Line counts stay analytics. See [Feature 1](docs/implementation/FEATURE_01_AI_INCIDENT_TO_OPERATOR.md).

Managed workers reuse the existing supervised pipeline and HMAC contract. They acquire a lease before source access, apply approved geometry/rules/counting lines, check model hash and reference dimensions, acknowledge the revision, and stop on lease/permission/revision changes. Local network replay requires an explicit loopback source and is labeled LOCAL RECORDED REPLAY. Fresh Chromium tests cover configuration approval, Start, moving inference, source outage/recovery, revision changes, rollback and disable. Source-rights setup still requires admin APIs, geometry editing is JSON, and multi-camera/field acceptance remains partial; external live rights have not been established. See [Feature 2](docs/implementation/FEATURE_02_AUTHORIZED_LIVE_CAMERA.md) and its [browser evidence](docs/audits/FEATURE_2_REAL_BROWSER_E2E.md).

Historical execution evidence and remaining gates: [post-integration audit](docs/audits/POST_INTEGRATION_README_AUDIT_AFTER.md), [test ledger](docs/audits/TEST_EXECUTION_LEDGER.md), [ranked backlog](docs/audits/REMAINING_FEATURES_MASTER_BACKLOG.md). For the local integration frontend use `RS_API_ORIGIN=http://127.0.0.1:8003` explicitly; the generic development default remains port 8000. The integration database has since been upgraded additively through revision 0028 after backup and isolated restore rehearsal; earlier revision 0022 reports are historical. Credentials remain in the protected local file. See the [current browser handoff](docs/audits/FINAL_BROWSER_HANDOFF.md) for prior journeys and [the notification implementation note](docs/completion/NOTIFICATIONS_20261112.md) for this revision.


## Incremental GitHub integration (47e3e85)

The existing integration now includes the reviewed main delta through `47e3e85`: visual camera/source-rights configuration using the existing approval and worker ACK flow, authorized recording playback/seeking from camera tiles, exact camera archive history, public Romanian prototype landing, reviewed-state/summary/error improvements, real-speed evidence playback and an authorized loaded-data print report. YOLOX-S ONNX/ByteTrack, mandatory MFA, tenant RLS, encrypted evidence and independent export approval remain authoritative. Demo curation cannot modify real-backend review state.

See the [incremental verdict and evidence](docs/audits/git_incremental_20261111T003730Z/GITHUB_INTEGRATION_FINAL_VERDICT.md), [60-file/33-commit decisions](docs/audits/git_incremental_20261111T003730Z/GITHUB_COMMIT_AND_FILE_COVERAGE.csv) and [browser/run instructions](docs/audits/git_incremental_20261111T003730Z/GITHUB_INTEGRATION_BROWSER_HANDOFF.md). Controlled moving footage and explicitly synthetic incident stimuli validate workflows; they do not establish real-world incident accuracy, certified speed, external source rights or production readiness. No migration or reseed of the existing integration database is required for this port.

## Romania incident map (in progress)

Authorized users with `map:read` can open **Harta incidentelor** at `/app/harta-incidentelor`. The map uses confirmed persisted location revisions; incidents without a confirmed location remain in the list without a point. On **Analiză video**, select a recording and choose an approved camera, mark a filming point on the map, or retain an unknown location. Video analysis itself cannot determine GPS coordinates. A camera position is a source anchor, not the precise collision point. See [the current implementation and test ledger](docs/audits/ROMANIA_INCIDENT_MAP_FINAL_HANDOFF.md) before operational use.

## In-app incident notifications (prototype)

The secure operator UI now has a persisted bell/inbox with per-user read, acknowledge and
dismiss state. New non-synthetic candidates, decisions and approved incident-location
revisions append a tenant-scoped notification event in the same database transaction as
the incident change. An authenticated SSE stream replays missed events and the open map
refreshes on delivery; the map also polls periodically as a recovery path. Recorded
footage and manual entries are labeled by source. Synthetic fixtures do not enter the
operational inbox. Browser Notification API and background PWA push are separate
capabilities and are not claimed by this in-app flow. See [API.md](API.md) and
[implementation evidence](docs/completion/NOTIFICATIONS_20261112.md). This is a local
prototype; representative field accuracy and authorized external live-camera activation
remain unvalidated.
