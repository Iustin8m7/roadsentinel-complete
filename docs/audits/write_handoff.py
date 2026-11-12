"""Source-anchored audit supplement and reproducible mission handoff. Never invent passing evidence."""
import ast,csv,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'docs/audits';I=R/'docs/implementation'
items=[
('Product/interfaces','frontend/src/App.tsx;secure-pwa/src;backend/app/main.py','backend/tests/test_contract_api.py','P1','PARTIAL','Secure backend authoritative; legacy architecture table contradicts current architecture. PWA browser not exercised.'),
('Detection/tracking','roadsentinel/detector.py;roadsentinel/pipeline.py;models/registry.json','backend/tests/test_mission_vertical.py','P0','VERIFIED REAL INPUT PARTIAL','Actual inference on licensed-derived synthetic frozen fixture; no incident accuracy measurement.'),
('Adapters/rights','roadsentinel/sources.py;roadsentinel/consent.py;roadsentinel/replay.py','tests/test_sources.py;tests/test_consent.py','P0','TESTED SYNTHETIC ONLY','Local adapters tested. External rights not established; no remote media fetched.'),
('Geometry/calibration','roadsentinel/geometry.py;backend/app/services/camera_config.py','tests/test_rules_rates.py','P1','TESTED SYNTHETIC ONLY','Synthetic geometry is not a calibrated real road. No speed certification.'),
('Rule thresholds','roadsentinel/rules.py;backend/app/services/offline_analysis.py','tests/test_rules.py;tests/test_mission_vertical.py','P0','VERIFIED REAL INPUT PARTIAL','Frozen-frame model tracks produce nine candidates; this is not street incident validation.'),
('Critical event types','roadsentinel/rules.py;backend/app/core/catalog.py','tests/test_rules.py','P1','TESTED SYNTHETIC ONLY','Wrong way/pedestrian/crash/object production precision and recall remain unverified.'),
('High event types','roadsentinel/rules.py','tests/test_rules.py','P1','TESTED SYNTHETIC ONLY','Stopped/offline candidate bridge implemented. Physical speed and near miss remain unvalidated.'),
('Medium event types','roadsentinel/rules.py;roadsentinel/rates.py','tests/test_rules_rates.py','P2','TESTED SYNTHETIC ONLY','Sampling constraints matter; no operational validation.'),
('Information/offline rules','backend/app/services/offline_analysis.py','backend/tests/test_mission_vertical.py','P0','VERIFIED REAL INPUT PARTIAL','Line counts stay analytics; only obstruction/queue eligible for explicit recorded review.'),
('Evidence assembly','backend/app/services/offline_promotion.py;backend/app/services/evidence.py;roadsentinel/pipeline.py','backend/tests/test_mission_vertical.py;backend/tests/test_evidence_integrity.py','P0','VERIFIED REAL INPUT PARTIAL','HTTP media + encryption verified for recorded fixture; crash orphan cleanup remains open.'),
('Signed ingestion','roadsentinel/sink.py;backend/app/api/ingest.py;backend/app/services/ingest_auth.py','backend/tests/test_ingest_auth.py;backend/tests/test_ingest_idempotency.py','P0','IMPLEMENTED UNVERIFIED','Use final execution ledger for test-level outcomes; managed fencing newly added.'),
('Operator queue','frontend/src/store/data.ts;backend/app/api/contract.py','backend/tests/test_contract_api.py','P0','PARTIAL','API exercised; new UI source labels compile. Full candidate promotion browser journey not verified.'),
('Decisions/patrol','backend/app/api/contract.py;backend/app/api/patrol.py','backend/tests/test_mission_vertical.py;backend/tests/test_patrol_stats.py','P0','VERIFIED REAL INPUT PARTIAL','Actual HTTP reject tested for recorded fixture. Signs/enforcement remain action labels.'),
('Archive/saved searches','backend/app/services/search.py;backend/app/api/contract.py','backend/tests/test_pagination.py','P1','IMPLEMENTED UNVERIFIED','Tenant-filtered parser and keyset paging exist; browser retrieval of new candidate not yet demonstrated.'),
('Investigation/export','backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py','backend/tests/test_evidence_integrity.py','P0','PARTIAL','Imported API/UI exist. Approval-to-export manifest verification of promoted incident not proven in this mission.'),
('Camera administration','backend/app/api/camera_control.py;backend/app/services/camera_config.py;frontend/src/components/CameraControlPanel.tsx','backend/tests/test_managed_live_runtime.py','P0','PARTIAL','Managed runtime fixture tests do not prove two-admin UI approval workflow.'),
('Clients/accessibility','frontend/src;secure-pwa/src','frontend/src/store/auth.test.ts','P2','PARTIAL','Frontend build and 15 tests pass. PWA browser and accessibility acceptance remain unverified.'),
('Authentication/MFA/RLS','backend/app/services/auth.py;backend/app/db.py;backend/app/bootstrap.py;backend/app/services/seed.py','backend/tests/test_auth.py;backend/tests/test_seed.py;backend/tests/test_isolation.py','P0','PARTIAL','Disposable DB authenticates with mandatory MFA. Existing integration owner BYPASSRLS=false remains blocker; existing DB untouched.'),
('Keys/audit','backend/app/core/crypto.py;backend/app/core/audit.py;backend/app/core/audit_anchor.py','backend/tests/test_crypto.py;backend/tests/test_audit.py','P1','IMPLEMENTED UNVERIFIED','AES-GCM and hash chain exist. Local checkpoint is not independent external custody.'),
('Privacy/legal','roadsentinel/redaction.py;roadsentinel/consent.py;backend/app/services/retention.py','tests/test_privacy_defaults.py;backend/tests/test_retention.py','P0','PARTIAL','Heuristic redaction is not anonymization. No legal/DPIA sign-off or enforcement integration.'),
('Model governance','roadsentinel/models.py;models/registry.json;training','tests/test_models.py','P1','PARTIAL','Stock model hash known; external configurable model path added. No representative evaluated activation.'),
('Real accuracy','docs/LIMITS.md;models/reports','tests/test_evaluation.py','P1','EXTERNALLY BLOCKED','No labeled representative data/approved target metrics. Counts not ground truth.'),
('Offline jobs','backend/app/api/offline_video.py;backend/app/services/offline_analysis.py;backend/app/models/offline_video.py','backend/tests/test_mission_vertical.py;backend/tests/test_offline_video_authz.py','P0','VERIFIED REAL INPUT PARTIAL','Upload/crop/job/candidates/media/review tested over HTTP. Restart/browser/retention matrix incomplete.'),
('Live worker','roadsentinel/remote_config.py;roadsentinel/live.py;roadsentinel/pipeline.py;backend/app/api/camera_worker.py','backend/tests/test_managed_live_runtime.py;tests/test_remote_config.py','P0','PARTIAL','Actual latest outcomes in managed-live and backend-final logs. Do not treat test-owned approval rows as admin acceptance.'),
('Contracts','backend/app/schemas/contract.py;frontend/src/lib/adapters.ts;API.md','backend/tests/test_contract_api.py','P0','PARTIAL','Legacy/secure contract coexist. New origin stored in details; labels added conservatively, unknown source disclosed.'),
('Migrations/seed','backend/alembic;backend/app/services/seed.py','backend/tests/test_isolation.py;backend/tests/test_seed.py','P0','PARTIAL','Fresh cluster tested through 0021. Existing integration not migrated or backed up during mission.'),
('Install/readiness','deploy/docker-compose.yml;frontend/vite.config.ts;backend/app/api/health.py','backend/tests/test_ops_and_authz.py','P1','PARTIAL','Current proxy correct. Compose not executed. Readiness does not mean a camera is online.'),
('Testing/CI','backend/tests;tests;frontend/e2e;.github/workflows/ci.yml','TEST_EXECUTION_LEDGER.md','P1','PARTIAL','Local execution evidence only; no GitHub CI execution or push.'),
('Legacy boundaries','roadsentinel/server.py;web;README.md','tests/test_api.py','P1','PARTIAL','Legacy batch destructive semantics remain isolated; not used for mission E2E.'),
('Optional AI/telemetry','roadsentinel/vlm.py;roadsentinel/tracking.py','tests/test_privacy_defaults.py','P2','IMPLEMENTED UNVERIFIED','External VLM and W&B not enabled in mission; no external data transmission test.'),
('Romanian source catalog','cameras/romanian-source-registry.json;backend/app/services/camera_discovery.py','backend/tests/test_camera_discovery.py','P1','PARTIAL','Catalog restored from original source. Candidates remain ingestion-disabled; no rights or availability claim.'),
('Optional scope','docs/LIMITS.md;README.md','not applicable','P3','NOT APPLICABLE / OPTIONAL','Fog/ice/plate/facial/enforcement/SSO not added. No automatic sanctions.'),
('Reliability/backpressure','roadsentinel/live.py;backend/app/services/camera_control.py','tests/test_live.py;backend/tests/test_managed_heartbeat.py','P0','PARTIAL','Critical queue overflow bounded; stale sequences no longer extend lease. Long soak/multi-camera absent.'),
('Honest presentation','frontend/src/lib/adapters.ts;frontend/src/pages/VideoAnalysisPage.tsx','frontend/src/store/auth.test.ts','P1','PARTIAL','RECORDED/LOCAL REPLAY/SYNTHETIC source prefixes. No external live or accuracy badge inferred.'),
('Integrated guarantees','backend/app/models/camera_control.py;backend/app/models/casework.py;backend/app/models/investigation.py','backend/tests/test_isolation.py','P0','PARTIAL','Tenant table inventory now derived after all models imported. Imported case/control paths need more end-to-end coverage.')]
now=datetime.now(timezone.utc).isoformat()
with (O/'README_COVERAGE_MATRIX.csv').open() as f:rows=list(csv.DictReader(f));fields=list(rows[0])
readme=(R/'README.md').read_text().splitlines()
append=['\n## Mandatory category cross-check (A01–A35)','The paragraph inventory above records source promises; the following categories identify concrete owners and acceptance limits. These statuses are conservative and are not a claim that every linked promise was functionally verified.\n']
for i,(name,code,test,priority,status,limit) in enumerate(items,1):
 aid=f'A{i:02}';rows.append(dict(zip(fields,[aid,'README.md + linked specs','1-'+str(len(readme)),name,status,'VERIFIED REAL END-TO-END',priority,code,test,'TEST_EXECUTION_LEDGER.md',limit])))
 append += [f'### {aid} {name}',f'- Code: `{code}`. Test owner: `{test}`.',f'- Baseline/current limit: {limit}',f'- Final conservative category: {status}; priority {priority}.','']
with (O/'README_COVERAGE_MATRIX.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
(O/'POST_INTEGRATION_README_AUDIT_BEFORE.md').write_text((O/'POST_INTEGRATION_README_AUDIT_BEFORE.md').read_text()+'\n'+'\n'.join(append))
# Actual source route inventory, without importing application settings or printing secrets.
route_lines=['# Architecture and contract map','','```mermaid','flowchart LR','  Source[Authorized source or recorded upload] --> Worker[YOLOX-S + per-camera ByteTrack]','  Worker --> HMAC[Signed event / preview / heartbeat]','  HMAC --> DB[Secure API + PostgreSQL FORCE RLS]','  Upload[Encrypted recording + analysis] --> Promotion[Explicit operator review submission]','  Promotion --> DB','  DB --> Evidence[AES-GCM protected evidence]','  DB --> UI[React operator and secure PWA]','  UI --> Decision[Human confirm/reject + audit]','```','','The secure backend is authoritative. Offline promotion is an authenticated human action, not an unsigned replacement for HMAC machine ingestion. Queue acceptance is not incident confirmation. Recorded capture time is unverified; detected_at is submission time and source_pts_ms carries media position.','', 'Migrations: 0001–0015 → rsint_cam1 → rsint_case1 → rsint_run1 → rsint_case2 → 0020 → 0021. 0021 adds two offline tenant indexes only. Existing integration DB not migrated.','','## Registered router declarations (source inspection)','Method/path | Function/source | Authentication evidence','---|---|---']
for p in sorted((R/'backend/app/api').glob('*.py')):
 text=p.read_text();prefix=re.search(r'router\s*=\s*APIRouter\(prefix="([^"]*)"',text);prefix=prefix.group(1) if prefix else ''
 try:tree=ast.parse(text)
 except SyntaxError:continue
 for node in ast.walk(tree):
  if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
  for d in node.decorator_list:
   if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr in ('get','post','put','patch','delete') and d.args and isinstance(d.args[0],ast.Constant):
    signature=ast.unparse(node.args);auth='HMAC service principal' if 'get_service_principal' in signature else 'session + declared permission' if any(s in signature for s in ['Principal','require','READ','MANAGE']) else 'inspect source (auth dependency may be indirect/public)'
    route_lines.append(f'{d.func.attr.upper()} {prefix}{d.args[0].value} | `{p.relative_to(R)}:{node.lineno}` `{node.name}` | {auth}')
route_lines += ['','## Key new contract','POST /api/recordings/{recording_id}/analyses/{run_id}/candidates/{index}/promote: session, CSRF, alerts:create AND videos:analyze; completed tenant-owned run and authenticated output required. Body reason (10–500 chars), optional synthetic_test flag. Returns numeric canonical event id, origin=recorded_upload and duplicate flag. 403 unauthorized; 404 tenant/job/candidate hidden; 409 output/PTS unavailable; 422 analytics-only candidate or invalid fields; 503 encoder unavailable. Alert remains new until existing decision route acts. Advisory lock per tenant/recording serializes retries; event_key=offline:<run>:<index>.','Managed heartbeat adds worker_epoch, seq and optional telemetry (validated old Heartbeat shape). Reply carries lease/directive/desired revision. Legacy telemetry body retains 204 behavior. Managed preview/event requires current unexpired epoch and acknowledged active revision.','Camera desired config now includes source_fingerprint, never the source URL. Local worker maps replay reference to an explicit loopback-only source; config revision change exits current tracker process for Supervisor restart. No tracker identity is shared between cameras.']
(O/'ARCHITECTURE_AND_CONTRACT_MAP.md').write_text('\n'.join(route_lines))
(I/'FEATURE_01_AI_INCIDENT_TO_OPERATOR.md').write_text('''# Recorded AI candidate to operator review

Implemented entrypoints: app.api.offline_analytics.promote_candidate → app.services.offline_promotion.promote. Existing app.api.offline_video owns upload/crop/jobs. Existing offline_analysis owns actual YOLOX-S + Supervision ByteTrack, output redaction, encrypted output and observation artifacts. No second incident API or worker stack was created.

Only possible_obstruction → stopped_on_road and traffic_queue → congestion are promotable. Counting crossings remain analytics. Operator/admin requires both videos:analyze and alerts:create. The source run must be completed, in the tenant, with completed observations and output. Human enters a reason. Source metadata remains in alert.details with recording/run IDs, candidate index, PTS, model identity/hash, limitations, review_only, synthetic flag and source note. Capture wall-clock time is explicitly unverified. No dispatch or automatic confirmation occurs.

A per-recording transaction advisory lock serializes camera creation and promotion. Existing event key returns the same numeric alert ID. An internal disabled recorded-source camera owns the canonical alert FK; it is not a runnable live camera. Media is extracted from the already redacted annotated output, not raw uploads. Keyframe and up-to-six-second clip use the output timestamp, clipped at boundaries. Encoder is deadline-bounded; files >50MiB refused. Temporary extraction directories are context-managed. Existing evidence service stores AES-GCM ciphertext, SHA-256 metadata and has_original=false. Existing session-bound signed media URLs deliver bytes.

React VideoAnalysisPage now offers a reason field and explicit submission only to permitted users. OfflinePromotion links to /app/alerte/{id}. adaptEvent exposes RECORDED, LOCAL RECORDED REPLAY, SYNTHETIC TEST or SOURCE UNVERIFIED in the rule summary, including archive/queue consumers. Existing decision, case notes/bookmarks and export routers remain canonical.

Current evidence: vertical-final.log, test_mission_vertical.py. Actual HTTP upload/crop/analysis/candidates/promotion/media/reject ran against independent PostgreSQL; real ONNX inference on a frozen licensed frame produced 60 samples and 9 candidates. Synthetic frozen footage exercises temporal mechanics, not real incident accuracy. The source is Editor, Street traffic.webm, CC BY 3.0 (Wikimedia Commons), original SHA in docs/YOLO_REAL_INFERENCE_REPORT.md. No original media copied into repository.

Still open: full browser candidate-to-case journey; approval/export hash proof for a promoted alert; restart/crash cleanup; concurrent transaction stress; raw-upload expiration/retention policy enforcement; representative moving real-world positive incidents and negatives. Existing evidence writes may leave encrypted orphan objects if a later transaction fails; do not claim crash-atomic storage cleanup. The offline dwell rules use a confirmed crop, not a certified prohibited-stopping zone, and must remain triage candidates.

Run isolated acceptance using INTEGRATED_BROWSER_DEMO_RUNBOOK.md; do not point fixtures at the existing integration DB.
''')
(I/'FEATURE_02_AUTHORIZED_LIVE_CAMERA.md').write_text('''# Authorized camera control to real inference

Canonical lifecycle remains roadsentinel.live.Supervisor → roadsentinel.pipeline.run. New roadsentinel.remote_config.ManagedCamera connects existing HMAC RemoteSink to GET /api/ingest/cameras/{slug}/config, managed heartbeat lease and config/ack. No new broker or task framework.

Before source open, worker obtains runnable active configuration and lease. Private YAML retains source endpoint; backend sends fingerprint only. Managed replay network input must be an explicit literal-loopback replay. Approved zones/rules/thresholds/calibration override profile values. Actual model id/hash and decoded reference dimensions are checked before ACK. Managed target_fps bounds model processing. A revision change, revocation, disable or lease loss raises an error at the next bounded poll; existing supervisor restarts at a clean tracker boundary and cannot reacquire while disabled. External source access still requires SourceSpec consent; external rights were not established in this mission.

Managed heartbeat validates HeartbeatIn and nested measured telemetry against the existing Heartbeat schema. Authoritative CameraWorkerStatus receives epoch/sequence, lease, revision, health and metrics; compatibility camera.status_info retains measured source/detections/tracks/traffic for React. Stale sequences cannot extend a lease. Duplicate worker gets stop. ACK requires a current lease and active version. Evidence and preview writes from managed cameras are fenced by epoch/lease/active acknowledged revision, in addition to HMAC and camera scope. A lease acquisition alone does not imply observed frames: state remains starting until model tracking processes frames; idle capture becomes reconnecting.

RemoteSink preview adds epoch/revision to its signed query, and incident details carry origin and config revision. Existing latest-only preview cache, redaction, bounded JPEG queue and rule/evidence publisher remain in use. Critical-only bounded queues now reject rather than grow past the configured limit. Camera runtime derives offline separately from stale.

Test-managed authorization records are explicit fixtures; they do not certify source-owner permission or prove two-admin approval UI. Read managed-live.log and backend-final.log for actual outcomes. tests/test_remote_config.py tests revocation/revision/model mismatch without networks. test_managed_heartbeat.py tests real signed lease arbitration. test_managed_live_runtime.py exercises actual replay/model/ACK/changing preview/disable using loopback HTTP and disposable PostgreSQL.

Remaining acceptance: supervised reconnect/backoff during forced outage, approved revision roll-forward/rollback browser flow, multi-camera stress/soak, evidence export for model-derived live candidates, backend-driven worker start against arbitrary approved private profile (existing controls retain their allowlist), robust max-retry/source-timeout reconciliation, and independently authorized external live. No physical camera or external stream was used. The full feature remains PARTIAL until these gates pass.
''')
# Concrete ranked remaining work, not implementation claims.
backlog=[
('Finish existing integration authentication','A18,A26','P0','backend/app/bootstrap.py; scripts/repair-integration-dev-auth.sh','Take a restorable integration-only backup, verify current DB/process identity, restore lookup-owner role via guarded script, inspect hashes and complete real MFA login. Do not seed blindly.'),
('Recorded promotion browser and authorization matrix','A10,A12,A18,A23','P0','frontend/src/components/OfflinePromotion.tsx;backend/tests/test_mission_vertical.py','Run two tenants and operator/admin/patrol/auditor over real HTTP/Chromium; candidate submission, duplicate clicks, media, decision, archive and restart must retain the same event.'),
('Managed control configuration lifecycle','A16,A24,A33','P0','roadsentinel/remote_config.py;backend/app/services/camera_control.py','Exercise actual two-admin config creation/approval/activation through API/UI, then require ACK and event revision matching across an approved change and rollback.'),
('Camera outage recovery and multi-camera resources','A03,A24,A33','P0','roadsentinel/live.py;roadsentinel/pipeline.py;backend/tests/test_managed_live_runtime.py','Interrupt and restore a test-owned MJPEG source; assert degraded/offline/recovered states, bounded threads, queues, memory and no duplicate evidence across two cameras.'),
('Evidence transaction crash recovery','A10,A11,A19','P0','backend/app/services/evidence.py;backend/app/services/offline_promotion.py','Fault-inject between ciphertext writes and DB commit; register only test-owned pending objects, remove on rollback or reconcile durable journal; never delete pre-existing evidence.'),
('Promoted case export and approvals','A15,A19','P0','backend/app/api/investigation.py;backend/app/api/casework.py;backend/app/services/package_verify.py','Promote a model-derived candidate, create note/bookmark/legal hold, obtain required independent approval, download package and verify every hash/manifest with negative permissions.'),
('Offline temporal rules and timebase validation','A04,A05,A09,A23','P1','backend/app/services/offline_analysis.py;roadsentinel/rules.py','Add moving/occluded/shake/outside-zone negatives and stable event intervals under PTS shifts/sample changes; preserve analytics-only crossings and do not relax dwell for demo.'),
('Retention and upload quotas','A10,A20,A23','P1','backend/app/services/offline_video_storage.py;backend/app/services/retention.py','Define bounded original/intermediate/job retention and per-tenant quotas with legal hold and interrupted-job recovery; run cleanup solely on fresh fixtures.'),
('Representative model evaluation and governance','A02,A21,A22','P1','models/registry.json;training;docs/LIMITS.md','Obtain licensed labeled multi-condition footage and approved metrics; measure precision/recall/false alerts/hour/count errors; activate only reviewed hashes. External approval needed.'),
('Secure PWA and deployment/restore acceptance','A17,A27,A28,A29','P1','secure-pwa;deploy;docs/OPERATIONS.md','Locked install/build and real HTTPS MFA/patrol/accessibility/push browser checks, then backup/restore drill on independent resources. No original DB mutation.')]
lines=['# Remaining features master backlog','',f'Updated {now}. Estimates below are rough engineering estimates, not delivery commitments. Both selected vertical slices retain unverified gates.','']
for n,(name,ids,prio,paths,step) in enumerate(backlog,1):
 lines += [f'## B{n:02} {name}',f'- Priority {prio}; requirements {ids}; rough complexity '+('2–5 days.' if n<9 else '1–3 weeks plus external dependencies.'),f'- Current state: PARTIAL / UNVERIFIED. Owners: `{paths}`.',f'- First testable action: {step}','- Required boundaries: tenant/RLS/MFA/CSRF/HMAC and source rights stay enforced; fixture cleanup may only touch mission-owned resources.','- Failure cases: unauthorized tenant/role, retry, stale revision, missing media/model and mid-operation restart.','- Definition of done: actual user-visible workflow and negative tests pass with reproducible logs; update coverage IDs using observed evidence.','']
lines += ['## Remaining category-specific acceptance','']
for n,item in enumerate(items,1):lines += [f'- A{n:02} {item[0]} ({item[3]}): {item[5]} Owners `{item[1]}`; next tests `{item[2]}`.']
lines += ['','## External and optional work','Production KMS/HSM, independent audit custody, approved DPIA/legal basis/retention, SSO, approved push devices, real external camera rights and representative data remain externally blocked. Fog/ice, plate/facial recognition and real enforcement are not scope defaults. No automatic enforcement should be inferred from action labels.']
(O/'REMAINING_FEATURES_MASTER_BACKLOG.md').write_text('\n'.join(lines))
(O/'FUTURE_FEATURE_IMPLEMENTATION_PROMPTS.md').write_text('# Future implementation prompts — NOT delivered\n\n'+'\n\n'.join(f'## {n:02} {name}\nWork only in the integration directory. Treat originals and all existing databases as read-only. Address {ids} ({prio}) in {paths}. {step} Before writes, establish disposable test ownership; preserve current contracts, mandatory auth/MFA/CSRF/RLS/HMAC, source permission and evidence. Add fault/authorization/idempotency coverage and run real HTTP/browser where relevant. Record exact counts and do not claim blocked acceptance. Completion requires the stated user-visible test and updated audit ledger.' for n,(name,ids,prio,paths,step) in enumerate(backlog,1)))
(O/'SECURITY_PRIVACY_REGRESSION.md').write_text('''# Security and privacy regression

Protected existing integration DB: identity queried only in READ ONLY transaction context, rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b. Owner role remains non-BYPASSRLS; no mutation or migrations applied. Temporary cluster independently initialized under unique /tmp/rsmission-* root on 55479; per-suite target names rsmission_*. Fixture now requires exact reset name and expected server port before DROP; runtime app role stays NOBYPASSRLS.

Mandatory MFA retained; test authentication uses generated fixtures and actual TOTP. No exemptions enabled. Unsafe session actions require existing CSRF middleware. Machine writes require exact-body HMAC, time/nonce checks, service-account-derived tenant and camera scope. Managed writes additionally require active config/lease/epoch/ACK. New promotion requires both video-analysis and alert-create permission; RLS/job scope is checked before decryption. Evidence media remains authenticated and user-bound; no static public path added. Source fingerprints omit credentials/query strings. Literal loopback replay is explicit and cannot masquerade as external live.

No external source permission was assumed. Redaction remains heuristic and is inherited from analysis output. No face recognition or persistent person identity added. Counts and speed remain unvalidated. No DPIA/legal-compliance or official evidence-admissibility claim is made. Audit hash chains are not independent external anchors.

Open risks: rollback orphan ciphertext, recorded capture-time uncertainty, upload retention/quota gaps, source DNS/redirect threat validation for external networks, long-stall reader thread recovery, full approval/export regression, live-source grant record scope enforcement on all legacy routes. Consult the final ledger for tests actually executed; code presence alone does not close these findings.
''')
(O/'INTEGRATED_BROWSER_DEMO_RUNBOOK.md').write_text('''# Isolated native runbook

Do not point pytest at an existing developer DB. The current integration at http://127.0.0.1:5175/login and http://127.0.0.1:8003 has a confirmed lookup-owner configuration issue. Its credentials file is backend/.integration-test-credentials.json (never print). Existing databases are preserved.

## One-time isolated test setup

Use Python 3.12, Node >=22.12 and PostgreSQL binaries already installed. Create a unique test cluster (example; retain the printed path for shutdown):

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
TASK_DIR=$(mktemp -d /tmp/rsmission-XXXXXXXX)
PG_BIN=/home/justin7m8/miniconda3/envs/rs-pg/bin
"$PG_BIN/initdb" -D "$TASK_DIR/pg" -U postgres -A trust --encoding=UTF8 --no-locale
"$PG_BIN/pg_ctl" -D "$TASK_DIR/pg" -l "$TASK_DIR/pg.log" -o "-h 127.0.0.1 -p 55479 -k $TASK_DIR" start
```

Check that port 55479 is unused first. Trust auth is only for this loopback disposable cluster, never an operational setup. The test fixture proves identity and requires reset opt-in. A dedicated integration venv is preferred; use backend/requirements.lock and requirements.txt with supervision==0.30.7 and onnxruntime==1.23.2, then pytest/httpx. Do not install into the original .venv. This mission executed the already installed original interpreter read-only with PYTHONDONTWRITEBYTECODE=1; it did not install into that environment.

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 \\
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55479/postgres \\
RS_TEST_DATABASE_NAME=rsmission_demo RS_TEST_ALLOW_DATABASE_RESET=rsmission_demo \\
RS_TEST_EXPECTED_PORT=55479 RS_MISSION_REAL=1 \\
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \\
PYTHONPATH=.. /home/justin7m8/Documents/roadsentinel/.venv/bin/python -m pytest tests/test_mission_vertical.py tests/test_managed_live_runtime.py -o addopts='' -q -s
```

Model is read-only from the approved local path; verify its registry SHA first. /tmp/Street_traffic.webm is the previously documented Editor CC BY 3.0 sample; no download or rights inference from a public camera URL. The recorded positive fixture intentionally freezes a licensed frame and is SYNTHETIC TEST, not a real obstruction.

## Standard integration UI start

After separately backed-up and guarded authentication repair, start only the integration backend from backend/ using its protected environment file, restricted role, and mandatory MFA. Do not paste secrets to terminal output. Existing processes are preserved by this mission.

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/frontend
RS_API_ORIGIN=http://127.0.0.1:8003 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Only run this when no verified integration frontend already owns 5175. Backend canonical command from backend/: `python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8003`; load the protected integration environment without printing secrets. Do not run migrations/seed against the existing DB until backup, identity and migration review are complete. The earlier guarded repair script requires privileged role repair; this mission has not run it.

Sign in, enroll TOTP with QR/manual secret and save recovery codes privately. /app/analiza-video → permitted upload → confirm crop → analyze → candidate → enter reason → explicit review submission → /app/alerte/{id}. Verify RECORDED label and media, then human reject/confirm. Archive and case panels are existing routes; full browser journey is still an acceptance task, not an executed demo claim.

For managed replay use the existing private YAML source profile plus approved control configuration. `control_source_reference: replay://<registered-ref>` maps to a literal loopback stream, with `source_replay: true` and licensed scope. HMAC service account must be camera-scoped. Run `python -m roadsentinel.live <private-profile.yaml> --status <integration-owned-state-path>`; source/keys are local protected configuration, never doc literals. Worker refuses missing model/hash/config/permission, ACKs after actual decoded frame dimensions, and exits on revision/lease change. No automatically approved camera or secret-bearing canned production profile is provided.

Stop only owned test services with their handles; shutdown only `$TASK_DIR/pg` using pg_ctl. Never stop PostgreSQL 55446/55444/55432 or unrelated UI/API ports.
''')
(O/'ISSUES_AND_UNVERIFIED_EVIDENCE.md').write_text('''# Issues and unverified evidence

- Existing integration login is still blocked: actual owner role BYPASSRLS=false, tenant lookups NULL. No existing user/hash enumeration through an RLS bypass was performed; no live login success claimed.
- Positive recorded fixture uses real detections on deliberately frozen licensed imagery. It is synthetic scene timing, not a real-world incident or accuracy validation.
- Full Chromium upload/candidate/promotion/case/export journey not executed. Frontend tests/build cannot prove browser acceptance.
- Managed runtime approval rows are test fixtures. Admin UI/four-eyes approval was not exercised by that test. Read latest log outcome before claiming runtime pass.
- Forced source outage/reconnect, effective approved reconfiguration, multi-camera load/soak and restart durability remain incomplete.
- No external camera machine-processing authorization established, no external frames fetched; external live remains BLOCKED.
- No actual case-package download/manifest/signature validation for promoted incident; code imported is not proof.
- Existing integration DB additive migration 0021 not applied; it requires backup and review. Disposable migrations do not prove a retained-data upgrade.
- PWA runtime/browser acceptance and production Compose/restore/push remain unverified.
- Original selected source digests and read-only git metadata can support safety checks; there was no full pre-mission hash baseline of every original private file. No claim of exhaustive private-media comparison.

Use the isolated native runbook and exact test ledger to reproduce. Never satisfy a missing test by weakening authentication, RLS, source rights or model outputs.
''')
print('Wrote source maps, feature documents and ranked backlog; final outcomes must be appended from logs.')
