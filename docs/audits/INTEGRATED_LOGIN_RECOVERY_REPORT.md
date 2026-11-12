# Existing integration login recovery — VERIFIED

The saved development password now authenticates against the actual existing 5175 → 8003 → rsint_20261110b:55446 application, with mandatory MFA and authenticated dashboard access. See [browser evidence](ACTUAL_BROWSER_LOGIN_EVIDENCE.md).

## Proven cause

`rs_tenant_id_by_slug`, `rs_auth_find_user` and related lookups were SECURITY DEFINER with pinned `search_path=public, pg_temp`, but their owner `rsint_owner_261110b` had BYPASSRLS=false. FORCE RLS applies to a normal table owner, including when entered by SECURITY DEFINER. Before a tenant is known, the lookup session has no `app.tenant_id`; tenant policies hide the existing tenant/user rows. Authentication therefore could not discover the account and returned its normal generic Invalid credentials response.

The same visibility failure made `seed()` believe the existing platform slug was absent. Its attempted INSERT conflicted with the actual unique slug index. A zero-row app-role SELECT was not evidence of an empty table.

Authorized administrator reads found **3 tenants and 9 users**. All nine existing hashes matched the password in `backend/.integration-test-credentials.json`; accounts were active/unlocked and MFA exemption false. None was enrolled before this execution. The password and existing identities required no recovery/reset. Sanitized account evidence: [account-inspection-before.json](runtime_verification/account-inspection-before.json). Hashes/passwords are excluded.

## Least-privilege repair

New `backend/app/services/lookup_roles.py::install_lookup_owner` and Alembic `0022_narrow_lookup_owner.py` establish `rsint_app_261110b__lookup`:

- NOLOGIN, NOSUPERUSER, NOINHERIT, NOCREATEDB, NOCREATEROLE, NOREPLICATION; no members/memberships.
- BYPASSRLS solely for the six reviewed identifier-only pre-tenant functions. It owns no application tables.
- SELECT only the required lookup columns: tenant identity/slug/platform flag; user ID/email/tenant; token lookup fields; allowlisted resource ID/tenant. **No users.password_hash read privilege and no public schema CREATE.**
- Six existing SECURITY DEFINER functions retain the fixed search_path; PUBLIC EXECUTE revoked, runtime EXECUTE explicitly granted. No unsigned or general-purpose lookup API was introduced.
- Runtime app and old migration owner remain NOBYPASSRLS. All 32 tenant tables retain FORCE RLS. Tenant context still uses transaction-local configuration in `app/db.py`.

The guarded `scripts/recover_integration_login.py` defaults to read-only inspection. `--apply` requires exact workspace/URL/DB/user/system identifier/current-owner checks, private backup, isolated restore and migration rehearsal, unchanged live row digests, and final preservation verification. It refuses identity mismatches. The old shell repair now delegates to this guarded script; its former blanket migration-owner BYPASSRLS grant was removed.

The existing DB upgraded rsint_case2 → 0020 → 0021 → 0022 only after rehearsal. 0021 adds two indexes. 0020's owner prerequisite was satisfied by the narrow dedicated owner before migration; no broad privilege was granted to the migrator. 0022 intentionally retains ownership hardening on downgrade. Admin URL is needed only for setup/migration, never provided to the HTTP runtime.

## Seed and partially initialized databases

`app/services/seed.py` refuses production. Existing tenants are resolved securely, missing expected development users/keys are created in tenant context, and conflicts are reconciled instead of assuming an existing unit is complete. Repeated seed preserves existing user IDs, password hashes, roles and MFA; it does not silently reset unrelated users. New users use the supplied development password. `--users-only` skips synthetic camera/alert/evidence creation. Existing user hashes are never rewritten just because the command was rerun. An invisible existing slug produces an explicit RLS/owner diagnosis instead of repeated blind insertion.

No seed command ran against A during recovery: every required account already existed. Repeated/partial seeding was tested solely on B.

## React auth/MFA corrections

- Real `/api/auth/me` identity/permissions now drive UI roles. Patrol and auditor no longer appear as operators; auditor lands at `/app/audit`. Unauthorized stats/alert/SSE fetches are suppressed.
- Mandatory enrollment uses `/api/auth/mfa/enroll/start`, QR, six-digit TOTP, `/confirm`, then shows eight recovery codes. Authenticated navigation occurs only after acknowledging the codes, fixing the previous early redirect.
- Empty tenant data now ends loading correctly instead of showing permanent dashboard skeletons.
- Sessions survive browser reload and an actual integration backend process restart. Logout invalidates protected requests. Wrong password stays 401 and wrong/replayed TOTP is rejected by regression tests.

## Actual live state

Operator, tenant admin, patrol and auditor Unit A accounts completed genuine QR enrollment and authenticated browser sessions. The operator also passed a subsequent normal TOTP challenge. Password unchanged. Private phone-import QR and recovery artifacts are in `backend/.integration-authenticators/` (0700 directory, 0600 files); not in screenshots or Markdown. Local test credential metadata marks the observed verified state. These development authenticators are intentionally local conveniences, not a production key-storage recommendation.

## Rollback/restore guidance

The private backup folder contains dump SHA-256, original row digests, original function owners and `rollback-lookup-owners.sql`. Restoring old ownership would intentionally restore the login visibility bug; never run that SQL blindly. First verify the exact database/system identifier again. Do not restore over the running database or drop existing data. A safe restore drill creates a new unique DB/cluster, recreates the two named roles, restores the dump, and compares the metadata digests, as the recovery script already did. The additive migration has no data-deleting rollback. Keep the verified backup private and retain the functional narrow owner.

## Regression proof

`backend/tests/test_lookup_ownership.py` reproduces the exact missing-row failure by changing only the dedicated owner's attribute in a disposable DB, then restores it in finally and proves lookup/repeated seed recovery. It also denies password column access and preserves an existing changed password across reseeding. `test_seed.py` verifies partial unit repair and forced RLS. `test_auth.py` covers password/TOTP/recovery/session/CSRF/invitation isolation. Full backend: 422 passed, 2 opt-in skipped. Reproducible fresh-cluster auth + both-feature subset: 44 passed. No security control disabled.

## Final preservation and repeat-restore proof

The completed0022 database, including real enrolled MFA state, was backed up and restored again using `scripts/recover_integration_login.py --rehearse-only`. Every row digest matched, narrow lookup ownership was re-established in the clone and the clone stopped cleanly. No live DB mutation occurred in this repeat drill. Proof: runtime_verification/recovery-idempotent-rehearsal.log. New private backup: backend/.integration-backups/20261110T131915Z-5be60312. The repair supports both old and already-hardened ownership states without blind seeding.

Final tenant-scoped app-role checks found9 existing accounts with matching saved password and all4 Unit A accounts with MFA enabled/no exemptions: runtime_verification/account-inspection-after.json. Actual function definitions/search_path/ACLs and tenants/users policies: runtime_verification/lookup-function-contracts.json. Full disposable schema proof: runtime_verification/disposable-schema-proof.json,0022 and32 FORCE tables.

Test cluster55481 was stopped only after SELECT identity+data_directory exactly matched its recorded mission-owned root. Runtime B2 stopped automatically; existing55446 PostgreSQL and5175/8003 remain running. Final direct/proxy health/readiness/OpenAPI200 and unauthenticated protected401 are in runtime_verification/final-http-status.json. Frontend was rerun through the instrumented runner after the empty-dashboard fix: all19 tests/lint/TypeScript/build pass; exact commands/timing in runtime_verification/runs/20261110T131348Z-6f99f550/commands.json. Final documentation link check:0 broken links in93 active Markdown files; private dependency trees and frozen source evidence are intentionally excluded.
