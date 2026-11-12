"""Rebuild source-anchored inventory; statuses are conservative until execution evidence exists."""
import csv, hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/audits'
links=set(re.findall(r'\]\(([^)#]+)',(ROOT/'README.md').read_text()))
files=['README.md']+sorted(p for p in links if not p.startswith(('http','mailto')))
rows=[]
for f in files:
 p=ROOT/f
 if not p.is_file():
  rows.append([f'DOC-{len(rows)+1:04}',f,'','Missing linked document','BROKEN','VERIFIED REAL END-TO-END','P2','','','','Restore or correct documentation link'])
  continue
 lines=p.read_text().splitlines(); heading=''; start=0; buf=[]
 def emit():
  if not buf:return
  text=' '.join(buf)
  if text.startswith('```'):return
  rows.append([f'REQ-{len(rows)+1:04}',f,f'{start+1}-{start+len(buf)}',heading+': '+text,'IMPLEMENTED UNVERIFIED','VERIFIED REAL END-TO-END','P1','See ARCHITECTURE_AND_CONTRACT_MAP.md','See TEST_EXECUTION_LEDGER.md','','Execute concrete acceptance behavior; historical documentation is not current-run evidence'])
 for i,line in enumerate(lines):
  if line.startswith('#'):
   emit();buf=[];heading=line.lstrip('# ').strip()
  elif not line.strip():emit();buf=[]
  else:
   if not buf:start=i
   buf.append(line)
 emit()
fields=['id','source','lines','requirement','current_status','target_status','priority','code_owner','test_path','evidence_link','next_acceptance']
with (OUT/'README_COVERAGE_MATRIX.csv').open('w') as fp:
 w=csv.writer(fp);w.writerow(fields);w.writerows(rows)
body=['# Post-integration README audit — before','',f'Inventory timestamp: {datetime.now(timezone.utc).isoformat()}. Every paragraph/table/command block in the current README and its directly linked local documents is retained below. An inventory entry is not a passed acceptance test. Historical performance statements are unverified in this execution.','','## Confirmed integration gaps','','- Offline candidates: backend/app/api/offline_analytics.py:388 returns review-only provenance; no promotion route.','- Worker: roadsentinel/pipeline.py has no control-plane desired-config/ACK calls; backend/app/api/camera_worker.py exposes these but no matching pipeline adapter.','- Historical auth repair exists in app/services/seed.py and LoginPage.tsx. Its privileged owner-role repair has not been run by this mission.','- Vite runtime proxy is correct on port 5175; default fallback 8000 remains intended for generic development.','- Existing integration service identity: cwd backend under this workspace; app database rsint_20261110b on loopback 55446. No write authorization is inferred from a health response.','','## Source inventory and individual criteria','']
for r in rows:body+=['### '+r[0]+' — '+r[1]+':'+r[2],r[3],'','Status: '+r[4]+'. Next: '+r[-1]+'.','']
(OUT/'POST_INTEGRATION_README_AUDIT_BEFORE.md').write_text('\n'.join(body))
(OUT/'PRE-FLIGHT.md').write_text('''# Pre-flight

Write root: /home/justin7m8/Documents/roadsentinel-integration (resolved, distinct).
Read-only roots: /home/justin7m8/Documents/roadsentinel and /home/justin7m8/Documents/roadsentinel-github-review.
Original interpreter may be executed with bytecode writes disabled; never install into it.
Current backend PID 1655813 cwd resolves to integration/backend, port 8003; frontend PID 1671183 port 5175 uses RS_API_ORIGIN=http://127.0.0.1:8003. Both direct and proxied /api/health/live returned alive.
Other services on 8001/8002/5173/5174 and PostgreSQL 55432/55444/55446 are preserved.
Credentials sources: backend/.env.integration.local and backend/.integration-test-credentials.json; contents excluded.
Existing auth changes from prior task are present. Multiple Codex processes exist; no inference of ownership from process name. No other writer has been detected from source inspection. No existing DB mutations performed.
Temporary mission cluster will be independently initialized under a unique /tmp/rsmission-* directory, TCP loopback only, with a distinct port and DB name. Tests must print effective nonsecret DB identity and guard destructive fixtures.
Compatibility risks: legacy server vs secure contract, offline origin vs alert semantics, pipeline YAML vs control config, historical docs with stale test counts, absent model artifact in integrated model path, hard-coded rs_test fixture.
''')
(OUT/'BASELINE_FAILURE_REPRODUCTIONS.md').write_text('''# Baseline reproductions

1. Read `backend/app/api/offline_analytics.py:388`: candidates are returned as offline_recording/pending_review; route search shows no promotion action. Missing capability, not an HTTP failure claim.
2. `rg "config/ack|/config" roadsentinel/pipeline.py`: no control-plane handshake. Config API exists in backend/app/api/camera_worker.py.
3. Current proxy: curl direct 8003 and proxied 5175 /api/health/live returned alive. Historical wrong proxy is not reproduced.
4. Prior owner-role failure is documented in the preceding authentication repair; this mission has not independently reproduced its database query yet. No blind seeding performed.
5. Model registry references models/yolox_s.onnx, which is absent in integration. No silent download performed.
''')
(OUT/'TOP_TWO_FEATURE_ACCEPTANCE.md').write_text('''# Acceptance gates

F1-01: Given a licensed recording and checked YOLOX artifact, real decoding/inference/tracking yields candidate: UNVERIFIED.
F1-02: Given completed owned analysis, operator explicitly promotes eligible candidate with redacted keyframe and bounded clip: ABSENT baseline.
F1-03: Duplicate/concurrent promotion returns same alert; forbidden role/tenant denied: UNVERIFIED.
F1-04: Persisted encrypted media, decision, archive and case export survive restart: UNVERIFIED.
F2-01: Worker acquires authoritative lease before source access and acknowledges approved configuration: PARTIAL baseline.
F2-02: Actual local replay yields changing real-model preview and signed measured telemetry: UNVERIFIED current run.
F2-03: Disable/revoke/lease loss stops capture; reconnect/backoff and missing model have honest state: UNVERIFIED.
F2-04: Approved revision changes and alert provenance are fenced: UNVERIFIED.
External live acceptance: BLOCKED pending documentary source-specific processing/recording rights.
''')
print(len(rows),'criteria inventoried')
