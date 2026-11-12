# RoadSentinel API contracts

This page documents two distinct contracts. The secure backend in `backend/` is authoritative for
supported operation. Its contract schemas are in `backend/app/schemas/contract.py`, its native
endpoints are in `backend/app/api/`, and development-only interactive docs are at `/api/docs`.
The legacy implementation uses `roadsentinel/schemas.py` and is not suitable for operational data.

All dashboard endpoints use a session cookie set by `POST /api/login`. A `401` means "show the login screen".
Errors return `{"detail": "<message in Romanian>"}`, ready to show to the user.

Two servers implement portions of this compatibility contract. **`backend/` is authoritative**;
`roadsentinel/server.py` (prototype, shared password) is legacy offline-demo code. Differences on the secure backend are listed in
[§ Secure backend](#secure-backend-backend) at the end; shapes are identical, new fields are additive.

The API descriptions through **Server configuration** below describe the legacy implementation
unless a secure-backend note says otherwise. Do not use the legacy shared-password or bearer-token
configuration with the secure stack.

## Auth

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/login` | `{"operator": "ag. Popescu", "password": "..."}` | `Me` |
| POST | `/api/logout` | – | `Me` |
| GET | `/api/me` | – | `Me` = `{"operator": str \| null, "auth_required": bool}` |

The operator name from the session is what the audit log records for every view and decision.

## Alerts

| Method | Path | Notes |
|---|---|---|
| GET | `/api/events?status=new&camera_id=demo-highway` | `Event[]`, undecided first, then by priority (critical → info), then oldest first |
| GET | `/api/events/{id}` | `EventDetail` = `Event` + `audit[]` |
| POST | `/api/events/{id}/view` | Body `{}`. Records "who looked at this case". Call when a case is opened. `204` |
| POST | `/api/events/{id}/decision` | `{"decision": "confirm" \| "reject", "action": "dispatch_patrol", "note": "..."}`. `action` is required to confirm and ignored on reject. Returns `EventDetail`. `409` if the event was already decided (refetch and show the existing decision) |
| GET | `/api/meta` | Event type labels/priorities and the list of actions, so the UI never hardcodes them |

`Event`:

```json
{
  "id": 1, "camera_id": "demo-highway", "camera_name": "Autostradă – cameră demo (pod pietonal)",
  "location": "Demo highway, gantry km 12",
  "type": "very_high_speed", "priority": "high",
  "occurred_at": "2026-10-16T14:05:16", "video_t": 16.5,
  "track_id": 72, "object_class": "car", "speed_kmh": 155.0,
  "rule": "Viteză 155 km/h > prag 150 km/h (limită 130)",
  "details": {"limit_kmh": 130, "measured_kmh": 155.0},
  "keyframe_url": "/media/demo-highway/event_..._very_high_speed.jpg",
  "clip_url": "/media/demo-highway/event_..._very_high_speed.mp4",
  "vlm_status": "skipped", "vlm_text": null,
  "status": "new", "action": null
}
```

- `priority`: `critical` | `high` | `medium` | `info`
- `status`: `new` | `confirmed` | `rejected`
- `vlm_status`: `pending` | `confirmed` | `rejected` | `uncertain` | `skipped` (no API key). `vlm_text` is a one-line Romanian description.
- `object_class` is `null` for scene-level alerts (congestion).
- Media URLs need the session cookie; use them directly in `<img>` / `<video>`.

`AuditEntry`:

```json
{"id": 12, "event_id": 1, "actor": "ag. Popescu", "action": "confirmed", "note": "Trimite patrulă", "at": "2026-10-17T10:45:07Z", "type": "very_high_speed"}
```

`action` is one of `login`, `detected`, `viewed`, `confirmed`, `rejected`, `vlm_confirmed`, `vlm_rejected`,
`vlm_uncertain`. `at` is always UTC with an offset; `event_id` is `null` for logins.

## Live updates

`GET /api/stream` is a Server-Sent Events stream:

```js
const s = new EventSource("/api/stream");          // same origin, cookie is sent automatically
s.addEventListener("alert", (m) => addAlert(JSON.parse(m.data)));   // Event
s.addEventListener("audit", (m) => addAudit(JSON.parse(m.data)));   // AuditEntry (decisions, views, VLM)
s.onopen = () => reloadQueue();   // after a reconnect, reload once
```

Alerts carry an SSE `id`, so on reconnect the browser sends `Last-Event-ID` and alerts created in the gap are replayed.
A `401` on the stream means the session expired: call `GET /api/me` and show the login screen.

### Secure in-app notifications (`backend/`)

`GET /api/notifications?limit=30&before=<sequence>` returns a bounded inbox page, a
database-derived `unread` count, `latest_sequence`, and `next_cursor`. Each item carries
an immutable event ID, the canonical incident UUID and external alert number, event kind
(`candidate_created`, `confirmed`, `rejected`, `location_revised`), priority, source
provenance, current status, and per-user receipt timestamps. No media or coordinates are
included. `POST /api/notifications/{event_id}/read`, `/acknowledge`, or `/dismiss` updates
the caller's receipt idempotently; acknowledgement is not an incident decision.

`GET /api/notifications/stream?after=<latest_sequence>` is an authenticated SSE stream
with `notification` messages and tenant-local `id` cursors. The browser reconnects with
`Last-Event-ID`; each poll rechecks session, active user, role, and alert visibility.
The persisted event log is written in the alert transaction and polled directly from
PostgreSQL, so there is no in-memory-only delivery queue or external push dependency.
Synthetic test alerts are excluded. The operator client refreshes the inbox and map on
delivery, and falls back to periodic map refresh after a network interruption.
`GET /api/notifications/preferences` and `PUT /api/notifications/preferences` with
`{"sound_on_critical": true|false}` persist an opt-in per user. The browser attempts
audio only after a user gesture and handles autoplay denial without affecting the inbox.

## Search, stats, cameras, audit

| Method | Path | Notes |
|---|---|---|
| POST | `/api/search` | Body `{"q": "camioane oprite pe acostament ieri între 14 și 18", "limit": 50, "cursor": null}`; returns `{"filter": {...}, "results": Event[], "next_cursor": "..."}`. Page size is 1–100. Cursors are signed, tenant/filter-bound, and expire after one hour. Preferred because it avoids putting query text in URLs/access logs |
| GET (deprecated) | `/api/search?q=...&limit=50&cursor=...` | Compatibility endpoint with the same cursor response. The query is not stored or put in the audit chain, but intermediaries may log URL query strings; new clients should use POST |
| GET | `/api/saved-searches` | List the caller's saved searches (up to 100); filters are tenant-scoped and user-owned |
| POST | `/api/saved-searches` | `{"name": "...", "query": "..."}`; stores normalized filters only, not the query text |
| PUT | `/api/saved-searches/{uuid}` | Replace that caller's saved search name and parsed filters |
| POST | `/api/saved-searches/{uuid}/run` | Execute saved filters using the caller's current alert visibility and return `SearchResponse`; optional body `{"limit": 50, "cursor": "..."}` continues the signed filter-bound cursor |
| DELETE | `/api/saved-searches/{uuid}` | Delete that caller's saved search; create/update/delete/run are audited |
| GET | `/api/stats` | Counts by priority, status and type; `vlm_available` |
| GET | `/api/cameras` | Camera registry and health fields (`id` is slug; additive `uuid`, coordinates, timezone, active state, heartbeat); `video_url` is an annotated recording, not a live source |
| GET | `/api/cameras/discovery` | Requires `cameras:read`; 35 public Romanian scene records with canonical provider pages, presentation/player descriptors, source kind and separate ingestion/authorization fields. The Iași HLS URL is documented but browser playback is not asserted; candidates remain ingestion-disabled until per-source analysis permission is recorded |
| GET | `/api/audit?limit=50` | Latest audit entries, newest first |

`filter` fields: `event_types[]`, `object_classes[]`, `priorities[]`, `date_from`/`date_to` (local ISO time),
`hour_from`/`hour_to` (time-of-day window on any date), `min_speed_kmh`, `status`, `text`, `explanation`.
The parser is keyword-based, not semantic or LLM-backed. Audit records retain only query length and
the parsed filter, never the raw query text.

## Ingestion (pipeline → API, not for the UI)

HMAC per service account; the pipeline uses `RS_API_URL`, `RS_INGEST_KEY_ID`, and
`RS_INGEST_SECRET`. Secrets are never sent as bearer tokens and must not be embedded in camera URLs.

| Method | Path | Body |
|---|---|---|
| POST | `/api/ingest/events` | multipart: `event` (JSON, see `IngestEvent` in `schemas.py`), `keyframe` (jpg), `clip` (mp4). `422` with field errors if invalid; nothing is stored. Priority is derived from `type` on the server |
| PUT | `/api/ingest/cameras/{id}/video` | multipart: `video` (annotated mp4) |
| DELETE | `/api/ingest/cameras/{id}` | Removes a camera's events and media before reprocessing |

## Server configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...`; defaults to SQLite in `data/` |
| `DASHBOARD_PASSWORD` | Shared operator password; unset = no login (local dev only) |
| `SECRET_KEY` | Signs the session cookie |
| `INGEST_TOKEN` | Token the pipeline uses to post events |
| `COOKIE_SECURE` | `1` = session cookie only over HTTPS (default when a password is set) |

On Railway (`RAILWAY_ENVIRONMENT` is set) the server refuses to start without `DASHBOARD_PASSWORD`, `SECRET_KEY` and
`INGEST_TOKEN`.
| `S3_BUCKET`, `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION` | Media bucket; unset = local `data/media/` |
| `ANTHROPIC_API_KEY` | Optional: LLM search parsing (and VLM on the pipeline machine) |

## Secure backend (`backend/`)

Same paths and JSON. What changes for a client:

| Topic | Secure backend |
|---|---|
| CSRF | Every `POST`/`PATCH`/`DELETE` needs header `X-CSRF-Token` = value of cookie `__Secure-rs_csrf`. Call `GET /api/auth/csrf` once at startup to get the cookie. Ingestion (`/api/ingest/*`) is exempt |
| Login | `POST /api/login {"operator": "<e-mail>", "password": ...}` → `200 Me` with `mfa_required: true` (and `mfa_enrollment: true` on first login). Second step: `POST /api/auth/mfa/verify {"code": "123456"}` (or `{"recovery_code": ...}`) → `204`; then `GET /api/me` returns the operator. First-login enrollment: `POST /api/auth/mfa/enroll/start` (QR) and `/api/auth/mfa/enroll/confirm {"code"}`. Accounts come from invitations; there is no shared password |
| Sessions | Access cookie lives 10 min and is renewed with `POST /api/auth/refresh` (`204`); on `401` try one refresh, then show the login screen. Idle timeout 30 min and absolute lifetime 12 h are enforced by the server (`idle_timeout` revocation) |
| Actor | Always the authenticated user's display name; never taken from a request body |
| Scope | Everything is limited to the user's unit (tenant). Patrol users only see alerts assigned to them. Auditors cannot read alerts |
| Media | `keyframe_url`, `clip_url`, `video_url` look like `/api/media/<uuid>?exp=…&sig=…`: decrypted per request, bound to the user, valid 15 min (refetch the event to get fresh links). Use them directly in `<img>`/`<video>` from the same origin |
| `Event.redaction` | Additive: `"heads_only"` means the pipeline blurred only people's heads; **plates are visible** (show a badge). `"full"` = faces and plates blurred |
| `Camera` | `id` is the slug; additive `uuid`, `latitude`, `longitude`, `is_active` (for the map) |
| `GET /api/audit` | Alert history of the unit only (`login`, `detected`, `viewed`, `confirmed`, `rejected`, `vlm_*`). The full tamper-evident chain is `GET /api/audit/chain` (auditors) and `GET /api/audit/verify` |
| `Event` (additive) | `redaction`: `full` (heuristic blur of faces + plates), `heads_only` (plates visible), `off` (**no redaction**, show FĂRĂ REDACTARE) or `unknown`; `has_original`: `false` = one stored copy only (pipeline evidence), unblur/export of an original is refused with `409 no_original`; `evidence_purged`: retention deleted the files (`410` on media). `details.confidence = "low"` marks alerts computed from sparse frames, `details.speed_calibration` is `validated` or `unvalidated` (speed then "orientativ"), `details.synthetic` marks seeded demo data |
| Camera status | `GET /api/cameras` items carry `status_info` from the pipeline heartbeat: measured `fps`, rule capabilities, source state/dimensions/reconnects, traffic line counts and rolling flow. No source URL is accepted in status |
| `GET /api/stats` | `vlm_available` is always `false` here: VLM runs on the pipeline machine |
| `GET /api/stream` | Same events; the session is re-checked every second and the stream ends when it is revoked or expired (reconnect → `401` → login) |
| Search | Keyword parser only; the query text never leaves the server |
| Ingestion auth | HMAC per service account instead of a bearer token: headers `X-RS-Key-Id`, `X-RS-Timestamp` (unix s, ±60 s), `X-RS-Nonce` (single use), `X-RS-Signature` = base64url(HMAC-SHA256(secret, `METHOD\nPATH?QUERY\nTIMESTAMP\nNONCE\nhex(sha256(body))`)), no padding. Create a key with `python -m app.cli create-service-account --tenant unit-a --name pipeline-1` (secret shown once) |
| `IngestEvent` | Unknown fields → `422` (do not send `priority`); `camera_id` must be a camera registered in the unit (`python -m app.cli register-camera --tenant unit-a --slug demo-highway --name … --location …`) and inside the service account's camera scope; `occurred_at` is camera-local time without offset; `details` ≤ 4 KB, depth ≤ 3; keyframe must be JPEG, clip MP4 |
| `DELETE /api/ingest/cameras/{id}` | Nothing is ever deleted: `403` in production; elsewhere undecided alerts of that camera are hidden (`superseded`), decisions and evidence are kept |

## Added in release/ready (secure backend only)

| Area | Endpoint | Notes |
|---|---|---|
| Ingestion | `POST /api/ingest/events` | optional `event_key` (`[A-Za-z0-9_.:-]{8,80}`): a retry with the same key returns the same `id` instead of a duplicate. New types `near_miss`, `object_on_roadway` (object class `object`) |
| Ingestion | `POST /api/ingest/cameras/{id}/heartbeat` | optional JSON body `{"fps": 0.45, "rules": {"hard_braking": {"supported": false, "min_fps": 7.1, "reason": "…"}}}` (≤ 32 rules); stored as camera `status_info` |
| Recovery | `POST /api/users/{id}/reset-requests` `{reset_mfa, justification, case_reference}` | tenant admin; creates an `account_reset` approval that a **different** admin approves in `/api/approvals/{id}/approve` |
| Recovery | `POST /api/users/reset-requests/{approval_id}/issue` | the requester only, after approval: returns `{token, accept_path, expires_at}` once (1 h, single use) |
| Recovery | `POST /api/auth/reset/inspect` `{token}`, `POST /api/auth/reset/accept` `{token, password}` | public; revokes all sessions; `reset_mfa` removes TOTP + recovery codes (re-enrollment at next login) |
| Account | `POST /api/auth/password` `{current_password, new_password}` | fresh MFA; signs out the other devices |
| Sessions | `POST /api/sessions/revoke-others`, `POST /api/users/{id}/sessions/revoke-all` | own other devices / admin (fresh MFA) |
| Patrol | `GET /api/patrols` (operator/admin), `POST /api/alerts/{id}/assign`, `POST /api/alerts/{id}/patrol-status {"status": "en_route"\|"on_scene"\|"done"}` | assignee only, forward only; no positions/ETAs |
| Stats | `GET /api/stats/response?since_hours=24&tz=Europe/Bucharest` | operator/admin; median + p90 + n of creation→first view and creation→decision, rejection rate with n, by type/camera/local hour |
| Retention | `GET/PUT /api/retention`, `POST /api/retention/purge {dry_run, confirm}`, `POST/DELETE /api/retention/holds/{alert_id}` | tenant admin; purge is dry-run by default, real purge needs `confirm:"PURGE"` + fresh MFA; held alerts are never purged |
| Cameras | `POST /api/cameras {slug?, name, location, timezone?, latitude?, longitude?}` | tenant camera manager, fresh MFA; explicit slug can be matched to a local pipeline profile; response includes generated/provided `slug` |
| Cameras | `PATCH /api/cameras/{uuid}` | tenant admin, fresh MFA, audited before/after; slug immutable. Operator UI can edit name, location, coordinates, and timezone; source URLs, rules, zones, and calibration remain outside this endpoint |
| Camera workers | `GET /api/cameras/{uuid}/worker`; `POST .../worker/start`, `/stop`, `/restart` | tenant camera manager, fresh MFA for mutations; launches/stops a supervised local `roadsentinel.pipeline --live` child from an allowlisted `cameras/*.yaml` profile whose `id` matches the camera slug. Requires localhost `RS_API_URL` and camera-scoped `RS_INGEST_KEY_ID`/`RS_INGEST_SECRET`. Desired/actual state is reported separately; `RUNNING` requires a fresh post-start pipeline heartbeat. |
| Ops | `GET /api/ready`, `GET /api/metrics` (bearer `RS_METRICS_TOKEN`, 404 if unset), `GET /api/ops/status` (tenant admin) | see docs/OPERATIONS.md |

Evidence rule: `POST /api/evidence/{id}/access {"variant":"original"}`, `/export` and `POST /api/approvals` return `409 no_original` when `has_original` is false, `410 evidence_purged` after retention.

## Integrated development authentication and review contracts

The secure backend is authoritative; legacy shared-password examples above do not describe its authentication. In the integrated React UI, `POST /api/login {operator: email, password}` sets a short-lived pending-MFA cookie and returns `mfa_required` plus `mfa_enrollment`. It does not issue an authenticated user session before the second factor. Native `POST /api/auth/login {email,password}` returns `enrollment_required` instead. Both require existing CSRF/Origin rules.

For first enrollment: pending enrollment cookie → `POST /api/auth/mfa/enroll/start` returns private QR SVG data URI/secret → `POST /api/auth/mfa/enroll/confirm {code}` returns8 private recovery codes and session cookies. UI waits for recovery acknowledgement before navigation. For enrolled accounts: `POST /api/auth/mfa/verify {code}` (or recovery_code) returns204. `GET /api/auth/me` supplies actual role/permissions;401 means no valid authenticated session. `POST /api/logout` compatibility response200 and native `/api/auth/logout`204 revoke the session. Wrong password401; failed MFA never grants access. Never log QR/secrets/codes.

Explicit recorded review: `POST /api/recordings/{recording_id}/analyses/{run_id}/candidates/{index}/promote {reason,synthetic_test?}` requires owned completed analysis, video-analysis and alert-create permission, CSRF and an eligible obstruction/queue candidate. It returns the canonical alert with recorded provenance; repeated promotion returns the same ID. Foreign tenant404; forbidden role403; invalid/noneligible/unfinished state yields a bounded validation/conflict error. Audit action is emitted by the existing offline promotion service. Authenticated event/evidence routes expose protected redacted keyframe/clip, never public raw upload URLs. See the current architecture map and FULL_INTEGRATION_E2E_VALIDATION.md for tested control-plane revision/lease/HMAC routes.

Approved camera configuration may include `counting_lines: [{id, points: [[x1,y1],[x2,y2]], lane?}]`. Coordinates are pixels in the approved `reference_frame`; at most16 lines, unique IDs, finite bounded distinct endpoints, bounded lane labels and no unknown fields. Omission means no counting lines. An approved revision replaces private-profile counting lines; it does not merge unapproved geometry. This is an optional extension of existing versioned JSONB, so no schema migration beyond0022 is required. Draft/validate/submit/independent approve/activate/rollback remain under `/api/camera-control/cameras/{uuid}` and require their existing role, CSRF, fresh-MFA and revision guards.

Local worker Start passes scoped ingest credentials and required runtime/model settings to the inference child, excluding API database/session/evidence/cloud keys. Private redacted scratch files use the supervisor-owned `RS_PIPELINE_WORK_DIR`; they are not public media endpoints. Staging encryption/expiry remains a documented backlog item. Fresh browser evidence is in [Feature1](docs/audits/FEATURE_1_REAL_BROWSER_E2E.md) and [Feature2](docs/audits/FEATURE_2_REAL_BROWSER_E2E.md).


## Incremental integration contracts (47e3e85)

- `GET /api/camera-control/catalog`: authenticated `cameras:status_read` (the canonical permission enum is `cameras_status_read`), returns schema/coordinate convention, zone/rule capabilities, threshold/acquisition bounds and defaults. No tenant records or source credentials are exposed. Guest401; existing auditor read policy remains permitted. The server validator is authoritative.
- `POST /api/cameras`: additive optional `managed: true` initializes a disabled onboarding camera. Existing clients omitting it retain the legacy behavior. Duplicate tenant slug409; unauthorized mutation403. Source/grant/version/reviewer/worker gates remain separate canonical control-plane actions.
- `PUT /api/ingest/cameras/{slug}/video`: existing HMAC multipart request. Managed producers must additionally sign query `worker_epoch` and `revision`, matching the active holder/configuration, with an active `events_and_recordings` grant. Missing/stale/revoked managed credentials/scope are denied. No unsigned alternative was added.
- `GET /api/media/{evidence_id}`: existing user-bound signed URL, session/tenant/role/visibility checks precede serving. Single `Range: bytes=a-b`, `a-` or `-suffix` returns206 with `Content-Range`, `Content-Length`, `Accept-Ranges: bytes`; invalid/multiple/unsatisfiable ranges416. `Cache-Control: no-store` remains. Managed whole-camera recordings require current recording scope even for an older signed URL; revocation denies it. Alert evidence follows existing case/retention policy.
- Camera contract responses add nullable `source_kind` from the existing column. A fresh heartbeat on `recorded_replay` cannot label the source LIVE. Camera recording, preview and incident evidence remain distinct.
- Tile history uses existing `POST /api/archive/search` with structured `filters.camera_id`, not an approximate display-name search. Tenant/RBAC filtering and cursor pagination remain server-enforced. Free-text searches retain the existing private POST/saved-search workflow.

No new tables or migration revisions were introduced. Source geometry remains reference-image pixel coordinates; incompatible backdrop aspect ratios are not silently rescaled into an approved revision. Source and grant forms do not establish documentary permission by themselves. See [semantic decisions](docs/audits/git_incremental_20261111T003730Z/GITHUB_SEMANTIC_MERGE_DECISIONS.md) and [security evidence](docs/audits/git_incremental_20261111T003730Z/GITHUB_INTEGRATION_SECURITY_REVIEW.md).

Timing metadata is additive JSON: new live event details include `clip_start_source_s`, `clip_end_source_s`, `clip_encoded_fps`, `clip_event_offset_s` (actual encoded frame position), and `clip_timing=cfr_observed_span`. Recorded promotion retains `clip_start_output_s` and adds `clip_encoded_fps`. Clients do not assume the event is at the midpoint or that all clips are30FPS; unknown legacy timing does not enable precise frame-step/jump controls. No existing evidence bytes or hashes were rewritten.
