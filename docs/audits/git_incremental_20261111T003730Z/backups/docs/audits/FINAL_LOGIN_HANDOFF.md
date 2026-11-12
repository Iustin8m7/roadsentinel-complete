> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Verified existing login — YES

Open **http://127.0.0.1:5175/login**. API **http://127.0.0.1:8003** uses **rsint_20261110b@127.0.0.1:55446**, revision0022.

Operator: **operator.a@roadsentinel.local**, tenant **unit-a** (no tenant field). Password is unchanged and actually tested: use `backend/.integration-test-credentials.json` (0600). Admin **admin.a@roadsentinel.local** was also verified with the same saved development password.

MFA is enabled and already enrolled by the browser verification. Locally open `backend/.integration-authenticators/operator.a.html`, scan its private QR into your authenticator, and enter the current six-digit code when logging in. Alternatively run `.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local` to compute the real development TOTP. Do not share QR/secrets/recovery codes.

Actual Chromium proof: [operator dashboard](runtime_verification/screenshots/live-operator.png), [network/result evidence](runtime_verification/live-browser-result.json). The last successful journey includes authenticated role/dashboard data, refresh and logout followed by401. No remaining host privilege blocker for login. [Copy/paste quickstart](OPERATOR_DEMO_QUICKSTART.md).

Both broader AI features remain PARTIAL despite successful isolated fixture journeys: no claim of real incident accuracy, external camera rights, complete live-incident export or production readiness. Originals preserved; NO GITHUB PUSH.
