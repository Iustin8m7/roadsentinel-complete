# Final status of `release/ready`

Branch `release/ready` (from `main` a2c870d, plus the `design/wow` redesign merged). `main`, `design/pro-ui` and `design/wow` are untouched. Nothing was pushed, fetched or opened on GitHub. Date of the runs: 2026-11-05.

## Gates, as actually run
Environment: Linux, Node 22.23.4 (conda `rs-node22`), Python 3.12 venv, PostgreSQL **18.6** (conda `rs-pg`, localhost; CI is configured for 16.10: deviation), Chromium for Playwright. No Docker.

| Gate | Result |
|---|---|
| Backend `pytest` (real PostgreSQL, RLS, triggers) | **392 passed** in 77 s |
| Backend `ruff` / `black --check` / `mypy` | clean / 103 files unchanged / no issues in 69 files |
| Root tests (rules, alert gate, live, models, evaluation, calibration, consent, redaction, legacy API) | **128 passed, 2 skipped** (the 2 need `ultralytics`); `ruff` clean |
| `frontend/` | `tsc -b` ok · eslint 0 errors · vitest **11/11** · build: entry JS 414.15 kB (133.29 kB gzip), CSS 66.02 kB (12.72 gzip), lazy `LivePlayer` 398.85 kB (only for the opt-in external stream) |
| `secure-pwa/` | eslint + prettier ok · typecheck ok · vitest **9/9** · build: JS 315.77 kB (97.82 gzip), CSS 17.57 kB, precache 16 entries 378.38 KiB |
| Playwright walk `frontend/` (mock + real-API stubs, admin/operator, light/dark, desktop/mobile, axe, console errors, external requests) served with the strict CSP | **0 failures** (164 s) |
| Playwright walk `secure-pwa/` (every route incl. /admin, light/dark, desktop/mobile, axe, confirm dialogs, MFA enrollment) strict CSP | **0 failures** |
| `npm audit --omit=dev` (both apps) | 0 vulnerabilities (queries the npm registry) |
| `scripts/scan_secrets.py` working tree | 0 findings. History: 15 findings, all the old demo-password literal; no key/token patterns |
| `scripts/check_docs.py` | 0 broken links in 50 markdown files |
| Backup → restore on local PostgreSQL | counts equal, audit head hash equal, runtime role works (docs/OPERATIONS.md) |
| Authorization matrix + hostile-input test over every discovered route (> 60 routes, > 200 requests) | pass |

## Measured performance (method in docs/LIMITS.md; local, loopback, 1 uvicorn worker)
`scripts/measure_latency.py`, 30–40 signed events, 1.37 s apart: ingest request p50 37–42 ms, p95 52–56 ms. Event-to-screen via SSE: 1 viewer p50 555 / p95 972 ms (n=40); 21 viewers p50 567 / p95 989 ms; 51 viewers p50 512 / p95 930 ms; 0 events missed; API RSS 113 MB. The delay is the 1 s SSE poll. Not a production or WAN measurement.

## What was implemented (see docs/IMPLEMENTATION_PROGRESS.md)
* **P0**: mandatory MFA restored (+ guarded demo exemption) · no default credentials · evidence `has_original` + honest redaction labels (full/heads_only/off/unknown) · redaction on by default in the pipeline · manual, CI-gated deploy · CI jobs for every app · strict CSP on the Railway gateway (non-root) · design/wow merged · idle/absolute session limits actually enforced.
* **P1/P2**: low-fps rule mode with capabilities computed from the measured fps · near-miss, object-on-roadway, stationary-after-impact crash · alert gate (dedupe/cooldown/rate) · idempotent ingestion · live reader/supervisor/bounded uploads · public-stream consent gate · model registry, install/activate/rollback, evaluation harness with leakage refusal, manifests and dataset checker · calibration tool · labelling guide and data card.
* **P1 features**: four-eyes account recovery, own password change, session revocation, break-glass CLI · retention (policy, legal hold, dry-run, audited purge) · patrol workflow (assign, status) · camera edit/disable · measured response-time statistics · UI for these (secure PWA admin, patrol panel, stats panel).
* **Ops**: readiness, token-guarded metrics, per-tenant ops status, backup/restore scripts, latency tool, OPERATIONS/LIMITS/SETUP/PRESENTATION docs, one-command demo.

## NOT verified (do not claim)
* **GitHub CI** (none of the workflows ran), **Docker** images/compose/stack, **Railway** (deploy, env vars, volume/S3 persistence), the Dockerfile `USER`/`HEALTHCHECK` change of the gateway.
* **`roadsentinel/pipeline.py` end to end**, any **YOLO inference**, `training/eval.py` on real weights, the VLM, live streams: torch/ultralytics were not installed. The pieces (rules, gate, reader, uploader, supervisor, registry, metrics) are tested with fakes.
* **All detection accuracy, false-alarm rates, night/rain/fog behaviour, speed accuracy**: unmeasured (docs/LIMITS.md).
* PostgreSQL 16 (suite ran on 18.6); Windows and macOS (docs/SETUP.md equivalents are not run); push-notification delivery to a real browser; the CSP header was applied through the preview server and not independently probed with a violating page.
* `pip-audit` was not re-run (needs the network); the audit's `certifi` finding is still open.

## Not done, and why
| Item | Why |
|---|---|
| Rules / zones / thresholds managed from the UI with versioning | They live in per-camera YAML read by the pipeline; a safe UI needs a config-sync channel from the API to the pipeline (design needed). Roadmap |
| Camera creation from the UI, four-eyes camera changes | `register-camera` CLI remains; edit/disable is done |
| Archive: saved searches, pagination, export with four-eyes, editable query interpretation | Not started (backend search is a keyword parser) |
| Operator QoL: claim/lock alert, shift handover, j/k shortcuts, density toggle | Not started |
| API unification (`/api/alerts` vs `/api/events`) | Both kept; new endpoints are on the canonical `/api/alerts` family where they take a UUID. Adapter deprecation notes not written |
| Tram class, fog/ice detection, plate reading, undistortion | Need data/models; documented as roadmap |
| GDPR/DPIA, pentest, SLA, field validation, reliable hosting, camera-owner consent, dataset licences | Outside the repository (legal/organisational) |
| Audit-log erasure of personal data, KMS, evidence re-encryption on key rotation | Larger design changes, listed in docs/LIMITS.md |

## What remains for production
Legal basis + DPIA + retention schedule; written permission for every video source; accuracy and false-alarm measurement on real, labelled, multi-condition footage with `training/eval.py`; calibration validation per camera; a pentest; a restore drill and monitoring on the real platform; a multi-process rate limiter/SSE design before scaling beyond one API process; reliable hosting with persistent or S3 evidence storage; secret and weight custody beyond individuals' laptops.

## Next actions
1. Push nothing yet: review `docs/PR_DESCRIPTION.md`, then decide on the PR when you say so.
2. Run the CI on GitHub for this branch and fix whatever differs from the local run (Postgres 16, Docker stack).
3. Model integration: `docs/MODEL_INTEGRATION.md` (install → manifests → eval → activate → rollback).
4. Fill `source_consent` only after written permission exists; keep `cameras/iasi-piata-unirii.yaml` off until then.
