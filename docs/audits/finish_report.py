import csv, json, re
from pathlib import Path
from datetime import datetime, timezone
R=Path(__file__).resolve().parents[2];O=R/'docs/audits'
# Sanitize retained execution traces before they become handoff artifacts.
for p in O.glob('*.log'):
 s=p.read_text(errors='replace')
 s=re.sub(r"(totp_secret|password|secret|refresh_token|access_token)(\s*=\s*|['\"]\s*:\s*['\"])(['\"]?)[A-Za-z0-9_+/.=:-]{8,}",r'\1=<REDACTED>',s,flags=re.I)
 s=re.sub(r'(postgresql(?:\+psycopg)?://[^:/\s]+:)[^@\s]+@',r'\1<REDACTED>@',s)
 s=re.sub(r'([?&]sig=)[^&\s\"\']+',r'\1<REDACTED>',s)
 p.write_text(s)
ledger=['# Test execution ledger','','All tests in this mission ran in the agent-visible environment on the native loopback network. Original services were not restarted. Artifact timestamps below are UTC file completion/modification times, not instrumented command start times. pytest durations/counts are copied from actual output. Shell exit codes were not persisted uniformly; passing summaries establish test outcome but are not invented process telemetry.','','## Guarded database command used','', '''```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 \\
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \\
RS_MISSION_REAL=1 \\
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55479/postgres \\
RS_TEST_DATABASE_NAME=rsmission_release RS_TEST_ALLOW_DATABASE_RESET=rsmission_release \\
RS_TEST_EXPECTED_PORT=55479 PYTHONPATH=.. \\
/home/justin7m8/Documents/roadsentinel/.venv/bin/python -m pytest tests -o addopts='' -q
```''','Final full result: **419 passed, 2 skipped, 11 warnings in 109.86 s**. The suite includes actual model/HTTP/Chromium tests via RS_MISSION_REAL=1; older opt-in tests test_real_yolo_e2e and test_offline_analytics_real_video remained skipped because their separate flags were not enabled. No skipped test was counted as passing.','','Final focused rerun used rsmission_negatives and `tests/test_mission_vertical.py tests/test_managed_live_runtime.py tests/test_managed_heartbeat.py -o addopts=\'\' -q -s`: **3 passed in 18.32 s**. This added explicit cross-tenant/patrol/auditor promotion denials and private media denial. The same test verifies UI duplicate submission returns the original alert.','','Database final inspection: rsmission_negatives / 127.0.0.1 / 55479 / postgres; Alembic 0021; **32 tables ENABLE + FORCE RLS**. rs_test_app BYPASSRLS=false, rs_test_owner BYPASSRLS=true. Existing integration READ ONLY identity: rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b; lookup owner rsint_owner_261110b BYPASSRLS=false; platform/unit-a lookups NULL. Administrator connection to integration was unavailable; no integration DB writes.','','## Other exact commands','', '- Pipeline: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend <read-only-python> -m pytest tests/test_remote_config.py tests/test_live.py tests/test_sources.py tests/test_rules.py tests/test_rules_rates.py tests/test_sink.py tests/test_catalog_sync.py tests/test_consent.py -o addopts=\'\' -q`: **91 passed in 2.29 s**.', '- React: `npm run typecheck && npm test && npm run build`: **15 tests passed**, build passed. `npm run lint`: passed. Full captured Vite output was returned by the tool; frontend-typecheck.log records typecheck.', '- PWA: `npm ci --offline`; then Node 22 PATH and `npm run typecheck && npm test && npm run build`: **9 passed**, typecheck/build passed in pwa-verified.log. Initial Node 20 run had two Vitest worker errors; initial build found missing tokens.css, restored from original source. Config uses configurable RS_API_ORIGIN via Vite loadEnv.', '- Core changed services: `ruff check backend/app/services/offline_promotion.py backend/app/api/ingest.py backend/app/api/offline_analytics.py roadsentinel/remote_config.py`: passed (ruff-core.log). Whole-tree Ruff was not green and is not claimed; imported/offline/test lint findings remain in ruff logs.', '- `python -m compileall -q backend/app roadsentinel`: passed. Shell guard script syntax was validated in previous prerequisite work; it was not executed against integration.', '', '## Real model and fixture provenance','', 'Model: YOLOX-S ONNX SHA-256 c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063, CPUExecutionProvider; Supervision 0.30.7 ByteTrack, ONNX Runtime 1.23.2. Read-only approved local model path, no model download and no install into original venv.', 'Media: Editor, Street traffic.webm, Wikimedia Commons, CC BY 3.0; SHA-256 e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2. Raw licensed input remained in /tmp/Street_traffic.webm. Positive recorded fixture freezes the first real frame, resizes to 640x360, writes 36 s at 5 fps in test-owned tmp_path and processes at 2 fps. Actual outcome: 60 model samples and 9 obstruction candidates. Existing rule uses 90% dwell coverage tolerance (candidate reason reports 27 s for the configured 30 s); this must not be described as an observed street obstruction or exact threshold certification.', 'Live test: loopback-only MJPEG replay of the same licensed moving recording. Approved config/grant rows were fixture-created. Actual subprocess obtained lease, ACKed revision 1, produced two distinct authenticated preview payloads, then stopped on disable. External live and physical camera were not tested. Per-condition detector accuracy and live inference latency percentiles were not recorded as new acceptance metrics.', '', '## Executed browser scope','', 'Actual Chromium via frontend/e2e/mission-review.mjs: password → TOTP → /app/analiza-video → reason → explicit resubmission of already promoted candidate → same /app/alerte/{id} → rejected state, synthetic source label and playable protected clip. Upload/job and first promotion were real HTTP, not browser interactions. No claim that browser performed the upload or first promotion. Screenshot: screenshots/recorded-review.png; inspected, no auth secrets shown. Full UI confirm/case/export/archive/restart and live camera-detail browser journey remain unverified.','','## Retained run artifacts (failures included)','']
for p in sorted(O.glob('*.log')):
 text=p.read_text(errors='replace');summaries=re.findall(r'(?m)^.*(?:\d+ passed|\d+ failed|\d+ errors?|All checks passed|Build failed|built in|Tests\s+\d+ passed).*$' ,text)
 ledger += [f'### {p.name}', f'Artifact UTC: {datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()}', 'Outcome excerpt: '+ ('; '.join(summaries[-3:])[:750] if summaries else 'Inspect retained bounded trace; no passing summary recorded.'),'']
(O/'TEST_EXECUTION_LEDGER.md').write_text('\n'.join(ledger))
with (O/'README_COVERAGE_MATRIX.csv').open() as f:rows=list(csv.DictReader(f));fields=list(rows[0])
fields += ['after_source','after_lines','verification_limit']
map_groups={r['id']:r for r in rows if r['id'].startswith('A')}
for r in rows:
 r['after_source']=r['source'];r['after_lines']=r['lines'];r['verification_limit']='Coverage inventory; unverified behavior is not promoted to passing status by code presence.'
 if r['source']=='README.md' and r['id'].startswith('REQ'):
  r['source']='docs/audits/README_BEFORE_SOURCE.txt'
  # Preserve BEFORE line anchors; README changes are additive/corrective and explicitly linked.
  r['after_source']='README.md';r['after_lines']='See corresponding current heading (before lines preserved)'
 if not r['code_owner']:r['code_owner']='ARCHITECTURE_AND_CONTRACT_MAP.md'
 if not r['test_path']:r['test_path']='TEST_EXECUTION_LEDGER.md'
 if r['id'] in ('A02','A05','A09','A10','A13','A23'):
  r['evidence_link']='vertical-release.log; screenshots/recorded-review.png'
 if r['id'] in ('A16','A24','A33'):
  r['evidence_link']='vertical-release.log; pipeline-release.log'
  r['verification_limit']='Managed approval is fixture-owned; outages, reconfiguration, export and live browser remain unverified.'
 if r['id']=='A18':r['evidence_link']='backend-release.log; TEST_EXECUTION_LEDGER.md'
with (O/'README_COVERAGE_MATRIX.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
after=['# Post-integration README audit — after','', 'The before audit and source snapshot are preserved. Inventory: 150 source paragraph/table criteria plus all 35 mandatory category checks. This is a broad source-grounded coverage review with functional evidence where executed; **it is not an assertion that every requirement or every transitively linked document was exhaustively acceptance-tested**. Remaining unknowns stay unverified.','','## Delivered behavior and proof','', '- F1 PARTIAL: actual recorded upload/crop/YOLOX/ByteTrack/candidates → explicit canonical review promotion → encrypted keyframe/clip → authenticated browser display and duplicate resubmission → operator rejection via real HTTP. Frozen fixture is explicitly synthetic. No automatic live dispatch.', '- F2 PARTIAL: actual local MJPEG recording replay → approved-fixture config → HMAC lease + ACK revision 1 → real pipeline inference/tracking → changing authenticated preview → stop after disable. Managed event/preview fencing and bounded queue are implemented. Full outage/reconfigure/browser/case acceptance remains open.', '- Tests: 419 backend passed, 2 skipped; final new-flow regression 3 passed; pipeline 91; React 15; PWA 9. See exact ledger and failure history.', '- Existing integration auth remains blocked by lookup owner without BYPASSRLS. Test authentication used actual MFA on disposable resources; no bypass introduced. Existing DB/credentials were preserved.', '- Snapshot omissions repaired: common_passwords.txt, demo/local-UVC/Iasi source profiles, Romanian discovery registry and PWA tokens.css. Public candidates remain disabled. Additive 0021 reconciles two offline indexes; applied only to fresh mission DBs.', '- README corrected authoritative API/evidence/optional telemetry/person-identity wording, added source-safe recorded review and managed worker limitations. Paragraph BEFORE anchors refer to README_BEFORE_SOURCE.txt.', '', '## Category evidence and remaining acceptance','']
for r in rows:
 after += [f'### {r["id"]} — {r["requirement"][:130]}',f'Source: `{r["source"]}:{r["lines"]}`. Category: **{r["current_status"]}**; priority {r["priority"]}.',f'Owner: `{r["code_owner"]}`. Test/evidence: `{r["test_path"]}`; `{r["evidence_link"] or "No direct current-run acceptance proof"}`.',f'Next acceptance: {r["next_acceptance"]}. {r["verification_limit"]}','']
after += ['## Unclosed P0 gates','', 'Existing integration auth; full first-promotion browser journey from upload; case export/approval and manifest verification; crash/restart durability and orphan cleanup; controlled stream disconnect/recovery; approved revision change/rollback; multi-camera bounds; existing-data migration backup/restore validation. External live is blocked by missing documented rights. No real-world accuracy, legal admissibility or production-readiness claim is made.']
(O/'POST_INTEGRATION_README_AUDIT_AFTER.md').write_text('\n'.join(after))
(O/'TOP_TWO_FEATURE_ACCEPTANCE.md').write_text('''# Final acceptance gates

F1-01 PASS PARTIAL REAL INPUT: 60 actual model samples, 9 candidates from synthetic frozen licensed frame; no representative incident accuracy.
F1-02 PASS: HTTP operator explicit promotion into canonical new alert; recorded origin and synthetic label; encrypted redacted JPEG and playable bounded MP4.
F1-03 PASS: repeated submission idempotent; other tenant 404; patrol/auditor 403; cross-tenant media denied.
F1-04 PASS PARTIAL BROWSER: actual password/TOTP, candidate-list resubmission links same alert, rejected state and playable clip. First upload/promotion/decision performed by HTTP. Full case/archive/export/restart browser not passed.
F1-05 UNVERIFIED: approved case export manifest and crash/restart durability.

F2-01 PASS LOCAL REPLAY: fixture-approved managed source acquires lease before source open; real model and reference check; ACK revision 1.
F2-02 PASS: signed preview, two distinct payloads, authenticated tenant access, actual YOLOX/ByteTrack pipeline.
F2-03 PASS: second epoch receives stop; model mismatch/revision/revocation unit negatives; actual disable stops worker and managed preview reads are gated.
F2-04 UNVERIFIED: forced disconnect and reconnect, approved effective config reload/rollback, multi-camera stress and live detail browser.
F2-05 UNVERIFIED: eligible model-derived live incident + exported evidence. Recorded positive and HMAC ingest are separate verified components, not a claimed single live incident test.
External live: BLOCKED (no verified source-specific processing/recording authorization).

Overall: Feature 1 PARTIAL; Feature 2 PARTIAL. No all-green completion claim.
''')
(O/'FINAL_ENGINEERING_HANDOFF.md').write_text('''# Final engineering handoff

Implementation and source coverage audit delivered; selected features remain PARTIAL against the full mission acceptance gates. Begin with POST_INTEGRATION_README_AUDIT_AFTER.md, TEST_EXECUTION_LEDGER.md, TOP_TWO_FEATURE_ACCEPTANCE.md and REMAINING_FEATURES_MASTER_BACKLOG.md.

Recorded review now uses the existing authoritative alert/evidence APIs. Operator/admin can explicitly submit eligible completed offline candidates with reason, idempotent event key and tenant scope; clips/keyframes are redacted output encrypted by existing evidence service. Canonical UI displays recorded/synthetic provenance and existing review/casework panels. Actual model/HTTP/Chromium proof is retained.

Managed pipeline now consumes approved control config, acquires a processing lease, checks source identity and model/reference, ACKs, publishes compatible measured telemetry, fences event/preview writes, and stops on control changes. Graceful exit closes reader and pending queues; critical-only queue overflow is bounded. Model hash is checked again before offline execution. External URLs remain consent-gated and replay cannot claim external live.

Verification: final full backend 419 passed + 2 skipped; later focused 3 passed; pipeline 91; React 15; PWA 9, both client builds. Whole-tree lint and every README behavior are not asserted. Snapshot omissions and index drift were fixed. Migration 0021 was tested on fresh mission resources only (32 forced-RLS tables); original schema/history not rewritten.

Existing runtime preserved: http://127.0.0.1:5175/login, backend http://127.0.0.1:8003. The actual existing DB identity is rsint_20261110b / 127.0.0.1 / 55446 / rsint_app_261110b. Its lookup owner is still BYPASSRLS=false, so saved-account authentication is NOT fixed live. Administrator connection unavailable. No migration/seed/role/account write made to that DB. The protected existing credential file was not changed. A privileged guarded repair needs backup/identity verification in the native host; do not blindly rerun seed. Existing backend was not restarted, so source changes are not claimed deployed into that process.

No GitHub push or remote mutation was performed; integration has no Git metadata and none was initialized. Original source roots were read-only throughout mutation commands. A late-baseline comparison checked 307 primary and 301 review tracked source files with zero changes; this is not a complete private-file or whole-session hash baseline. Interpreter executed read-only with bytecode writes disabled; no installation into original .venv. Original databases were not accessed for writes.

Remaining next ten tasks (first action and detailed definitions are in the backlog):
1. Guarded integration auth repair after backup; verify one correct password→MFA request.
2. Full browser first promotion and retained-data restart test.
3. Real two-admin config lifecycle and effective worker revision change.
4. Controlled stream outage/recovery plus two-camera resource measurement.
5. Inject mid-evidence-write failure and reconcile only newly owned orphan objects.
6. Case approval/export package with manifest/hash verification.
7. Temporal-rule moving/occluded/shake negatives and exact dwell semantics.
8. Upload quotas and expired source/output/artifact retention with holds.
9. Licensed representative labeled evaluation and approved thresholds.
10. PWA HTTPS/patrol/browser and isolated deployment restore drill.

Minimal safe next command:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
cat docs/audits/INTEGRATED_BROWSER_DEMO_RUNBOOK.md
```

Frontend standard start (only if the existing integration Vite has been stopped by its owner): `RS_API_ORIGIN=http://127.0.0.1:8003 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5175 --strictPort`. The runbook includes the exact disposable PostgreSQL/test setup and source/model paths. Never use original DBs, disable MFA/RLS/HMAC, or represent synthetic fixtures as real incidents.
''')
(O/'MISSION_CHECKPOINT.md').write_text('Final checkpoint: code and reports persisted. Full suite and focused tests completed; existing integration auth requires privileged host repair. Current test-owned cluster shutdown status is recorded in the final ledger appendix. Do not rerun generators over preserved before audit; resume from unverified gates in TOP_TWO_FEATURE_ACCEPTANCE.md.\n')
print('Wrote final ledger, AFTER audit and engineering handoff; retained failures were sanitized.')
