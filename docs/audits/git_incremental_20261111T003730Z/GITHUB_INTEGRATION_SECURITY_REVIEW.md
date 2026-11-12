# Incremental integration security review

Scope: source main `47e3e85`, current integration only. This report documents tested controls and limits; it is not legal certification or production sign-off.

| Boundary | Implementation / current evidence | Limit |
|---|---|---|
| Password/MFA/session | Actual native Chromium operator/admin/patrol/auditor, wrong password and TOTP refusal, protected data, refresh/new tab and logout; `native-final/live-browser-result.json` | Development HTTP loopback intentionally uses non-Secure cookies; production controls were not relaxed |
| QR onboarding | Fresh disposable user in recorded browser test enrolls QR, confirms TOTP and acknowledges eight masked recovery codes | Existing native users were not reset or re-enrolled |
| Role/tenant isolation | Full backend suite, direct app-role FORCE RLS tests and cross-tenant media/control probes | No government deployment or installed PWA HTTPS journey claimed |
| Database ownership | Native DB identity/0022/32 FORCE RLS and app NOBYPASSRLS in `runtime-final.json`; fresh schema inventory per successful runner | Disposable bootstrap migration owner retains its documented legacy BYPASSRLS; it is not used by API/worker. Native runtime role is NOBYPASSRLS. Existing dedicated NOLOGIN, column-limited identifier lookup owner remains unchanged |
| Camera onboarding | Managed creation stays disabled; malformed file URL rejected; source/grant UI writes canonical routes | Documentary rights must be supplied by actual owner/provider; public accessibility is not permission |
| Configuration | Server validator, immutable versions, distinct reviewer, optimistic revisions, exact lease/ACK and rollback | Numeric/pixel editor is not certified physical calibration |
| Worker trust | Camera-scoped HMAC key, nonce/replay/skew checks, epoch/revision fence, no DB/admin/master keys in worker environment | Full encrypted crash-retry spool and multi-camera soak remain incomplete |
| Whole recording ingestion | Same managed fence plus active recording scope; signed query metadata; revocation blocks old URL/listing | Legacy unmanaged behavior remains compatible; adopting legacy cameras is still an explicit action |
| Recording retrieval | User-bound signed link, current session, tenant RLS and scope before decrypt/range; 206/416 and cross-tenant denials tested | Range requests currently require a size-verification decryption pass; not a CDN cache path |
| Evidence/case/export | Encrypted RSE1 media, redacted preview/clip, independent approval, SHA-256 package verification/tamper refusal, audit and restart persistence | Heuristic redaction cannot guarantee complete anonymization; no admissibility claim |
| Demo isolation | Both mock mode and explicit curation required; no operational status replay/hiding; no fake patrol metrics | Curated synthetic demonstrations remain non-operational |
| Public assets | CC BY 3.0 attribution, model/source hashes, heuristic redaction and local replay watermark | They demonstrate inference, not genuine incident detection or certified speed |
| Public pages/DOM | No tenant metrics exposed; public decisions stay local; existing textContent map markers retained | A full accessibility/security penetration audit is not claimed |
| Secrets | Existing mode-0600 password file unchanged by this mission; private authenticator values never copied to reports; masked QR/recovery screenshots | The local test authenticator store is development-only and must remain private |

No new schema migration or live seed ran. All new media, camera, case and failure-injection fixtures were created in newly named disposable runtimes. Native writes were legitimate authentication/session/audit operations and the owned backend restart, not new operational fixtures. Original databases were never used as test resources.

Reversible code preimages/modes are in `backups/`; restore is a reviewed source-file operation, not a DB rollback. Do not overwrite files changed by another engineer after this mission. Existing migration backups remain untouched. No git commit, remote write, push, fetch or original-worktree mutation was performed.
