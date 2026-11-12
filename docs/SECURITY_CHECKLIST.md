# RoadSentinel – Security checklist

Source of truth for the security status. Mapped to **OWASP ASVS 4.0.3 Level 2** chapters and
the **OWASP API Security Top 10 (2023)**.

Status values: **Implemented** (code + automated test), **Partial** (some aspects missing, see
note), **Not implemented**, **Out of scope** (hackathon / organizational).

_Last updated: 2026-10-17. Baseline: 249+ backend tests; CI running._
[CI run 39037941341](https://github.com/CristiMachine25/roadsentinel/actions/runs/39037941341)
passed the backend, secure PWA, secret scan and Docker stack smoke jobs, including TLS,
security headers, non-root containers, seeding and the audit tamper demonstration. CodeQL
runs separately; SARIF artifacts are retained because code scanning uploads are disabled
on this private repository. A successful analysis does not imply that all findings are resolved.

Backend code paths below are relative to `backend/`; other paths are relative to the repo
root. Tests are in `backend/tests/` unless prefixed `secure-pwa/`.

## OWASP ASVS 4.0.3 – Level 2

| # | Control | ASVS | Status | Evidence (code → test) |
|---|---|---|---|---|
| 1 | Documented threat model and trust boundaries | V1.1 | Implemented | `docs/THREAT_MODEL.md` (review) |
| 2 | Single central access-control layer | V1.4, V4.1 | Implemented | `app/core/policy.py` → `test_isolation.py::TestRbac` |
| 3 | Passwords ≥ 12 chars, common-password check, no composition rules | V2.1 | Implemented | `app/core/security.py` → `test_auth.py::TestInvitations::test_password_policy` |
| 4 | Argon2id password storage | V2.4 | Implemented | `app/core/security.py` → `test_auth.py::TestLogin::test_recovery_code_login_single_use` (hash format) |
| 5 | Anti-automation: rate limits + lockout | V2.2.1 | Implemented | `app/core/rate_limit.py`, `app/services/auth.py` → `test_auth.py::TestBruteForce` |
| 6 | MFA (TOTP) mandatory, replay-safe, recovery codes | V2.7, V2.8 | Implemented | `app/services/auth.py` → `test_auth.py::TestEnrollment`, `TestLogin` |
| 7 | No account enumeration (generic errors, dummy hash) | V2.2, V3 | Implemented | `app/services/auth.py` → `test_auth.py::test_unknown_account_and_wrong_password_are_indistinguishable` |
| 8 | Invitation-only provisioning; single-use hashed tokens with expiry | V2.5, V2.3 | Implemented | `app/services/auth.py` → `test_auth.py::TestInvitations` |
| 9 | Password change / admin reset / MFA reset with four-eyes | V2.5 | Not implemented | planned P0.4b |
| 10 | Session tokens in HttpOnly/Secure/SameSite=Strict cookies | V3.4 | Implemented | `app/core/http.py` → `test_auth.py::test_cookie_flags` |
| 11 | Server-side session revocation (logout, user, admin) | V3.3 | Implemented | `app/api/sessions.py` → `test_auth.py::TestSessions` |
| 12 | Refresh-token rotation + reuse detection (family revoke) | V3.3 | Implemented | `app/services/auth.py::rotate_refresh` → `test_auth.py::test_refresh_reuse_revokes_family` |
| 13 | Absolute and idle session timeouts (server-side) | V3.3.1, V3.3.2 | Partial | Baseline: 7-day refresh expiry and UI idle lock in `secure-pwa/src/auth/idle.ts`; server 30-minute idle / 12-hour absolute limits are delivered by `feature/contract-api` (PR #12) |
| 14 | Re-authentication for sensitive actions | V3.7, V4.3 | Implemented | `app/deps.py::require_fresh_mfa` → `test_auth.py::TestReauth` |
| 15 | CSRF protection | V4.2.2 | Implemented | `app/core/http.py::CSRFMiddleware` → `test_auth.py::TestCsrf` |
| 16 | Tenant isolation: RLS (FORCE) + app layer, fail-closed | V4.1, V4.2 | Implemented | `alembic/versions/0002_security.py`, `app/db.py` → `test_isolation.py::TestDatabaseIsolation` |
| 17 | Object-level authorization, 404 on foreign ids | V4.2.1 | Implemented | `app/deps.py::not_found` → `test_isolation.py::TestApiIsolation` |
| 18 | Patrol users only see assigned alerts | V4.2.1 | Implemented | `app/core/policy.py::scope_alerts` → `test_isolation.py::test_patrol_sees_only_assigned_alerts` |
| 19 | Four-eyes for unblur/export | V4.3, V11.1 | Implemented | `app/services/approvals.py` → `test_approvals.py` |
| 20 | Input validation via strict schemas (extra=forbid) | V5.1 | Partial | Pydantic schemas validate types/lengths; `extra` not forbidden yet (P0.4) |
| 21 | Output encoding / no raw HTML | V5.3 | Implemented | React escaping; eslint bans `dangerouslySetInnerHTML` (`secure-pwa/eslint.config.js`) |
| 22 | No SQL built from input | V5.3.4 | Implemented | SQLAlchemy only; dynamic SQL limited to allow-listed identifiers (`rs_resource_tenant`) |
| 23 | Approved crypto only; no custom primitives | V6.2 | Implemented | `app/core/crypto.py` → `test_crypto.py` |
| 24 | Envelope encryption, per-tenant versioned DEKs, rotation | V6.4 | Implemented | `app/services/keys.py` → `test_encryption_at_rest.py::TestKeyRotation` |
| 25 | Field encryption of PII (plates, TOTP secrets), blind index | V6.2, V8.3 | Implemented | `app/core/crypto.py` → `test_encryption_at_rest.py::TestCiphertextAtRest` |
| 26 | Evidence encrypted at rest; tamper/truncation detected | V6.2, V12.3 | Implemented | `app/services/evidence.py` → `test_crypto.py::TestFileEncryption` |
| 27 | Key material from managed KMS/HSM | V6.4 | Not implemented | env master keys behind `KeyProvider`; see `docs/ARCHITECTURE_TARGET.md` |
| 28 | Generic errors, no stack traces | V7.4 | Implemented | `app/main.py` returns a generic 500 with correlation id and `X-Request-ID`; validation errors omit submitted values → `test_startup.py::TestGenericErrors` |
| 29 | Log redaction of secrets/PII | V7.1 | Implemented | `app/core/redaction.py` → `test_encryption_at_rest.py::TestLogRedaction` |
| 30 | Tamper-evident, append-only security audit log | V7.2, V7.3 | Implemented | `app/core/audit.py` → `test_audit.py` |
| 31 | Structured JSON logs with correlation ids | V7.1 | Not implemented | planned P1.5 |
| 32 | Security event detection / alerting | V7.2 | Not implemented | planned P1.5 |
| 33 | Sensitive data not cached (no-store, SW shell only) | V8.2 | Implemented | `app/core/http.py`, `secure-pwa/src/pwa/sw.ts` → `test_headers_push.py` |
| 34 | Client-side data wiped on logout | V8.2.3 | Implemented | `secure-pwa/src/auth/cleanup.ts` → `secure-pwa/src/security.test.ts` |
| 35 | Retention / purge / crypto-shredding | V8.3 | Not implemented | planned P1.6 |
| 36 | TLS everywhere externally, HSTS | V9.1 | Implemented | `deploy/Caddyfile` → passing CI `stack` job, HTTPS / headers / redirect checks |
| 37 | TLS to the database outside dev | V9.2 | Not implemented | planned P1.4 |
| 38 | Dependency scanning, SAST, secret scanning | V10.3, V14.2 | Partial | `.github/workflows/*`: pip-audit, npm audit and gitleaks passed CI; CodeQL preserves SARIF artifacts with scanning upload disabled; findings require review |
| 39 | Evidence served only via short-lived signed URLs | V12.4, V13 | Implemented | `app/api/evidence.py` → `test_encryption_at_rest.py::TestSignedEvidenceUrls` |
| 40 | Upload validation (type, size, content) | V12.1, V12.2 | Not implemented | no upload endpoint yet; planned P0.3 |
| 41 | SSRF protection for camera URLs | V12.6 | Not implemented | planned P1.3 |
| 42 | Strict CORS, Content-Type checks, body limits | V13.1, V14.5 | Partial | Explicit CORS allowlist in `app/main.py` (no headers by default); production rejects wildcard / non-HTTPS origins → `test_startup.py::TestCors`, `TestProductionConfig`; Caddy 10 MB limit; global API Content-Type/body limits remain planned P0.4 |
| 43 | Security headers (CSP, COOP/CORP, HSTS, nosniff, Referrer) | V14.4 | Implemented | `app/core/http.py`, `deploy/Caddyfile` → `test_headers_push.py` |
| 44 | Production config refuses insecure startup | V14.1 | Implemented | `app/core/startup.py` rejects weak/reused secrets, weak master keys, debug, insecure cookies/origins, seed credentials and unsafe DB roles; unreachable DB fails closed → `test_startup.py::TestProductionConfig`, `TestDatabaseRoleCheck` |
| 45 | API docs disabled in production | V14.3 | Implemented | `app/main.py` → `test_headers_push.py::test_docs_disabled_in_production` |
| 46 | Hardened containers (non-root, read-only, cap_drop) | V14.1 | Partial | `backend/Dockerfile`, `secure-pwa/Dockerfile`, compose; CI verifies non-root startup; no pids/mem limits yet (P1.4) |
| 47 | Backups encrypted and restore-tested | V8.1 | Not implemented | planned P1.7 |
| 48 | Machine-to-machine authentication: per-tenant HMAC-signed requests, replay protection (timestamp skew + single-use nonces), key rotation with overlap, instant revocation, secrets encrypted with the tenant DEK and shown once, tenant derived only from the key | V2.10, V13.2 | Implemented | `app/services/ingest_auth.py`, `app/api/service_accounts.py` → `test_ingest_auth.py` |

## OWASP API Security Top 10 (2023)

| Risk | Status | Evidence |
|---|---|---|
| API1 Broken Object Level Authorization | Implemented | RLS + `not_found` + policy scoping → `test_isolation.py` |
| API2 Broken Authentication | Implemented | User auth (`test_auth.py`) and HMAC machine auth (`test_ingest_auth.py`). Ingestion endpoints themselves arrive with plan step 3 |
| API3 Broken Object Property Level Authorization | Partial | Explicit response models; mass-assignment hardening (`extra=forbid`) planned P0.4 |
| API4 Unrestricted Resource Consumption | Partial | Auth rate limits, `limit` caps on some lists; global body/pagination caps planned P0.4 |
| API5 Broken Function Level Authorization | Implemented | `require(Permission)` on every route → `test_isolation.py::TestRbac` |
| API6 Unrestricted Access to Sensitive Business Flows | Partial | Four-eyes unblur/export, rate-limited login; per-key rate limit and body cap on ingestion (`test_ingest_auth.py::TestLimits`); media validation planned P0.3 |
| API7 Server Side Request Forgery | Not implemented | No outbound fetches today except Web Push; camera URLs planned P1.3 |
| API8 Security Misconfiguration | Partial | Headers, no-store, docs off in prod and production startup checks implemented; remaining hardening tracked above |
| API9 Improper Inventory Management | Partial | Single versioned API, docs off in prod; route-sweep test planned P0.4 |
| API10 Unsafe Consumption of APIs | Not implemented | VLM / model output handling planned P1.2 |

## Out of scope

External penetration test · hardware-backed key management / managed KMS · legal GDPR or
Directive 2016/680 assessment · physical and infrastructure security · the detection pipeline
itself (YOLO / rules / VLM logic).
