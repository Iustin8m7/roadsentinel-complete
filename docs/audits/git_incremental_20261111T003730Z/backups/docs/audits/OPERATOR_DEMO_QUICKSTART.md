> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Operator demo quickstart — existing login verified

The current UI/API/database are running. Start with the existing instance; do not seed or run migrations again.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
xdg-open backend/.integration-authenticators/operator.a.html
xdg-open http://127.0.0.1:5175/login
```

The first command opens a private development QR. Scan it into your own authenticator. It contains secret material: keep it local. These accounts were enrolled during the actual browser test, so login now shows a six-digit challenge rather than new enrollment.

- Tenant: unit-a; no tenant input field is required.
- Operator: `operator.a@roadsentinel.local`.
- Admin: `admin.a@roadsentinel.local` (use its own admin.a.html QR).
- Password: existing, unchanged, verified value in `backend/.integration-test-credentials.json` (0600). It is shown once in the interactive final handoff; do not paste it into docs/logs.
- Enter the current TOTP from the imported QR. Dashboard: `/app`. Auditor: `/app/audit`.
- Save recovery codes privately from `backend/.integration-authenticators/authenticators.json`; no shared screenshot/log should contain them.

Without a phone, local development can compute its genuine enrolled second factor:

```bash
.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local
```

Never store the printed code in a shared log. TOTP is replay protected; wait for the next30-second interval if already consumed. MFA is not disabled.

## Check or start only integration services

```bash
curl --fail http://127.0.0.1:8003/api/health/live
curl --fail http://127.0.0.1:5175/api/health/live
```

If a service is stopped, start only that service:

```bash
python3 scripts/integration-dev.py backend
python3 scripts/integration-dev.py frontend
```

The helper refuses occupied ports. For a necessary restart use `--restart-pid <verified integration PID>`; it checks user/cwd/command/DB target before signaling. It never stops PostgreSQL. Backend uses `.venv.integration`; frontend starts with explicit `RS_API_ORIGIN=http://127.0.0.1:8003` and mocks off. Alternative foreground frontend command:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/frontend
PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH RS_API_ORIGIN=http://127.0.0.1:8003 VITE_USE_MOCKS=0 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Do not launch a competing frontend/backend while their ports are occupied. Private owned logs/PID metadata: `backend/.integration-runtime/`. API development schema path is `/api/openapi.json`; `/openapi.json` is not the configured path.

## Actual fixture demonstrations without contaminating the existing DB

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/verify-integration.py flows
```

This runs actual Chromium and actual model/HTTP against a newly created disposable DB, with its own Vite/API/replay servers. Evidence/logs and exact commands go to `docs/audits/runtime_verification/runs/<unique>/`; all owned servers stop afterward. It does not fill your dashboard with artificial cases.

For your own permitted media, use `/app/analiza-video`: upload, confirm crop, start analysis, inspect eligible obstruction/queue candidates and explicitly send for review. This is recorded evidence; it is never live dispatch. `/app/alerte/<id>` shows media/rejection/case notes. The camera demo uses `/app/camere`: registration, control/source/grant/version workflow, separate administrator approval, lease/ACK and real preview. Sources without documented rights must remain disabled. See the two feature implementation reports for configuration contracts. Not every real clip will generate an incident; zero events is a valid outcome.

## Login repair diagnostics (normally unnecessary now)

```bash
bash scripts/repair-integration-dev-auth.sh
```

Default is inspection only. Do not rerun privileged changes simply to log in. If repair is needed after independent changes, the sole guarded `--apply` path verifies exact server system ID, private backup, isolated restore/rehearsal and row preservation. No reset or password overwrite occurs. See INTEGRATED_LOGIN_RECOVERY_REPORT.md for the backup/rollback limitations.
