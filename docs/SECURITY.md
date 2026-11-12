# RoadSentinel – Security

This document describes the security controls that are **implemented and tested** in this
repository, how each one works, how to run the tests, and the known limitations. Production
items that are *not* implemented are listed in [ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md);
the threat model is in [THREAT_MODEL.md](THREAT_MODEL.md).

## Overview

| Area | Control | Where | Tests |
|---|---|---|---|
| Accounts | Invitation-only (no public sign-up), single-use hashed token, 24 h expiry | `app/services/auth.py`, `app/api/users.py` | `test_auth.py::TestInvitations` |
| Passwords | Argon2id (argon2-cffi), ≥ 12 chars, common-password deny list | `app/core/security.py` | `test_auth.py` |
| MFA | Mandatory TOTP, QR enrollment on first login, 8 hashed recovery codes, replay-safe | `app/services/auth.py` | `test_auth.py::TestEnrollment`, `TestLogin` |
| Sessions | 10 min access JWT + 7 day rotating refresh token, cookies only, family revocation on reuse, server-side session list | `app/services/auth.py`, `app/api/sessions.py` | `test_auth.py::TestSessions` |
| Brute force | Per-IP and per-account rate limits, 5 failures → 15 min lockout, generic errors | `app/core/rate_limit.py` | `test_auth.py::TestBruteForce` |
| CSRF | Double-submit token + Origin / `Sec-Fetch-Site` check on every unsafe `/api` request | `app/core/http.py` | `test_auth.py::TestCsrf` |
| Step-up | Fresh MFA (≤ 5 min) for approvals, export, user/session management, key rotation | `app/deps.py::require_fresh_mfa` | `test_auth.py::TestReauth`, `test_approvals.py` |
| RBAC | Central permission map + object rules (patrol: assigned alerts only) | `app/core/policy.py` | `test_isolation.py::TestRbac` |
| Tenant isolation | PostgreSQL RLS (FORCE) + app-level tenant from token only; 404 on foreign ids; probes audited | `alembic/versions/0002_security.py`, `app/db.py`, `app/deps.py` | `test_isolation.py` |
| Encryption | Envelope encryption (per-tenant DEK, versioned), AES-256-GCM fields, HMAC blind index, chunked AES-GCM evidence files | `app/core/crypto.py`, `app/services/keys.py` | `test_crypto.py`, `test_encryption_at_rest.py` |
| Evidence access | 60 s HMAC-signed URLs bound to user + evidence + variant, plus session cookie | `app/api/evidence.py` | `test_encryption_at_rest.py::TestSignedEvidenceUrls` |
| Four-eyes | Generic approval requests (unblur, export); approver ≠ requester; 30 min revocable grant | `app/services/approvals.py`, `app/api/unblur.py` | `test_approvals.py` |
| Audit | Per-tenant SHA-256 hash chain, DB-enforced append-only, verify endpoint | `app/core/audit.py` | `test_audit.py` |
| Logging | Redacting filter (passwords, tokens, JWTs, cookies, plates, keys); validation errors never echo input | `app/core/redaction.py`, `app/main.py` | `test_encryption_at_rest.py::TestLogRedaction` |
| Transport & browser | Caddy TLS + HSTS; CSP without `unsafe-*`, COOP/CORP, `no-store` on API | `deploy/Caddyfile`, `app/core/http.py` | `test_headers_push.py`, CI `stack` job |
| PWA | Static-shell-only service worker, no tokens in JS storage, logout wipes caches/IndexedDB, 5 min idle lock, generic push | `secure-pwa/src/` | `secure-pwa/src/security.test.ts` |
| Supply chain | Locked deps, pip-audit, npm audit, CodeQL, gitleaks, Dependabot, SHA-pinned actions, non-root images | `.github/`, Dockerfiles | CI |

## How the controls work

### Authentication

1. `POST /api/auth/login` checks the password. Unknown accounts still run an Argon2 verification
   against a dummy hash (constant-ish time) and always get the same `401 Invalid credentials`.
   A correct password only yields a 5-minute, HttpOnly `rs_mfa` cookie scoped to `/api/auth`;
   no session exists yet.
2. `POST /api/auth/mfa/verify` (TOTP or recovery code) or, for not-yet-enrolled users,
   `mfa/enroll/start` → `mfa/enroll/confirm`. Only then is a session created.
3. TOTP secrets are encrypted with the tenant DEK. The last accepted time-step is stored, so a
   code can never be used twice (±1 step drift allowed). Recovery codes are Argon2id hashes and
   single-use.
4. Failures of either factor count towards the lockout (5 → 15 minutes). Rate limits:
   login 30/5 min per IP and 10/5 min per account (also applied to non-existent accounts),
   MFA 10/5 min per account, invitations 20/5 min per IP, refresh 120/5 min per IP.

### Sessions and cookies

| Cookie | Content | Path | Lifetime |
|---|---|---|---|
| `__Secure-rs_access` | HS256 JWT `{sub, tid, sid, typ=access}` | `/api` | 10 min |
| `__Secure-rs_refresh` | 256-bit random token (stored as SHA-256) | `/api/auth` | 7 days |
| `__Secure-rs_mfa` | JWT `{typ=mfa_pending}` | `/api/auth` | 5 min |
| `__Secure-rs_csrf` | random token, readable by JS (double submit) | `/` | 12 h |

All are `Secure`, `SameSite=Strict`, and all but CSRF are `HttpOnly`. Every request
re-loads the session row, so revocation (user, admin, logout, refresh reuse, user disabled)
takes effect immediately rather than when the JWT expires. Refresh tokens rotate on every use;
presenting a used token revokes the whole session ("token family") and is audited.

### Authorization and tenant isolation

* `app/core/policy.py` is the only place that maps roles → permissions. Routers depend on
  `require(Permission.x)`; object rules (`scope_alerts`, `can_view_alert`) live there too.
* The tenant id comes **only** from the verified access token and is re-checked against the
  session and user rows. No endpoint accepts a tenant id.
* Every transaction runs `set_config('app.tenant_id', <tid>, true)` (= `SET LOCAL`), applied by a
  SQLAlchemy `after_begin` hook so it survives commits within a request.
* Every tenant-scoped table has `ENABLE` + `FORCE ROW LEVEL SECURITY` and one policy
  `tenant_id = rs_current_tenant()` for `USING` and `WITH CHECK`. A missing setting yields
  `NULL` → zero rows (fail closed).
* The API connects as `rs_app`: `NOSUPERUSER NOBYPASSRLS`, owns nothing, DML-only grants.
  Migrations run as `rs_owner`. A guard test fails if any table with a `tenant_id` column lacks
  a policy.
* Composite foreign keys `(tenant_id, x_id)` stop cross-tenant references (FK checks bypass RLS).
* Lookups that must happen before a tenant is known (login by e-mail, refresh by token hash,
  invitation by token hash) use narrow `SECURITY DEFINER` functions that return identifiers only.
* A lookup that finds nothing answers `404`. If the id exists in another tenant (checked with
  `rs_resource_tenant`), the probe is written to **both** tenants' audit chains; the response is
  byte-identical to a genuinely missing id.

### Encryption

* **Master keys** (`RS_MASTER_KEYS`, versioned) live behind the `KeyProvider` interface
  (`EnvKeyProvider` today, KMS/Vault later). They wrap per-tenant 256-bit keys with AES-256-GCM;
  the AAD binds `tenant_id | purpose | version`, so a wrapped key copied to another tenant will
  not unwrap.
* **Per tenant**: a `data` DEK (versioned) and an `index` key (HMAC).
* **Fields** (plates, TOTP secrets): `F1 | dek_version | 96-bit random nonce | AES-GCM(ct+tag)`
  with AAD `rs-field | tenant_id | field name`.
* **Blind index**: `HMAC-SHA256(index_key, field | normalized plate)` enables exact-match search.
* **Evidence files**: `RSE1` header (DEK version, 32-byte salt, chunk size); per-file key
  `HKDF-SHA256(DEK, salt, info=tenant|evidence|variant)`; 64 KiB chunks, counter nonces, AAD
  includes the header, the chunk index and a final-chunk flag (detects tampering, reordering and
  truncation). Both the redacted and the original variant are encrypted; neither is ever served
  statically.
* **Rotation**: `python -m app.cli rotate-tenant-key --tenant unit-a` (or
  `POST /api/tenants/current/rotate-key`) creates DEK v+1, re-encrypts encrypted columns and
  keeps old versions for existing evidence. `python -m app.cli rewrap-keys --tenant ...`
  re-wraps all DEKs after adding a new master key version.

### Audit log

`entry_hash = SHA-256(canonical JSON of tenant_id, seq, timestamp, actor_id, action,
resource_type, resource_id, ip, user_agent, details, prev_hash)`; genesis `prev_hash` is 64 zeros.
Writers take a per-tenant advisory lock so `seq` has no gaps. Entries are written in their own
transaction, so denied or failed actions are still recorded. `rs_app` has only `SELECT, INSERT`;
`BEFORE UPDATE OR DELETE` and `BEFORE TRUNCATE` triggers raise for every role, including the
owner. `GET /api/audit/verify` walks the chain and returns the first broken entry. Details are
redacted before hashing.

Audited actions include: login success/failure/lockout, MFA success/failure/enrollment,
recovery-code use, re-auth, logout, refresh-token reuse, session revocation, invitation
create/revoke/accept/failure, user updates, tenant creation, alert create/confirm/reject/assign,
plate search, evidence URL issued/viewed/exported, approval request/approve/deny/revoke/
self-approval blocked, key rotation/re-wrap, cross-tenant probes, access denials, verification runs.

### Four-eyes approvals

`ApprovalRequest(kind = unblur | export)` needs a written justification (≥ 20 characters) and a
case reference. Only a `tenant_admin` other than the requester can approve or deny, with fresh
MFA. Approval creates a 30-minute grant for the requester and that evidence only; the grant is
re-checked when each signed URL is redeemed, so revocation and expiry apply immediately.
An unblur grant never authorizes export.

### Frontend / PWA

* Cookies only; the SPA never sees a token. ESLint forbids `localStorage`,
  `sessionStorage.setItem`, `eval`, `new Function` and `dangerouslySetInnerHTML`.
* The service worker (`injectManifest`) precaches only the hashed static shell plus an offline
  page; it ignores `/api/*`. The API sends `Cache-Control: no-store` everywhere.
* Logout, session expiry and revocation call `clearClientState()`: Cache Storage, IndexedDB,
  web storage and the push subscription are deleted.
* After 5 minutes idle the UI is replaced by a lock screen that requires a TOTP code
  (`POST /api/auth/reauth`).
* Push payloads are generic (`New alert, priority: critical`); the server refuses any other
  keys and the service worker replaces anything unexpected with a fixed text.
* Invitation tokens are carried in the URL fragment (`/invite#token`), which is never sent to
  servers or in `Referer`, and removed from the address bar immediately.

## Running the security tests

```bash
# Backend (needs a PostgreSQL 16 superuser URL; a throwaway DB "rs_test" is created)
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.lock pytest httpx ruff black mypy
export RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/postgres
.venv/bin/pytest                       # 171 tests
.venv/bin/pytest tests/test_isolation.py tests/test_audit.py tests/test_encryption_at_rest.py

# Frontend
cd secure-pwa && npm ci && npm test && npm run lint && npm run build
```

Tests use dedicated roles (`rs_test_owner`, `rs_test_app`) so they never alter a dev database.

## Known limitations (hackathon scope)

* **Rate limiter is in-memory**: correct for one API process; use Redis when scaling out.
* **Master keys come from an environment variable**; a KMS/HSM is the production answer.
* **Tail truncation of the audit log** (deleting the newest entries) is not detectable from the
  chain alone; anchoring the head hash externally (WORM storage / SIEM) is on the roadmap.
* **Blind index** reveals equality of plates within a tenant (by design for search); the index
  key is not rotated by `rotate-tenant-key` (rotating it requires recomputing all indexes).
* **First-login enrollment**: someone who obtains a seeded user's password before that user
  enrolls could enroll their own authenticator. Invitations reduce this (enrollment happens in
  the same flow); seeded accounts are for development only.
* **Caddy image runs as root** inside its container (to bind 80/443); all capabilities except
  `NET_BIND_SERVICE` are dropped. Our own images run as non-root and read-only.
* **Pipeline ingestion** is authenticated by per-service-account HMAC signatures (see API.md).
  Its body is still read into memory before the signature is checked (capped by
  `ingest_max_body_bytes`): put a body-size limit in front of it.
* **Video-based speed** is for alerting/triage only (see README); fines need certified equipment.
* **Redaction is a heuristic** (head = top third of a person box, plate = lower band of a vehicle box). It misses
  small, night and unusual targets; it is not a guarantee and nothing here claims GDPR compliance.
* **Pipeline evidence has no distinct original**: only the processed copy is stored (`has_original=false`), so
  four-eyes unblur/export applies to manually created evidence only.
* **Retention** deletes evidence files, not alerts, hashes or audit entries. The audit log keeps IP, user agent and
  free-text notes for the life of the chain.
* **MFA is mandatory.** The only exception is a demo switch (`RS_MFA_EXEMPTION_ENABLED`, off by default,
  refused at start-up and ignored in production).
* **Session limits**: idle timeout 30 min and absolute lifetime 12 h are enforced; the in-memory rate limiter and the
  in-process SSE polling (1 s per connected client) limit a deployment to one API process.
* Web Push delivery depends on the browser vendor's push service; payloads contain no data.
