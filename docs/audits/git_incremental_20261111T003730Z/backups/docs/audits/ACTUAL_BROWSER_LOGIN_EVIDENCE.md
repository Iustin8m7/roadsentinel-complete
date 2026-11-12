> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Actual existing-browser login evidence — PASS

Runtime **A**, not an ephemeral substitute: Chromium accessed `http://127.0.0.1:5175/login`; Vite proxied to actual FastAPI 8003; its process URL and live DB queries verified rsint_20261110b on 127.0.0.1:55446. Password was read from the existing protected credential file. No credential is repeated here.

| Account | Real backend role | Observed browser behavior |
|---|---|---|
| operator.a@roadsentinel.local | operator | Wrong password 401; correct password 200 + MFA required; visible QR; valid TOTP; eight recovery codes held until acknowledgement; /app; refresh; protected APIs; logout. Then normal TOTP sign-in again. |
| admin.a@roadsentinel.local | tenant_admin | QR enrollment, TOTP, recovery acknowledgement, /app; users API allowed; logout. |
| patrol.a@roadsentinel.local | patrol | QR enrollment, /app; users and audit verify forbidden; no unauthorized stats request; logout. |
| auditor.a@roadsentinel.local | auditor | QR enrollment, /app/audit; real audit chain data; events forbidden; logout. |

Executed `PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH node frontend/e2e/live-login-recovery.mjs`. First run: five successful journeys, no JavaScript page errors. [Original enrollment result](runtime_verification/live-browser-enrollment-result.json), [original log](runtime_verification/live-browser-enrollment.log). A subsequent run verifies completed dashboard loading/empty state, not only navigation or HTTP status; see [latest result](runtime_verification/live-browser-result.json) and [latest log](runtime_verification/live-browser-loaded.log). Screenshots are taken only after MFA, with no password/QR/recovery material:

- [Operator dashboard](runtime_verification/screenshots/live-operator.png)
- [Tenant administrator](runtime_verification/screenshots/live-tenant_admin.png)
- [Patrol dashboard](runtime_verification/screenshots/live-patrol.png)
- [Auditor view](runtime_verification/screenshots/live-auditor.png)

The sanitized network trace in the result includes only role/method/path/status. Protected `/api/auth/me` returns 200 after MFA and 401 after logout. `/api/users` returns 200 for tenant admin and 403 for the other three roles. `/api/audit/verify` returns 200 for admin/auditor and 403 for operator/patrol. Auditor `/api/events` returns 403 as required. Browser reload preserves identity. An actual owned backend process restart preserved a previously issued session, followed by a successful logout and subsequent 401: [restart-session.json](runtime_verification/restart-session.json).

The existing integration contains no test incidents/cameras from these browser login tests. An empty queue is a legitimate completed response. The fixed dashboard shows Nicio alertă de verificat instead of permanent loading. No demo/mock alert was inserted to disguise the empty tenant.

MFA is now enrolled for those four development accounts. To use a phone, locally open the corresponding private `backend/.integration-authenticators/<email-prefix>.html` and scan its QR into your authenticator. Then login asks for its current six-digit code. The local helper `scripts/integration_totp.py <email>` reads the enrolled secret under mode-0600 protection and computes a genuine TOTP; it does not exempt or bypass MFA. Do not share these files. Codes are single-use within their time step; if an immediately repeated code is rejected, wait for the next 30-second step.
