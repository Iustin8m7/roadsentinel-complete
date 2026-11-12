# Browser handoff — integrated main through 47e3e85

Open **http://127.0.0.1:5175/** for the public prototype page or **http://127.0.0.1:5175/login** for the real application. Backend is **http://127.0.0.1:8003**. The native runtime remains on `rsint_20261110b@127.0.0.1:55446`, revision0022. No migration is needed for this incremental port.

## Existing accounts

Tenant `unit-a`; operator `operator.a@roadsentinel.local`, administrator `admin.a@roadsentinel.local`, patrol `patrol.a@roadsentinel.local`, auditor `auditor.a@roadsentinel.local`. Password is in **`backend/.integration-test-credentials.json`**, mode0600. Do not paste it into logs/reports/commands. It was accepted by the native backend and genuine Chromium after the owned restart; it was not reset.

MFA remains mandatory. These development identities are already enrolled. If automation just consumed the current code, wait for the authenticator's next30-second code; replay rejection is intentional. Use the existing private QR setup files in `backend/.integration-authenticators/` with your phone authenticator. The local `scripts/integration_totp.py` helper is development-only; its output is secret and must not be captured in evidence. Operator/admin/patrol reach `/app`; auditor reaches `/app/audit`. The new editor does not bypass distinct-administrator approval.

## Safe normal start/check

If services are already running, use them; do not launch duplicates.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
curl --fail http://127.0.0.1:8003/api/health/live
curl --fail http://127.0.0.1:5175/api/health/ready
# Only when the corresponding integration service is stopped:
python3 scripts/integration-dev.py backend
python3 scripts/integration-dev.py frontend
```

The frontend launcher always supplies `RS_API_ORIGIN=http://127.0.0.1:8003`, mock mode off, loopback5175 and `--strictPort`. For a manual foreground frontend start:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/frontend
PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH RS_API_ORIGIN=http://127.0.0.1:8003 VITE_USE_MOCKS=0 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Do not run this while5175 is occupied. No production port default was changed.

## Repeat the controlled journeys

The preferred commands below create fresh own DBs/services/fixtures, execute real Chromium and model paths, then stop only their own processes. They require the existing licensed `/tmp/Street_traffic.webm`, verified local YOLOX ONNX asset and integration dependencies; they do not download an unknown model or camera.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
python3 scripts/verify-integration.py browser
python3 scripts/verify-integration.py camera
```

Results go under `docs/audits/runtime_verification/runs/<new-UTC-tag>/` by default. Add `--evidence-root docs/audits/<owned-directory>` to segregate a rerun. Commands contain no credentials. Each run has exact DB identity, logs, screenshots and schema-security output. The camera run deliberately waits for natural90-second lease expiry; this is not a frozen UI. Test services/DBs are stopped at completion, so test-created cameras/cases are not left in the native tenant.

Recorded sequence: menu **Analiză video** → upload moving licensed30-second clip → ROI/counting line → actual90 sampled frames → annotated playback/heatmap/counts → separately labeled frozen SYNTHETIC TEST positive → explicit review promotion → source-marked alert → reject with reason → note/bookmark → distinct admin export approval → generate/download ZIP → verify hashes/tampered copy → restart/API/browser archive persistence. The synthetic event is not a genuine road incident.

Camera sequence: **Camere → Adaugă cameră → Control și configurare** → declare local replay source and exact processing/recording/export grant → visual editor (reference1920×1080, polygon, line, rules and10FPS) → submit revision → distinct eligible administrator approves/activates → UI worker Start with the test-owned allowlisted YAML profile → exact lease/ACK revision → changing real model preview → tile **Înregistrare**, 1×/pause/seek/206 → **Istoric**, exact server camera filter → revise/approve/ACK2 → disconnect/reconnect → own worker crash/natural lease expiry → rollback/ACK1 → disable → revoke grant and deny old recording URL.

The local worker profile contains camera acquisition/consent, not DB/admin/master keys. The harness owns/removes only its generated profile. Production/external source credentials are never exposed by these commands. A typed public camera URL is not processing permission.

## Inspect evidence

- [Native after-restart role login log](native-final-browser.log) and [network/status assertions](native-final/live-browser-result.json).
- [Native operator dashboard](native-final/screenshots/live-operator.png), [admin](native-final/screenshots/live-tenant_admin.png), [auditor](native-final/screenshots/live-auditor.png).
- [Detailed run/test index](GITHUB_INTEGRATION_TEST_LEDGER.md) links actual current-run moving inference, visual editor, recording player, report PDF, approval/export and recovery screenshots.

Remaining limits: external source rights/field accuracy, exact VFR gap preservation and legacy media without timing metadata, long-running multi-camera capacity, comprehensive crash-spool/retention/quota tests, installed HTTPS PWA and a complete accessibility audit. The source delta is not a production-readiness certificate.
