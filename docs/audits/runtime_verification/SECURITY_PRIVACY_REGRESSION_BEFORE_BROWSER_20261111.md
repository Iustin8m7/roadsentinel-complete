# Current security/privacy regression — 2026-11-10

Existing integration login recovery PASS. Exact identity verified live before changes; private dump restored and migration rehearsed on an isolated cluster. All original row digests preserved at migration boundary. Existing passwords untouched; four accounts enrolled through genuine MFA afterwards. A migrated to0022. Full backend422 passed/2 opt-in skipped; root213; React19; PWA9. Whole-tree/static/production security certification is not claimed.

| Boundary | Current evidence and limits |
|---|---|
| RLS |32 named ENABLE+FORCE tables on A; runtime app and old migrator NOBYPASSRLS. Dedicated NOLOGIN column-limited lookup owner only. Hash-column and schema-CREATE access denied; no role members. See live-security-after.json and test_lookup_ownership.py. |
| Tenant | Native principal drives tenant context; cross-tenant promotion/media negative HTTP passes; broader isolation suite passes. Identifier lookup does not return password hashes/media. |
| Password/MFA | All9 hashes matched saved password before repair. Four Unit A roles enrolled using QR/TOTP; normal challenge and wrong password verified in live Chromium. TOTP replay/recovery/CSRF/session tests pass. MFA exemption false. |
| CSRF/cookies | Existing middleware retained. Real cookie-preserving browser login, refresh, logout; negative Origin/token tests pass. Local HTTP Secure=false was already configured for loopback; production Secure/TLS defaults not weakened. |
| RBAC | UI uses backend permissions/roles, hides unauthorized requests; live users/audit/events negative checks. Auditor remains auditor, patrol remains patrol. Backend remains authoritative. |
| HMAC/lease | Exact-body signature, nonce/time/camera/account checks remain. Real signed managed config/heartbeat/preview, duplicate worker denial, ACK/revision2 and stop/re-enable tested. Managed positive incident remains unverified. |
| Evidence | Real recorded promotion writes encrypted redacted media; authenticated playable retrieval, tenant denial, independently approved hash-verified export pass. Redaction is heuristic, not complete anonymization; package manifest is unsigned. |
| Audit | Auth/MFA/decisions/configuration repair audited through existing service. Hash chain exists; no external independent custody anchor. |
| Consent/SSRF | Explicit local replay grant and loopback source; no external camera access or assumed rights. External DNS/redirect threat matrix and permission remain unverified. |
| Retention/recovery | Live DB backup restored/verified; no reset. Evidence crash orphan reconciliation, quotas and long-term retention soak remain backlog items. |
| Secrets | Password unchanged in0600 credential file. QR/seeds/recovery codes are only in0700/0600 ignored private authenticator directory; no screenshots of enrollment. Public traces contain paths/status only. Development TOTP helper uses actual enrolled factor. |
| Originals |608 source hashes and both HEADs unchanged; no original DB writes, no original dependency install, NO GITHUB PUSH. |

No facial recognition, persistent person identity, automatic enforcement, invented violations, certified speed, DPIA/legal compliance or production readiness is claimed.

---

# Historical security report

# Security and privacy regression

Protected existing integration DB: identity queried only in READ ONLY transaction context, rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b. Owner role remains non-BYPASSRLS; no mutation or migrations applied. Temporary cluster independently initialized under unique /tmp/rsmission-* root on 55479; per-suite target names rsmission_*. Fixture now requires exact reset name and expected server port before DROP; runtime app role stays NOBYPASSRLS.

Mandatory MFA retained; test authentication uses generated fixtures and actual TOTP. No exemptions enabled. Unsafe session actions require existing CSRF middleware. Machine writes require exact-body HMAC, time/nonce checks, service-account-derived tenant and camera scope. Managed writes additionally require active config/lease/epoch/ACK. New promotion requires both video-analysis and alert-create permission; RLS/job scope is checked before decryption. Evidence media remains authenticated and user-bound; no static public path added. Source fingerprints omit credentials/query strings. Literal loopback replay is explicit and cannot masquerade as external live.

No external source permission was assumed. Redaction remains heuristic and is inherited from analysis output. No face recognition or persistent person identity added. Counts and speed remain unvalidated. No DPIA/legal-compliance or official evidence-admissibility claim is made. Audit hash chains are not independent external anchors.

Open risks: rollback orphan ciphertext, recorded capture-time uncertainty, upload retention/quota gaps, source DNS/redirect threat validation for external networks, long-stall reader thread recovery, full approval/export regression, live-source grant record scope enforcement on all legacy routes. Consult the final ledger for tests actually executed; code presence alone does not close these findings.

## Additional executed acceptance: export and source recovery

After the earlier checkpoint, real HTTP case export uncovered two integration defects: CaseError/ExportError were not registered with the application error mapper (not-ready export answered 500), and approval API approve/deny/revoke did not call the existing export-job transition hook. app.main now registers the existing domain response mapping; app.api.unblur connects on_approval_decided. No policy was bypassed. The expanded real-model test adds a case observation, records the fixture's explicit CC BY 3.0 license through the existing admin grant API, requests export, observes not-ready 409, obtains independent admin approval, generates/downloads the encrypted package through signed authenticated access, and verifies the canonical manifest digest and all member hashes using verify_package. Package remains unsigned: hash integrity is not independent legal custody. **14 passed in 17.29 s** with the approvals suite (case-export-release.log).

The managed test now forcibly interrupts only sockets belonging to its controlled replay server and temporarily refuses reconnection. It observes authoritative reconnecting health, expiry of stale preview (404), restoration of actual frames and healthy state, then stops the worker on disable. **1 passed in 14.70 s** (managed-recovery.log). This does not establish external-live availability or multi-camera capacity. Approved configuration state is still fixture-created; actual two-admin UI activation and revision change remain unverified.

The full original-suite checkpoint was 419 passed + 2 skipped; backend-final-proof.log is the subsequent full run including these added assertions. Consult its final summary before using it as release evidence. Docs checker now works without Git metadata; snapshot omissions and quoted relative links were corrected, with 0 broken links in 85 Markdown files at that checkpoint. README source snapshot is README_BEFORE_SOURCE.txt.
