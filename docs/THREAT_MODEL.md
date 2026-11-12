# RoadSentinel – Threat model (STRIDE)

Scope: the security foundation in this repository (API, database, evidence store, PWA, reverse
proxy). The detection pipeline is out of scope until it exists.

## Assets

| Asset | Why it matters |
|---|---|
| Evidence (clips/keyframes, original and redacted) | Personal data (faces, plates), legal evidence |
| Plate numbers | Personal data under GDPR / Directive (EU) 2016/680 |
| Alerts and operator decisions | Operational police data; integrity matters for accountability |
| Audit log | Proof of who accessed what; must be trustworthy |
| Credentials, TOTP secrets, recovery codes, sessions | Account takeover enables everything else |
| Tenant keys (DEKs) and master keys | Decrypt all protected data |
| Availability of alerting | Delayed alerts delay emergency response |

## Actors

* **Operator / patrol / admin / auditor** of a police unit (tenant) – legitimate, partly trusted.
* **Malicious or curious insider** in a tenant (e.g. wants to unblur a neighbour's car).
* **User of another tenant** (Unit B probing Unit A).
* **External attacker** on the Internet / police network.
* **Privileged infrastructure insider** (DBA, host admin).
* **Stolen or shared device** holder.

## Trust boundaries

```
 Browser (PWA, SW)  ──TLS──▶  Caddy  ──▶  FastAPI (rs_app)  ──▶  PostgreSQL (RLS)
        │                                    │                        ▲
        └─ push service (untrusted) ◀─VAPID──┘                        │ migrate (rs_owner / superuser)
                                             └──▶ evidence volume (ciphertext only)
```

1. Internet ↔ Caddy (TLS termination). 2. Caddy ↔ API (internal network). 3. API ↔ DB (internal
`db` network, restricted role). 4. API ↔ evidence volume. 5. API ↔ third-party push services.
6. Device storage (Cache Storage, IndexedDB) ↔ other users of the same device.

## Threats and mitigations

Phase numbers refer to the implementation phases (0 skeleton, 1 authentication, 2 authorization
& isolation, 3 encryption, 4 audit, 5 four-eyes, 6 PWA, 7 supply chain).

### S – Spoofing

| Threat | Mitigation | Phase |
|---|---|---|
| Password guessing / credential stuffing | Argon2id, min length + common list, per-IP & per-account rate limits, lockout, generic errors | 1 |
| Stolen password | Mandatory TOTP before any session; recovery codes hashed & single use | 1 |
| TOTP code replay / phishing relay | Time-step replay protection; short MFA-pending window; SameSite=Strict cookies | 1 |
| Account enumeration | Same response and timing for unknown/locked/wrong password; per-account limits on unknown e-mails | 1 |
| Forged tokens | HS256 with server secret, typed tokens (`access` vs `mfa_pending`), issuer + exp checks, session row lookup | 1 |
| Rogue sign-up | No registration endpoint; invitation-only, single-use hashed token, 24 h | 1 |
| Spoofed push notifications | VAPID-signed sends; SW shows only whitelisted generic text | 6 |

### T – Tampering

| Threat | Mitigation | Phase |
|---|---|---|
| CSRF on state-changing endpoints | SameSite=Strict + double-submit token + Origin/Sec-Fetch-Site check (also on login) | 1 |
| Writing into another tenant | RLS `WITH CHECK`, composite tenant FKs, tenant only from token | 2 |
| Modifying ciphertext / evidence files | AES-GCM authentication; file header/chunk index/final flag in AAD | 3 |
| Swapping redacted/original or files between evidence | Per-variant, per-evidence HKDF keys | 3 |
| Editing/deleting audit entries | Hash chain; no UPDATE/DELETE grants; triggers block all roles; verify endpoint | 4 |
| Self-approving an unblur | Server-side requester ≠ approver; admin-only; fresh MFA | 5 |
| Tampered signed URL (e.g. redacted → original) | HMAC over purpose, evidence, variant, user, expiry; grant re-check | 3, 5 |
| Malicious dependency / action | Lock files, audits, CodeQL, Dependabot, SHA-pinned actions | 7 |

### R – Repudiation

| Threat | Mitigation | Phase |
|---|---|---|
| "I never viewed that evidence" | Every signed URL issuance and every view/export audited with actor, IP, UA | 3, 4 |
| "I never approved that" | Approvals record approver, time, note; audited; MFA-fresh | 4, 5 |
| Insider rewrites history | Hash chain detects edits, deletions, reorders; tamper demo | 4 |
| Failed actions disappear on rollback | Audit entries committed in their own transaction | 4 |

### I – Information disclosure

| Threat | Mitigation | Phase |
|---|---|---|
| Cross-tenant data access (IDOR) | RLS FORCE + restricted role; 404 for foreign ids; probes audited; tested on every endpoint | 2 |
| Missing tenant context → leak | Fail closed: NULL setting matches no rows (tested) | 2 |
| DB dump / backup theft | Plates, TOTP secrets: AES-256-GCM; evidence encrypted on disk; DEKs wrapped by master key | 3 |
| Unblurred faces/plates by default | Redacted variant default; original only with four-eyes grant | 5 |
| Evidence URL leakage (history, logs, Referer) | 60 s expiry, bound to user, still requires session; `Referrer-Policy: no-referrer` | 3, 6 |
| Secrets in logs | Redacting log filter; Caddy log filter drops cookies/authorization; validation errors don't echo input | 3 |
| Data left on shared device | No tokens in JS storage; no API caching; logout wipes caches/IndexedDB; idle lock | 6 |
| Push service sees personal data | Generic payload only, enforced server- and client-side | 6 |
| XSS steals data | Strict CSP (no inline/eval), React escaping, lint bans raw HTML, HttpOnly cookies | 6 |
| Clickjacking | `frame-ancestors 'none'`, `X-Frame-Options: DENY` | 6 |
| Secrets committed to git | `.env` ignored, generated by script; gitleaks in CI | 7 |

### D – Denial of service

| Threat | Mitigation | Phase |
|---|---|---|
| Login/MFA flooding | Rate limits (429 + Retry-After) | 1 |
| Lockout abuse against a known user | Lockout is time-bounded (15 min); per-IP limits slow attackers; admin can still act | 1 |
| Large uploads | Caddy `request_body max_size 10MB` | 0 |
| Resource exhaustion | Container hardening; healthchecks + restart policies | 0 |

Residual: no WAF / global DDoS protection (see roadmap).

### E – Elevation of privilege

| Threat | Mitigation | Phase |
|---|---|---|
| Operator performs admin actions | Central permission map; denials audited; RBAC matrix tested | 2 |
| Patrol reads unassigned alerts | Object-level scope in policy layer; 404 | 2 |
| Admin invites a system admin / changes own role | Assignable-role allow-list; self-modification blocked | 2 |
| Stale session used for sensitive action | Step-up MFA within 5 minutes | 1 |
| App process compromised → DB-wide access | `rs_app` has no BYPASSRLS, owns no tables, cannot ALTER; superuser creds only in one-shot migrate | 2 |
| Container escape helpers | Non-root, read-only rootfs, `cap_drop: ALL`, `no-new-privileges` | 7 |

## Residual risks

See "Known limitations" in [SECURITY.md](SECURITY.md) and the roadmap in
[ARCHITECTURE_TARGET.md](ARCHITECTURE_TARGET.md).
