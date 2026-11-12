# Operator handoff — existing browser login verified

Open **http://127.0.0.1:5175/login**. Backend **http://127.0.0.1:8003**; exact verified DB **rsint_20261110b,127.0.0.1:55446**, revision0022. Operator **operator.a@roadsentinel.local**, tenant **unit-a**, no tenant input required. Admin **admin.a@roadsentinel.local** also verified. Password remains in protected `backend/.integration-test-credentials.json`0600; it is deliberately not reproduced here.

MFA is enabled and already enrolled. Open private `backend/.integration-authenticators/operator.a.html` locally and import its QR into your authenticator, then enter its current code. Or, in your own local terminal only:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local
```

The verification ends with logout; your browser starts a new legitimate MFA session. [fresh native operator dashboard](REAL_BROWSER_SCREENSHOTS/2026-11-11/A-auth-live-operator.png); [five native login journeys](runtime_verification/browser-20261111T011541+0200/auth-final-code.log).

Services are already running. If stopped, the helpers refuse occupied ports and never touch the DB:

```bash
python3 scripts/integration-dev.py backend
python3 scripts/integration-dev.py frontend
```

Equivalent frontend start from `frontend/`: `RS_API_ORIGIN=http://127.0.0.1:8003 VITE_USE_MOCKS=0 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort`. Do not start a competing backend/database or rerun seed blindly.

Prepare safe repeatable inputs with `.venv.integration/bin/python scripts/prepare-browser-fixtures.py`. Use `data/integration-browser-fixtures/LICENSED_MOVING_TRAFFIC.mp4` at Analiză video; confirm crop, draw a count line, request3samples/sec and run. Inspect the90-frame output/heatmap; these are observations, not unique-vehicle accuracy. For deterministic incident-workflow demonstration, use `SYNTHETIC_TEST_frozen_licensed_frame.mp4`,2samples/sec,30second stationary rule, queue disabled. Mark **Material de test sintetic**, enter a reason, explicitly send one candidate to review, open its RECORDED/SYNTHETIC alert and reject/annotate/bookmark. Export requires an actual source export grant and a separate approver; self approval is denied.

To repeat the fully prepared model/browser scenarios without changing native data:

```bash
python3 scripts/verify-integration.py browser
python3 scripts/verify-integration.py camera
```

These create new disposable DBs/ports, seed their own accounts, perform real MFA/browser/model actions, and stop their own resources. Review printed log paths and screenshots. The camera test registers a licensed loopback replay, configures via browser JSON editor, approves with another admin, uses browser Start, observes moving preview, revision2, disconnect/recovery, natural lease expiry, rollback and final disable. Temporary camera/test DB are removed/stopped; they do not remain in your live dashboard. The live DB has not been filled with synthetic demonstration alerts.

Feature1 selected fixture journey passes; full product remains PARTIAL for source-rights UI, complete failure/retention matrix and real-world incident validation. Feature2 controlled replay passes; all-UI onboarding remains PARTIAL because adoption/source grant setup is API-driven and geometry is JSON, not a visual editor. External camera is BLOCKED by rights. No production/legal/accuracy claim. No GitHub write or original project/database change; [608 source hashes and both HEADs unchanged](runtime_verification/browser-20261111T011541+0200/reference-preservation.json).

Read first: REAL_BROWSER_AUTH_MFA_VERIFICATION.md, FEATURE_1_REAL_BROWSER_E2E.md, FEATURE_2_REAL_BROWSER_E2E.md, TEST_EXECUTION_LEDGER_UPDATED.md, README_COVERAGE_UPDATE.md and REMAINING_FEATURES_MASTER_BACKLOG.md.
