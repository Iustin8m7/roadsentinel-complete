# Integration plan: team prototype (origin/main) ↔ secure backend (feature/security-hardening)

Status: **proposal, waiting for a decision**. Nothing was merged, rebased, modified or deleted.
Sources read from `origin/main` @ `6892ca7`: `API.md`, `README.md`, `roadsentinel/{server,store,schemas,
sink,media,search,vlm,pipeline,rules,tracking}.py`, `web/index.html`, `tests/test_api.py`, root
config files. Merge prediction computed with `git merge-tree` (in memory, no refs touched).

Conventions: **"theirs"** = prototype on `origin/main` (`roadsentinel/` package, SQLite/Postgres
`events` + `audit` tables, shared password, Railway). **"ours"** = `backend/app` (multi-tenant,
RLS, MFA, encrypted evidence, hash-chained audit).

> **Decisions needed from you.** Items marked **⚑ APPROVAL** would change `API.md`,
> `web/index.html` or the pipeline. They are collected in [§8](#8-decisions-needed).

---

## 1. What the prototype is (facts relevant to integration)

| Area | Prototype behaviour | Security-relevant observation |
|---|---|---|
| Login | `POST /api/login {operator, password}`; one shared `DASHBOARD_PASSWORD`; operator name is free text from the request body | Audit actor is self-declared: anyone with the password can act as "ag. Popescu". No MFA, no lockout, no per-user revocation |
| Session | Starlette `SessionMiddleware`, signed cookie, `same_site="lax"`, 12 h | No server-side revocation; no CSRF token |
| Ingestion | `Authorization: Bearer INGEST_TOKEN` (one global token) | Token is a long-lived shared secret; no replay protection, no tenant binding |
| Data | `events` (int ids, `camera_id` slug) + `audit` (mutable, `ON DELETE CASCADE` from events) | No tenants, no RLS; `clear_camera` deletes events **and their audit trail** |
| Media | `/media/{key}` behind session cookie; with S3 it **302-redirects to a presigned URL valid 1 h** | After the redirect the URL works without any login for an hour; media stored unencrypted |
| Live | `GET /api/stream` SSE, DB polling every 1 s, `id:` = event id, `Last-Event-ID` replay | Stream never re-checks the session after it opened |
| Frontend | `web/index.html`: one inline `<script>` (≈250 lines), one inline `<style>`, Google Fonts, `innerHTML` templates with an `esc()` helper | Incompatible with our CSP (details §2.6) |
| Privacy | Pipeline blurs the **top third of each detected person box** (heads) | **Plates are never blurred**; occupants inside vehicles are dropped from detections, so drivers' faces are not blurred either |

The prototype's design choices that we keep because they are right: priority derived on the
server from `type` (`EVENT_TYPES`), media names chosen by the server, `CAMERA_ID` slug pattern,
"validate everything before storing anything", 409 on double decision, SSE with replay.

---

## 2. Implementing the API.md contract in our backend

Principle: **same paths, same JSON shapes**, served by `backend/app` under RLS. The contract
layer is a thin router (`app/api/contract.py`) that maps our models to their schemas, which are
copied verbatim from `roadsentinel/schemas.py` into `app/schemas/contract.py` (no field
renamed, no field removed). Our own endpoints stay where they are, except one path collision
(`/api/audit`, see §2.3).

### 2.1 Endpoint by endpoint

| API.md endpoint | Our implementation | Auth / scoping | Notes |
|---|---|---|---|
| `POST /api/login` | Reuses `services.auth.login_password`. `operator` field = **e-mail**. Password OK → MFA required | Public, CSRF, rate limits, lockout | **⚑ APPROVAL**: MFA needs a second step (see §3.1). Without approval the contract cannot carry MFA |
| `POST /api/logout` | `revoke_session` + clear cookies; returns `Me{operator:null, auth_required:true}` | Session | Same shape |
| `GET /api/me` | `Me{operator: user.display_name, auth_required: true}` | Session optional (returns `operator:null` when anonymous, like theirs) | Same shape |
| `GET /api/events?status&camera_id` | `select(Alert)` + `scope_alerts` (patrol → assigned only); `camera_id` = camera **slug** within the tenant; ordering exactly theirs: undecided first, priority, oldest first | `alerts:read` | Hard cap 500 rows (P0.4) |
| `GET /api/events/{id}` | Lookup by per-tenant `number`; 404 via `not_found` (cross-tenant probes audited) | `alerts:read` + patrol assignment | `audit[]` from our chain (§2.3) |
| `POST /api/events/{id}/view` | Appends `alert.viewed` to the chain (new action) | `alerts:read` | 204 |
| `POST /api/events/{id}/decision` | New endpoint over existing `_decide`: `confirm` needs `action ∈ ACTIONS` (400 otherwise), `reject` ignores it; stores `action` + `note`; 409 if decided | `alerts:decide` | Actor = authenticated user, never the body |
| `GET /api/meta` | Static: `EVENT_TYPES` + `ACTIONS` (moved to `app/core/catalog.py`, single source shared with the pipeline rules) | Session | Same shape |
| `POST /api/search` body `{"q": ..., "limit": 50, "cursor": ...}` | `Filter` validated by Pydantic, stable keyset pagination under RLS, max 100 rows/page; GET remains compatibility-only | `alerts:read` + patrol scope | Cursor HMAC is tenant/filter bound and expires in one hour; audit stores normalized filter and query length only |
| `/api/saved-searches` | User-owned normalized filter create/list/update/delete/run endpoints; raw query discarded | `alerts:read`, tenant RLS, owner filter | Create/update/delete/run actions audited; 100 saved searches per user |
| `GET /api/stats` | Counts by priority/status/type under RLS; `vlm_available` = flag state | `alerts:read` | Same shape |
| `GET /api/cameras` | Our `cameras` table (tenant) instead of `cameras/*.yaml` on disk; `video_url` = media URL of the camera's annotated video evidence | `cameras:read` | Seed imports `cameras/*.yaml` into Unit A |
| `GET /api/audit?limit=50` | **Their shape**, generated from our chain (§2.3) | `audit:read` **and** operators? | ⚑ their UI shows the audit sidebar to every operator; ours restricts audit to auditor/admin. Proposal: their endpoint returns only alert-related actions of the caller's tenant (detected/viewed/confirmed/rejected/vlm_*) to `alerts:read`; security events stay auditor-only |
| `GET /api/stream` | §2.4 | Session, re-checked | |
| `GET /media/{...}` | §2.5 | Session + RLS + grant | |
| `POST /api/ingest/events` | Multipart `event` / `keyframe` / `clip` exactly as today; `IngestEvent` validated with `extra="forbid"`; P0.3 media validation; stored as encrypted evidence | **HMAC service account** (§3.3) | 422 semantics kept: nothing stored on error |
| `PUT /api/ingest/cameras/{id}/video` | Encrypted evidence of kind `camera_video` attached to the camera | HMAC service account, camera in its scope | Size limit (configurable, default 500 MB) |
| `DELETE /api/ingest/cameras/{id}` | §3.5 | HMAC service account | Semantics change, **⚑ APPROVAL** |

### 2.2 Schema mapping

**`Event` → our `Alert` (+ `Camera`, `Evidence`)**

| `Event` field | Ours today | Change needed |
|---|---|---|
| `id: int` | `alerts.id` UUID | **Add `alerts.number BIGINT`**, per-tenant monotonic (allocated like the audit `seq`, under a per-tenant advisory lock), `UNIQUE (tenant_id, number)`. UUID stays the internal key; `number` is the public id. Per-tenant numbering avoids leaking other tenants' volumes |
| `camera_id: str` (slug) | `alerts.camera_id` UUID | **Add `cameras.slug`** (`CAMERA_ID` pattern, `UNIQUE (tenant_id, slug)`); serialize the slug |
| `camera_name`, `location` | `cameras.name`, `cameras.location` | Use the **registered camera's** values; ignore the ones in the ingest payload (the pipeline must not rename cameras). Optional `alerts.location_override` if the team needs per-event location |
| `type` | `alerts.event_type` (free string) | Restrict to `EVENT_TYPES` keys (CHECK / enum) |
| `priority` | `alerts.priority` | Server-derived from `type` on ingestion (already their rule; ours accepted priority from operators on `POST /api/alerts`, keep for manual alerts only) |
| `occurred_at` (naive local) | `alerts.detected_at` timestamptz | **Add `cameras.timezone`** (default `Europe/Bucharest`); convert naive local → UTC on ingest, UTC → naive local on output, so the JSON is unchanged |
| `video_t`, `track_id`, `object_class`, `speed_kmh`, `rule` | – | **New columns** (bounded: `video_t` 0..86 400, `speed_kmh` 0..400, `rule` ≤ 300 chars, `object_class` enum) |
| `details: dict` | – | **New `details JSONB`**, ≤ 4 KB serialized, depth ≤ 3, numbers/strings only (P0.4) |
| `keyframe_url`, `clip_url` | `evidence` rows | Computed per request (§2.5) |
| `vlm_status`, `vlm_text` | – | **New columns**; `vlm_text` ≤ 300 chars, treated as untrusted text (P1.2) |
| `status` | `alerts.status` | Same values |
| `action` | – | **New `alerts.action`** (`ACTIONS` key) + `alerts.decision_note` |
| – | `plate_enc`, `plate_bidx`, `assigned_to` | Stay internal; **never** added to `Event` (plates stay out of the contract) |

**`EventDetail.audit[]` / `AuditEntry` → our `audit_log` chain**

| `AuditEntry` field | Source |
|---|---|
| `id: int` | `audit_log.seq` (per-tenant, gap-free, monotonic: also usable as SSE cursor) |
| `event_id: int \| null` | `alerts.number` of `resource_id` when `resource_type="alerts"`; `null` for logins. Store `event_no` in `details` at write time to avoid a join on every read |
| `actor: str` | `users.display_name` of `actor_id`; `"system"` for detection; `"vlm:<model>"` for VLM verdicts; service-account name for other ingestion events. **Never from a request body** |
| `action` | Mapping: `auth.login.success→login`, `alert.created→detected`, `alert.viewed→viewed`, `alert.confirmed→confirmed`, `alert.rejected→rejected`, `alert.vlm_verdict` with `details.verdict` → `vlm_confirmed\|vlm_rejected\|vlm_uncertain`. Other actions are not exposed through this endpoint |
| `note` | `details.note` (decision note / rule text / VLM reason), length-bounded |
| `at` | `audit_log.ts` (UTC, offset included: their test `test_audit_times_are_timezone_aware` holds) |
| `type` | event type of the referenced alert |

**`Me`**: `{operator: display_name, auth_required: true}` (§3.1 for the MFA extension).

**Search `filter`**: their `Filter` model is adopted as-is (field allowlist, enums for types/
classes/priorities/status). Server-side additions: `date_from`/`date_to` span ≤ 92 days,
`hour_from`/`hour_to` 0..24, `min_speed_kmh` 0..400, `text` ≤ 100 chars matched with bound
parameters only, results ≤ 200. The filter is never turned into SQL text; it feeds the same
SQLAlchemy builder (`query_events` logic ported) under RLS.

### 2.3 Data-model changes (migration 0004, hand-written)

1. `cameras`: `slug` (unique per tenant), `timezone`.
2. `alerts`: `number`, `video_t`, `track_id`, `object_class`, `speed_kmh`, `rule`, `details`,
   `vlm_status`, `vlm_text`, `action`, `decision_note`; CHECK on `event_type` / `object_class` /
   `vlm_status`; `UNIQUE (tenant_id, number)`; index `(tenant_id, status, priority, detected_at)`.
3. `evidence.kind`: add `keyframe` (JPEG), `clip` (MP4), `camera_video`; `evidence.camera_id`
   nullable FK for camera videos (composite tenant FK).
4. Audit actions added: `alert.viewed`, `alert.vlm_verdict`, `alert.search`,
   `ingest.camera_video`, `ingest.camera_superseded`.
5. **Path collision:** our `GET /api/audit` (raw chain entries) moves to `GET /api/audit/chain`;
   `GET /api/audit/verify` stays. Our React audit page and `test_audit.py::TestEndpoints` are
   updated accordingly. Their `GET /api/audit` keeps its exact shape.

All new columns go through RLS automatically (same tables); the guard test
`test_every_table_with_tenant_id_is_protected` covers any new table.

### 2.4 SSE: `GET /api/stream` with `Last-Event-ID`

Same wire format as theirs (`retry: 3000`, `event: alert` with `id: <number>`, `event: audit`
without id, `: ping` keep-alive), so `web/index.html` works unchanged. Implementation:

* **Auth at connect**: normal `get_principal` (session cookie; CSRF not needed for GET). Origin
  header, if present, must be in the allowlist.
* **Tenant binding**: each poll runs in a fresh short transaction with `SET LOCAL app.tenant_id`
  of the connecting user; RLS guarantees nothing else can appear. Patrol users get
  `scope_alerts` (assigned only), and `audit` events only for alerts they can see.
* **Replay**: `Last-Event-ID` (digits only, ≤ 19 chars) → `number > id` within the tenant,
  capped at 200 replayed alerts; otherwise start from the current max (like theirs).
* **Revocation**: every poll (1 s) re-checks the session row and user (`revoked_at`, `is_active`,
  idle/absolute timeout from P0.4b). On failure the stream ends; the browser reconnects and gets
  `401`, which their UI already turns into the login screen.
* **Limits**: ≤ 3 concurrent streams per user and ≤ 200 per tenant (in-memory counter, Redis
  later); 15 s keep-alive; streams closed after the absolute session lifetime anyway.
* **Hardening**: `Cache-Control: no-store`, `X-Accel-Buffering: no`; Caddy needs
  `flush_interval -1` on `/api/stream`. Polling off the event loop (threadpool) like theirs;
  `LISTEN/NOTIFY` is a later optimization.

### 2.5 `/media` URLs with encrypted evidence, usable from `<img>` and `<video>`

Constraints: their UI puts `keyframe_url`/`clip_url` straight into `<img src>`/`<video src>`
(no `fetch`, no headers); `<video>` issues **HTTP Range** requests over minutes (seeking, Safari
always uses Range); media must stay encrypted at rest and be served only to authorized users.

Design:

* URL shape (opaque to the UI, contract only says "media URL"):
  `/media/<evidence_uuid>/<variant>.<ext>?exp=<unix>&sig=<hmac>` where `variant` is
  `redacted` by default. Generated when serializing each `Event`.
* **Authorization on every request** (including each Range request): session cookie →
  `get_principal` → RLS lookup of the evidence → patrol assignment check → for `original`, an
  active four-eyes grant. The cookie is sent automatically for same-origin `<img>`/`<video>`
  (SameSite=Strict allows same-site subresource requests).
* The HMAC signature (bound to user id, evidence, variant, expiry) stays as defence in depth
  (URL copied into another account or tenant fails), but its TTL for `view` URLs becomes
  **15 minutes** instead of 60 s, because a `<video>` element keeps re-requesting the same URL
  while playing/seeking. Export URLs keep 60 s. **This relaxes one parameter of the first pass;
  the session check on every request is what keeps it safe.** Recorded in SECURITY.md.
* **Range support** on the decrypting endpoint: our file format is chunked AES-GCM (64 KiB
  plaintext chunks, per-chunk tag), so a byte range maps to whole chunks: decrypt only those
  chunks, slice, return `206` with `Content-Range`, `Accept-Ranges: bytes`. Each chunk is still
  authenticated; the final-chunk flag is checked when the last chunk is included.
* **No S3 presigned redirects** (their 1-hour public URLs). If a bucket is used later, it only
  stores ciphertext and the API streams it.
* Response headers: `Content-Type` from the validated type (never client MIME),
  `Content-Disposition: inline`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
  `Cross-Origin-Resource-Policy: same-origin`.
* Every `/media` request for `original` is audited; `redacted` views are audited once per
  evidence per session (not per Range request) to keep the chain readable.

**Redaction caveat (⚑ decision):** the pipeline only blurs heads of detected people and never
plates (§1), and it sends no unblurred original. Proposal: store the pipeline's files as the
`redacted` variant flagged `redaction="heads_only"` and show a "plates not blurred" badge until
the pipeline team adds plate blurring; the four-eyes unblur flow only has something to unblur
once the pipeline also sends the raw clip. Alternative: store them as `original` and show
nothing until a grant exists (safe but breaks the demo).

### 2.6 `web/index.html` vs our CSP

Our CSP (`script-src 'self'; style-src 'self'; font-src 'self'`, no `unsafe-inline`) **blocks**:

1. The inline `<script>` at line 221 (whole app) → blank dashboard.
2. The inline `<style>` block.
3. One inline `style="padding:16px"` inside an `innerHTML` template (line 268): style
   attributes created by HTML parsing are blocked too.
4. Google Fonts (`fonts.googleapis.com` CSS, `fonts.gstatic.com` fonts): external hosts, and a
   privacy leak (police workstation IP/User-Agent to Google).

Not a problem: there are **no inline event handlers** (`on*=`) and no `eval`; all listeners use
`addEventListener`. `innerHTML` is used in 8 places; dynamic values go through `esc()` except
`TYPE[e.type] ?? e.type` and numbers (server-validated enums: low risk, but wrap in `esc()`).
`esc()` does not escape `'`; it is only used in double-quoted attributes, so it holds.

Required change (mechanical, **⚑ APPROVAL** because the file is the team's): move the script to
`web/app.js` and styles to `web/app.css`, replace the one style attribute with a class, self-host
the Barlow fonts (SIL OFL) or fall back to system fonts, and add the CSRF header to `api()`:

```js
const csrf = () => document.cookie.split("; ").find((c) => c.startsWith("__Secure-rs_csrf="))?.split("=")[1];
const api = async (path, body) => {
  const r = await fetch(path, body && { method: "POST", body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() } });
  ...
```

(plus one `GET /api/auth/csrf` call in `start()`). Rejected alternative: CSP hashes for the
inline script. They break on every edit, and the inline style attribute and Google Fonts would
still be blocked.

---

## 3. Security model mapped onto their flows

### 3.1 Per-user accounts with MFA instead of the shared password

* Accounts come from invitations (tenant admin), Argon2id, mandatory TOTP, lockout, rate limits
  (all existing). `DASHBOARD_PASSWORD` disappears.
* **Audit actor = authenticated user** (`principal.user_id` → display name). The `operator`
  field of the login body is only the login identifier (e-mail); it is never written to the
  audit log as an actor.
* **Contract gap (⚑ APPROVAL):** API.md's login returns `Me` after one step. Additive,
  backward-compatible proposal:
  * `POST /api/login` → `401` (bad credentials) or `200 Me` with two **new optional fields**:
    `{"operator": null, "auth_required": true, "mfa_required": true, "mfa_enrollment": false}`.
  * New `POST /api/login/mfa {"code": "123456"}` (or `{"recovery_code": ...}`) → `Me`.
  * New `POST /api/login/mfa/enroll` → `{qr_svg_data_uri, otpauth_uri}` for first login (or keep
    enrollment in our React page at `/login` and link to it).
  * UI: one extra dialog step in `index.html` (≈30 lines) after the password step.
* Session idle lock: their UI has none; our server-side idle/absolute timeouts (P0.4b) make
  the stream and API return 401, and their UI already shows the login screen.

### 3.2 Tenant scoping

* Every contract endpoint goes through `get_principal` → `SET LOCAL app.tenant_id`; no tenant
  in URLs or bodies. Camera slugs, event numbers and audit seqs are **per tenant**, so
  `GET /api/events/7` in Unit B can never resolve to Unit A's event 7. Cross-tenant probes
  return the same 404 and are audited (existing `not_found`).
* `/api/cameras` lists only the tenant's cameras; `cameras/*.yaml` becomes seed input.

### 3.3 Per-tenant HMAC ingestion replacing `INGEST_TOKEN`

Server side: P0.2 (in progress, uncommitted on `feature/security-hardening`): `ServiceAccount` per
tenant (optionally limited to camera ids), `ServiceKey` (secret shown once, encrypted with the
tenant DEK, rotation with overlap, immediate revocation), signature over
`METHOD\nPATH?QUERY\nTIMESTAMP\nNONCE\nSHA256(body)`, ±60 s skew, nonce table, per-key rate
limits, tenant derived **only** from the key. `camera_id` in the payload must be a camera slug
of that tenant and inside the account's camera scope.

**⚑ APPROVAL (API.md "Bearer token" line + pipeline code).** Exact change in
`roadsentinel/sink.py` (the only pipeline file touched; ~35 lines; no other module changes):

```python
# --- sink.py ---------------------------------------------------------------
import hashlib, hmac, base64, secrets, time            # new imports

class RemoteSink:
    def __init__(self, url, key_id, secret):            # was: (self, url, token)
        import httpx

        self.key_id, self.secret = key_id, secret.encode()
        # was: headers={"Authorization": f"Bearer {token}"}
        self.http = httpx.Client(base_url=url.rstrip("/"), timeout=120)

    def _send(self, method, path, **kw):                # new: sign the exact bytes sent
        req = self.http.build_request(method, path, **kw)
        body = req.read()                                # multipart is rendered once, here
        ts, nonce = str(int(time.time())), secrets.token_urlsafe(18)
        target = req.url.raw_path.decode()               # path + query, as the server sees it
        msg = "\n".join([method, target, ts, nonce, hashlib.sha256(body).hexdigest()]).encode()
        sig = base64.urlsafe_b64encode(hmac.new(self.secret, msg, hashlib.sha256).digest()).decode().rstrip("=")
        req.headers.update({"X-RS-Key-Id": self.key_id, "X-RS-Timestamp": ts,
                            "X-RS-Nonce": nonce, "X-RS-Signature": sig})
        r = self.http.send(req)
        r.raise_for_status()
        return r

    def clear_camera(self, camera_id):
        self._send("DELETE", f"/api/ingest/cameras/{camera_id}")          # semantics §3.5

    def add_event(self, event, keyframe_path, clip_path):
        body = {k: event.get(k) for k in EVENT_FIELDS if k != "priority"}  # server derives priority
        with open(keyframe_path, "rb") as kf, open(clip_path, "rb") as clip:
            r = self._send("POST", "/api/ingest/events", data={"event": json.dumps(body, default=str)},
                           files={"keyframe": ("keyframe.jpg", kf, "image/jpeg"),
                                  "clip": ("clip.mp4", clip, "video/mp4")})
        return r.json()["id"]

    def add_camera_video(self, camera_id, path):
        with open(path, "rb") as f:
            self._send("PUT", f"/api/ingest/cameras/{camera_id}/video",
                       files={"video": ("annotated.mp4", f, "video/mp4")})


def from_env():
    url = os.environ.get("RS_API_URL")
    key_id, secret = os.environ.get("RS_INGEST_KEY_ID"), os.environ.get("RS_INGEST_SECRET")
    if url:
        if not (key_id and secret):
            raise SystemExit("RS_API_URL is set but RS_INGEST_KEY_ID / RS_INGEST_SECRET are missing.")
        return RemoteSink(url, key_id, secret)
    return LocalSink()
```

Notes: filenames are sent as fixed names (no local paths leak); `priority` is no longer sent
(the server ignores it anyway; `extra="forbid"` would otherwise reject it). Also `EVENT_FIELDS`
must drop `priority` (their test `test_priority_comes_from_event_type` keeps passing on our side
because we ignore/forbid client priority). `pipeline/client_example.py` (P0.2) will contain the
same signing code as a standalone reference. `LocalSink` (direct DB writes) cannot work against
our database: it writes their `events` table with no tenant. It stays for offline demos with
their server, or is removed later.

### 3.4 Append-only audit chain replacing their `audit` table

* Every `store.log(...)` / `insert_event` / `set_decision` / `set_vlm` call site maps to
  `audit.record(...)` with the actions in §2.2; entries are hash-chained per tenant, written in
  their own transaction, and cannot be updated/deleted (grants + triggers).
* Their `audit` table had `ON DELETE CASCADE` from events: that behaviour is dropped; audit
  entries outlive the events they reference.
* `GET /api/audit` (their shape) and `EventDetail.audit` are *views* over the chain;
  integrity stays verifiable with `GET /api/audit/verify`.

### 3.5 `DELETE /api/ingest/cameras/{id}`

Today it deletes a camera's events **and their audit trail** (and media) before batch
reprocessing. That cannot coexist with an append-only audit log or evidence integrity, and it
lets anyone holding the ingest token wipe operator decisions.

Proposal (**⚑ APPROVAL**, contract semantics change, same path and status code):

* Production (`APP_ENV=prod`): **`403`**, audited (`ingest.camera_clear_denied`). Use
  `--live` (append-only), as the README already recommends for production.
* Dev/demo: **soft supersede**: events of that camera that are still `new` are marked
  `status`→ hidden via a new `alerts.superseded_at` (excluded from `/api/events`, `/api/search`,
  `/api/stats`, SSE), decided events and all evidence are kept, and one audit entry
  `ingest.camera_superseded {count}` is appended. Nothing is deleted.
* Service accounts need an explicit scope `camera:reset` to call it at all.

---

## 4. What leaves the deployment (third parties)

| Flow | Where it runs | Destination | Exactly what is sent | Faces / plates blurred? |
|---|---|---|---|---|
| **VLM verification** (`vlm.verify`) | Pipeline machine | Anthropic Messages API (`claude-opus-5-5`) via `ANTHROPIC_API_KEY` | Up to **3 JPEG images**: the keyframe (processed frame, width `OUT_W`, with boxes, labels and the event caption drawn) and 2 frames sampled from the event clip, resized to 1280×720; plus text: event type, rule string (measured speed and thresholds), object class, speed | **Partially.** Only the top third of each *detected* person box is blurred. **Plates are never blurred.** People inside vehicles are removed from detections, so **drivers/passengers are not blurred**. Undetected people are not blurred |
| **LLM search parsing** (`search.parse_llm`) | API server | Anthropic Messages API | The investigator's **query text verbatim**, today's date and weekday, the list of event types and labels. No images, no event data | n/a. The query can contain plates, names or addresses typed by a user |
| **Experiment tracking** (`tracking.py`) | Pipeline machine | Weights & Biases (`api.wandb.ai`), on automatically when a W&B key exists | Run config, git commit, metrics, an events table **with every keyframe image**, and the **full annotated video** (`wandb.Video`) | Same partial blurring as above; **plates visible** |
| Google Fonts | Operator browser | Google | Workstation IP, User-Agent, Referer policy permitting | n/a |
| S3 presigned media (if `S3_BUCKET` set) | Browser ← bucket | Railway bucket provider | Keyframes/clips unencrypted; URLs usable without login for 1 h | Partial (as above) |

**Configuration flag proposal.** One policy setting enforced on both machines:

```
RS_EXTERNAL_AI=off          # off (default in prod) | search_text | frames
```

* `off`: `vlm.check` returns `{"vlm_status": "skipped", "vlm_text": "Verificare VLM dezactivată de politică."}`
  **before** any image is read; `search.parse` uses only the keyword parser; `vlm_available=false`
  in `/api/stats`.
* `search_text`: only the search query text may go to the provider (documented as possible
  personal data).
* `frames`: VLM may send frames. Only allowed if plates **and** faces are blurred in those frames
  (pipeline flag `RS_REDACTION=full`); the server refuses to start in prod with
  `frames` unless `RS_EXTERNAL_AI_DPIA_REF` (a DPIA reference) is set.
* Separately `RS_EXPERIMENT_TRACKING=off` (default) disables W&B, or at least
  `wandb.Image`/`wandb.Video` uploads. Tracking evidence images in a SaaS has no operational
  need.
* The provider and model used for each verdict are written into the audit chain
  (`alert.vlm_verdict {provider, model}`) so every external transfer is accounted for.

GDPR implication (to document, not to claim compliance): sending police camera frames to a
third-party model provider is a transfer of personal data to a processor; it needs a legal basis
under Directive 2016/680, a processing agreement, data-residency review and a DPIA. The default
must be `off`.

---

## 5. Merge prediction (`git merge-tree feature/security-hardening origin/main`)

Merge base: `ce74693` (initial commit). Note: uncommitted P0.2 work is not part of the prediction.

**Textual conflicts (3, all trivial):**

| File | Kind | Resolution |
|---|---|---|
| `.gitignore` | content | Union of both (theirs adds `runs/`, `wandb/`, `*.pt`; ours adds `.idea/`, `data/`, caches, `*.tsbuildinfo`, `.env.*` with `!.env.example`) |
| `.dockerignore` | add/add | Keep ours at root (excludes `.env`, `data`, `backend/tests`, `node_modules`) + their `runs/`, `wandb/`, `*.pt`, `tests/` |
| `README.md` | content | Their "Run the demo / Deploy / Architecture" sections + our "Getting started (security foundation)"; one combined architecture diagram |

**No path conflicts**: their code is under `roadsentinel/`, `web/`, `cameras/`, `tests/`, root
`Dockerfile`; ours under `backend/`, `frontend/`, `deploy/`, `docs/`, `backend/tests/`.
`scripts/` has different file names on each side.

**Semantic conflicts (do not show up in git):**

1. **Two API servers** claim `/api/*`: `roadsentinel/server.py` (root `Dockerfile`, Railway) and
   `backend/app` (Compose + Caddy). Only one may be deployed. Plan: deploy ours, keep their
   package for the pipeline (`pipeline.py`, `rules.py`, `geometry.py`, `sink.py`, `vlm.py`,
   `search.parse_keywords`), retire `server.py`/`store.py`/`media.py` after the port (their
   decision).
2. **Same database**: `store.connect()` runs `meta.create_all()` and would create `events`/`audit`
   tables **without RLS** in our database if pointed at it. Never give the prototype server our
   `DATABASE_URL`.
3. **Deployment**: Railway runs one container; our stack is Compose + Caddy. Railway option:
   our backend image as the service (Railway terminates TLS; `RS_TRUST_PROXY=true`, HSTS from
   the app), Railway Postgres with a one-off `bootstrap-db && migrate` pre-deploy command, and the
   startup check will (correctly) refuse to start if the app is given the superuser URL.
4. **Python tooling**: their `ruff.toml` (line-length 120) at the root vs our
   `backend/pyproject.toml` (100); ruff uses the nearest config, so both keep working.

**Tests after a plain merge:** none of ours break (separate package and test tree; our CI runs
in `backend/`). Their 15 test functions in `tests/` (plus `test_rules.py`) keep passing too, with their own requirements. Caveat:
running `pytest` **from the repository root** would collect both trees and our
`from tests.conftest import ...` would resolve to their `tests/` package. Always run each
suite from its own directory (CI already does for ours; their suite is not in our CI).

**Tests after porting the contract onto our backend** (their file ported to
`backend/tests/test_contract.py`):

| Their test | Outcome on our backend |
|---|---|
| `test_dashboard_requires_login` | **Changes**: password alone → `mfa_required`; needs MFA step |
| `test_ingest_requires_token` | **Changes**: Bearer token → HMAC signature (negative cases become forged/replayed/expired signature) |
| `test_ingested_event_is_listed_with_media` | **Changes**: fake bytes `b"mp4-bytes"` are rejected by P0.3 media validation; needs a real tiny MP4/JPEG; media served decrypted |
| `test_decision_is_attributed_to_logged_in_operator` | Passes with actor = display name of the authenticated user; trail must filter to alert actions |
| `test_search_by_speed` | Passes (keyword parser) |
| `test_reprocessing_a_camera_replaces_its_events` | **Changes by design** (§3.5): dev = superseded/hidden, prod = 403 |
| `test_invalid_ingest_is_rejected_and_stores_nothing` (4 cases) | Passes; plus `extra="forbid"` cases |
| `test_ingest_rejects_bad_json` | Passes (422) |
| `test_priority_comes_from_event_type` | Passes if the ported payload omits `priority`; with `extra="forbid"` a payload containing `priority` gets 422 (stricter than theirs; or explicitly ignore that one field) |
| `test_camera_routes_reject_path_traversal` | Passes (slug pattern) |
| `test_media_does_not_serve_files_outside_media_root` | Passes (UUID keys, no filesystem paths in URLs) |
| `test_non_ascii_password` | Rewritten for per-user Argon2id passwords (Unicode supported) |
| `test_decided_event_cannot_be_decided_again` | Passes (409) |
| `test_audit_times_are_timezone_aware` | Passes |
| `test_stream_replays_events_missed_while_disconnected` | Rewritten as an HTTP test (`Last-Event-ID` header) instead of calling the internal generator |

Ours that need updating: `test_audit.py::TestEndpoints::test_listing_requires_audit_role` (path
→ `/api/audit/chain`), `frontend/src/routes/AuditPage.tsx`, the route-sweep and cross-tenant
suites (P0.4) gain the new routes. `test_encryption_at_rest.py::test_ttl_is_60_seconds` stays for
export URLs; a new test pins the 15-minute view TTL.

---

## 6. Step-by-step plan (end-to-end demo first)

Target demo: *pipeline posts an alert → operator logs in with MFA → sees it live → confirms it →
audit chain records it → Unit B cannot see it.* Estimates are focused work including tests.

| # | Step | Depends on | Effort | Demo-critical |
|---|---|---|---|---|
| 1 | Finish and commit **P0.2 core** (service accounts, HMAC verification, nonces, key admin endpoints, tests) | – | 2 h | ✅ |
| 2 | **Migration 0004** (§2.3) + seed: import `cameras/*.yaml` as Unit A cameras (slugs `demo-highway`, `demo-urban`), a Unit A service account, print key id + secret once | 1 | 1.5 h | ✅ |
| 3 | **`POST /api/ingest/events`** in their multipart shape: `IngestEvent` (strict), priority from type, timezone conversion, JPEG keyframe + MP4 clip validated (magic bytes + ffprobe from P0.3, minimal subset), encrypted evidence, `alert.created` audit | 1, 2 | 2 h | ✅ |
| 4 | **`sink.py` signing change** (§3.3), handed to the pipeline team, + `pipeline/client_example.py`; verify against a local server with a real pipeline run if a GPU/M2 machine is available | 3, ⚑ | 1 h | ✅ |
| 5 | **Read endpoints** `/api/me`, `/api/meta`, `/api/events`, `/api/events/{id}`, `/api/cameras`, `/api/stats`, their `/api/audit` (+ move ours to `/api/audit/chain`) | 2 | 2 h | ✅ |
| 6 | **`/media`** endpoint with session + RLS check, 15-min signed view URLs, Range support | 3 | 1.5 h | ✅ (video playback) |
| 7 | **`/view` + `/decision`** with ACTIONS, 409, audit actions mapped | 5 | 1 h | ✅ |
| 8 | **Login + MFA in their UI**: `/api/login` + `/api/login/mfa` (+ enroll) per §3.1; `index.html` → `app.js`/`app.css`, CSRF header, MFA dialog, fonts | 5, ⚑ | 2 h | ✅ |
| 9 | **SSE `/api/stream`** with replay, per-poll session re-check, patrol filter, limits; Caddy `flush_interval -1` | 5 | 1.5 h | ✅ (live) |
| 10 | **Isolation proof for the new routes**: extend cross-tenant suite + port their `test_api.py` | 3–9 | 1.5 h | ✅ |
| 11 | `PUT /api/ingest/cameras/{id}/video` + `DELETE` semantics (§3.5) | 3 | 1 h | – |
| 12 | `/api/search` (their `Filter`, keyword parser, RLS, caps) + `RS_EXTERNAL_AI` flag (server side) | 5 | 1.5 h | – |
| 13 | Pipeline-side privacy flags (`RS_EXTERNAL_AI`, `RS_EXPERIMENT_TRACKING`, plate blurring) — pipeline team | ⚑ | (theirs) | – |
| 14 | Resume hardening tiers: rest of P0.3 (media worker boundary, quotas), P0.4 sweep, P0.4b, then P1/P2 | – | per tier budget | – |

**Critical path to the full demo: steps 1–10 ≈ 16 h.** First visible milestone after steps 1–3
+ 5 (≈ 7.5 h): signed ingestion + alert listed in the API for Unit A only.

**What to cut if time runs out (in this order):**

1. Step 12 LLM search (keep the keyword parser; it's also the privacy-safe default) and step 11
   annotated camera video (`video_url: null` is valid in the contract).
2. SSE `audit` events (keep `alert` events with replay; the UI reloads on alert anyway).
3. Range support in step 6. Chrome plays faststart MP4 without seeking; Safari needs it, so
   say "use Chrome for the demo".
4. MFA enrollment inside their UI: enroll users beforehand through our React `/login` page and
   keep only the code step in `index.html`.
5. Do **not** cut: HMAC ingestion (step 1/3), session-bound actor + audit chain (step 7),
   tenant isolation tests (step 10), CSP-compatible frontend (step 8). Those are the demo's
   security story.

---

## 7. Risks and notes

* `vlm.verify` uses `client.messages.parse(..., output_format=Verdict)`. The current Anthropic
  SDK documents structured outputs via `output_config`/`parse()` helpers. Check against the
  installed SDK version before the demo (pipeline side).
* Their `IngestEvent.details: dict[str, Any]` and `vlm_text` are unbounded. We bound them
  (§2.2). Pipeline payloads larger than the limits will get 422.
* Their `occurred_at` is naive local time; DST transitions produce ambiguous times. Conversion
  uses the camera's IANA zone with `fold=0` and is documented.
* Our uncommitted P0.2 work-in-progress (migration 0003, service models, migration-drift guard)
  stays as-is in the working tree until you decide. Nothing from it is committed or pushed.

---

## 8. Decisions needed

1. **API.md login extension for MFA** (§3.1): approve the additive fields `mfa_required`,
   `mfa_enrollment` and the new `POST /api/login/mfa` (+ enroll)?
2. **Ingestion auth** (§3.3): replace "Bearer `INGEST_TOKEN`" in API.md with HMAC headers, and
   apply the `sink.py` change (pipeline team)?
3. **`DELETE /api/ingest/cameras/{id}`** (§3.5): prod 403 + dev soft-supersede, nothing deleted?
4. **`web/index.html` changes** (§2.6): extract script/style, self-host fonts, CSRF header, MFA
   step? Or should the team use our React frontend against the same contract instead (more work,
   ~1 day)?
5. **Redaction** (§2.5): store pipeline media as `redacted (heads_only)` with a visible badge
   until plates are blurred by the pipeline, or treat it as `original` (grant needed)?
6. **External AI** (§4): adopt `RS_EXTERNAL_AI=off` by default (VLM `skipped`, keyword search)
   and `RS_EXPERIMENT_TRACKING=off`?
7. **Audit visibility** (§2.1): may every operator see the alert-related audit sidebar (their
   UI), with security events auditor-only?
8. **Media view-URL TTL** (§2.5): accept 15 minutes for `view` URLs, given the per-request
   session check?
9. **Deployment target**: Compose + Caddy (ours), or our backend image on Railway (§5.3)?
