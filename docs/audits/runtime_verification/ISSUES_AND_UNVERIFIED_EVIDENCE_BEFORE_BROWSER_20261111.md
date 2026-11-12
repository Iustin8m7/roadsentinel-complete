# Current unresolved evidence — 2026-11-10

Login is no longer blocked: verified existing browser password/MFA/dashboard on5175/8003/rsint_20261110b:55446. Narrow lookup repair and additive0022 were applied after verified backup/restore rehearsal. The former claim of unavailable administrator access was disproved by the integration-specific admin role; no original credentials were used.

Remaining unverified items:

1. No genuine annotated real incident clip or representative precision/recall/false-alert evaluation. Frozen positive is explicitly SYNTHETIC TEST.
2. Managed moving replay produced0 eligible incidents; its complete event/evidence/case/export positive run remains unverified.
3. First recorded upload/analysis/promotion and final export approval/download were HTTP. Browser rejection/note/playback passed, but not every step in one browser-only journey.
4. Camera registration and changing preview were browser-tested. Config creation/two-admin approval/revision2 were real authenticated APIs; entire editor/reviewer browser/rollback interaction remains unverified.
5. No external camera rights or external live processing, no physical UVC test. Do not access public catalogs as implied permission.
6. No multi-camera sustained capacity, long soak, abrupt worker-death lease expiry or every outage boundary under real load.
7. No abrupt evidence-write crash/orphan reconciliation or complete case/archive reopened after backend restart. Live authentication session persistence across actual backend restart did pass.
8. PWA unit/lint/type/build pass; current-run trusted HTTPS install/patrol/push/accessibility browser acceptance not run.
9. No production KMS/HSM/SSO/external audit custody/DPIA/legal approval. Hash-verified package is unsigned; heuristic blur is not anonymization.
10. Broader original-upload quotas, intermediate retention and long-term legal-hold resource guarantees remain in backlog.

Safe repeat command: `.venv.integration/bin/python scripts/verify-integration.py flows` from the integration root. It creates/stops its own unique DB/cluster and does not reset the existing runtime. Exact future steps/owners are in REMAINING_FEATURES_MASTER_BACKLOG.md. No host privilege intervention is currently needed for login.

---

# Historical observations below (superseded where noted)

> Current runtime verification — 2026-11-10
> Existing integrated login is now VERIFIED with MFA on5175/8003/rsint_20261110b:55446 after backup/rehearsed narrow lookup-owner repair and0022. Use [FINAL_LOGIN_HANDOFF.md](FINAL_LOGIN_HANDOFF.md), [POST_INTEGRATION_RUNTIME_VERIFICATION.md](POST_INTEGRATION_RUNTIME_VERIFICATION.md) and [FULL_INTEGRATION_E2E_VALIDATION.md](FULL_INTEGRATION_E2E_VALIDATION.md).
> Historical observations below retain their original scope/date.

# Issues and unverified evidence

- Existing integration login is still blocked: actual owner role BYPASSRLS=false, tenant lookups NULL. No existing user/hash enumeration through an RLS bypass was performed; no live login success claimed.
- Positive recorded fixture uses real detections on deliberately frozen licensed imagery. It is synthetic scene timing, not a real-world incident or accuracy validation.
- Full Chromium upload/candidate/promotion/case/export journey not executed. Frontend tests/build cannot prove browser acceptance.
- Managed runtime approval rows are test fixtures. Admin UI/four-eyes approval was not exercised by that test. Read latest log outcome before claiming runtime pass.
- Controlled local source outage/reconnect has passed. Effective approved reconfiguration, multi-camera load/soak and restart durability remain incomplete.
- No external camera machine-processing authorization established, no external frames fetched; external live remains BLOCKED.
- Actual promoted case-package download and SHA-256 manifest/member validation passed. Package is unsigned; independent signature/custody is not claimed.
- Existing integration DB additive migration 0021 not applied; it requires backup and review. Disposable migrations do not prove a retained-data upgrade.
- PWA runtime/browser acceptance and production Compose/restore/push remain unverified.
- Original selected source digests and read-only git metadata can support safety checks; there was no full pre-mission hash baseline of every original private file. No claim of exhaustive private-media comparison.

Use the isolated native runbook and exact test ledger to reproduce. Never satisfy a missing test by weakening authentication, RLS, source rights or model outputs.

## Additional executed acceptance: export and source recovery

After the earlier checkpoint, real HTTP case export uncovered two integration defects: CaseError/ExportError were not registered with the application error mapper (not-ready export answered 500), and approval API approve/deny/revoke did not call the existing export-job transition hook. app.main now registers the existing domain response mapping; app.api.unblur connects on_approval_decided. No policy was bypassed. The expanded real-model test adds a case observation, records the fixture's explicit CC BY 3.0 license through the existing admin grant API, requests export, observes not-ready 409, obtains independent admin approval, generates/downloads the encrypted package through signed authenticated access, and verifies the canonical manifest digest and all member hashes using verify_package. Package remains unsigned: hash integrity is not independent legal custody. **14 passed in 17.29 s** with the approvals suite (case-export-release.log).

The managed test now forcibly interrupts only sockets belonging to its controlled replay server and temporarily refuses reconnection. It observes authoritative reconnecting health, expiry of stale preview (404), restoration of actual frames and healthy state, then stops the worker on disable. **1 passed in 14.70 s** (managed-recovery.log). This does not establish external-live availability or multi-camera capacity. Approved configuration state is still fixture-created; actual two-admin UI activation and revision change remain unverified.

The full original-suite checkpoint was 419 passed + 2 skipped; backend-final-proof.log is the subsequent full run including these added assertions. Consult its final summary before using it as release evidence. Docs checker now works without Git metadata; snapshot omissions and quoted relative links were corrected, with 0 broken links in 85 Markdown files at that checkpoint. README source snapshot is README_BEFORE_SOURCE.txt.
