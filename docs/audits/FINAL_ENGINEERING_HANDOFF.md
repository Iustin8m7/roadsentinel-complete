> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Final engineering handoff — existing login recovered

Current execution: 2026-11-10. **Existing integrated browser login PASS**, actual 5175 → 8003 → rsint_20261110b:55446. Four Unit A roles enrolled through real MFA; normal operator challenge, role checks, protected dashboard loading, browser reload, backend restart and logout verified. Password preserved; no seed/reset/password replacement.

Start with [FINAL_LOGIN_HANDOFF.md](FINAL_LOGIN_HANDOFF.md), [OPERATOR_DEMO_QUICKSTART.md](OPERATOR_DEMO_QUICKSTART.md), [INTEGRATED_LOGIN_RECOVERY_REPORT.md](INTEGRATED_LOGIN_RECOVERY_REPORT.md), [FULL_INTEGRATION_E2E_VALIDATION.md](FULL_INTEGRATION_E2E_VALIDATION.md).

## Delivered fixes

- Root cause: SECURITY DEFINER owner could not bypass FORCE RLS before tenant discovery. Six identifier-only functions now have a narrowly column-privileged NOLOGIN owner; runtime/migrator remain NOBYPASSRLS; all 32 FORCE RLS tables retained.
- Existing DB was backed up, restored/verified on a new cluster, migrated there as rehearsal, then upgraded additively to0022. Pre-existing table row digests were preserved at the migration boundary. Backup location and system identity are in the recovery report.
- Seed repairs partial development units and preserves existing passwords/roles/MFA; production seed forbidden. No seed was necessary on the existing DB.
- React uses native permissions/roles, retains recovery-code screen until acknowledgment, and properly completes an empty dashboard load. Dedicated integration Python runtime and guarded startup/repair/fixture runners added.
- Real camera test now creates state through actual admin UI/API, independently approves revisions, runs real model/lease/ACK/changing browser preview, tests competing worker refusal, revision2, reconnect and disable/re-enable. Orderly worker exit releases its lease.
- Recorded model fixture now executes actual UI rejection/case observation, followed by independent approval and hash-verified HTTP export.

## Verification

Backend422 passed/2 opt-in skipped; pipeline213 passed; React19 passed; PWA9 passed; both builds and lints pass. Independently repeatable fresh-cluster auth+flows44 passed. Documentation links checked; Python compile and targeted Ruff pass. Actual current logs/commands/counts are in [TEST_EXECUTION_LEDGER.md](TEST_EXECUTION_LEDGER.md). Test clusters stopped; existing UI/API/DB remain running. Source/HEAD preservation: 608 files across both references unchanged. NO GITHUB PUSH.

## Honest status

Feature1 **PARTIAL** beyond the passed synthetic recorded fixture; first upload/promotion and final export were HTTP, with actual browser playback/rejection/note. Feature2 **PARTIAL** beyond passed controlled replay lifecycle; moving replay had0 eligible incident events. No external rights, incident accuracy, multi-camera capacity, complete crash recovery or production/legal claim. [185-row after audit](POST_INTEGRATION_README_AUDIT_AFTER.md) retains every coverage ID.

## Next ten tasks

1. Browser-only recorded upload→analysis→promotion→approval→export→archive: begin with a real UI file upload.
2. Evidence crash/restart durability: fault-inject a single new ciphertext write.
3. Positive managed model incident: verify a lawful annotated rule fixture first.
4. Two-admin browser config editor/approval/rollback: create one draft in UI.
5. Multi-camera soak/crash expiry: measure two controlled source processes.
6. External rights/SSRF: review one written source authorization before stream access.
7. Original upload retention/quotas: assert refusal before writing a quota-exceeding fixture.
8. Representative evaluation: freeze licensed annotations and model/data hashes.
9. HTTPS secure PWA/patrol: authenticate one real MFA fixture under test TLS.
10. Deployment/key/audit/legal readiness: run an isolated restore/deploy drill.

Detailed owners, boundaries, estimates and acceptance are in [REMAINING_FEATURES_MASTER_BACKLOG.md](REMAINING_FEATURES_MASTER_BACKLOG.md). First user action: open the private operator QR locally, import it into your authenticator, then open http://127.0.0.1:5175/login using the verified credentials in the protected file.
