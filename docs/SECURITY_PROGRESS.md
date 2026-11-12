# Security progress log

Working log for the integration of the team prototype (`origin/main`) into the secure backend.
Plan: `docs/INTEGRATION_PLAN.md`. Control status: `docs/SECURITY_CHECKLIST.md`.
Updated in the same commit as every step.

## Decisions (owner, section 8 of the plan)

| # | Topic | Decision |
|---|---|---|
| 1 | MFA fields in `/api/login` | Approved (`mfa_required`, `mfa_enrollment`, `POST /api/login/mfa`, enroll) |
| 2 | Ingestion auth | HMAC-signed requests replace the Bearer token, including the `sink.py` change |
| 3 | `DELETE /api/ingest/cameras/{id}` | 403 in production; dev only soft-marks data as superseded. Audit entries are never deleted |
| 4 | Frontend | Team's `web/index.html`, with: script and styles in separate files (no inline script, style or handlers), no external fonts, CSRF token on every state-changing request, login screen with MFA, PWA manifest and service worker kept or added, strict CSP unchanged. Pages the dashboard lacks must be reachable from it (serving approach recorded in the plan) |
| 5 | Media | Stored as received, encrypted, tagged `redaction=heads_only`. **No code, UI, README or doc may claim plate blurring**; the README claim is to be corrected. Four-eyes covers the encrypted plate field and evidence export. Plate blurring is optional, only if time remains |
| 6 | Media view-URL TTL | 15 minutes, provided the session is re-checked on every media request |
| 7 | External AI / tracking | `RS_EXTERNAL_AI=off`, `RS_EXPERIMENT_TRACKING=off` as defaults |
| 8 | Other open items | Take the recommended option unless it weakens authentication, tenant isolation, encryption, audit, CSP or signed ingestion (then stop and ask) |

## Assumptions (open items taken at the recommended option)

* **A1 – Audit visibility (section 8 item 7):** every user with `alerts:read` sees the
  alert-related audit sidebar through the contract `GET /api/audit` (detected, viewed,
  confirmed, rejected, vlm_*), scoped to their tenant (and to visible alerts for patrol users).
  Security events stay auditor-only. Does not weaken audit: no write path changes, raw chain
  access still needs `audit:read`.
* **A2 – Deployment target (item 9):** Compose + Caddy (ours). Railway stays a later option.
  No security control is affected.
* **A3 – Dashboard-only pages:** served from the same origin as static files under the same CSP
  (details in the plan once step 8 starts).

## Environment notes

* Backend tests: from `backend/`, with `RS_TEST_ADMIN_DATABASE_URL` pointing at a local
  PostgreSQL 16 superuser (kept outside the repository; never committed).
* CI runs on `main` and `feature/**` since commit `e1122be`.

## Log

| Date | Commit | Step | Tests |
|---|---|---|---|
| 2026-10-17 | `e1122be` | CI triggers on `feature/**` | n/a |
| 2026-10-17 | `85a953a` | WIP P0.2: service accounts, key and nonce tables (migration 0003), migration-drift guard | backend suite green |
| 2026-10-17 | (this commit) | Integration plan and this log added | n/a |
| 2026-10-17 | `cbc9420` | Fix backend Dockerfile (`--require-virtualenv=false` is not a valid pip flag; stack smoke job failed at build) | CI fully green (stack job passed) |
| 2026-10-17 | `213148a` | P0.2 core: HMAC verification (skew, nonces, rate limit, body cap), service-account/key admin API + CLI, `/api/ingest/ping`, `rs_resource_tenant` covers service accounts (migration 0003 amended in place; never released) | backend suite green (incl. `test_ingest_auth.py`) |
| 2026-10-17 | (this commit) | Repair: `213148a` accidentally committed an empty `SECURITY_CHECKLIST.md` (failed scripted edit); content restored and updated | n/a |

## CI status (first runs, 2026-10-17)

* Secret scan, frontend, backend jobs: green.
* Docker stack smoke test: failed at image build (Dockerfile flag above); fixed, now green.
* **CodeQL: fails with "Code scanning is not enabled for this repository".** Needs the repository
  owner to enable code scanning (Settings > Code security). Not fixable from the branch.
  Checklist item 38 stays "unverified" for CodeQL until then.

## Notes on P0.2

* `/api/ingest/*` is exempt from the CSRF middleware **because** it accepts only the HMAC
  signature; cookies are ignored there (`test_session_cookie_is_not_accepted`).
* Unknown-key failures are rate limited per IP and not written to any audit chain (no tenant to
  attribute them to; avoids strangers growing the log). Failures with a real key id are audited.
* Assumption A4: migration 0003 was amended rather than adding a migration, because it had
  never been applied outside tests. If a dev database is already at 0003, re-create it.
