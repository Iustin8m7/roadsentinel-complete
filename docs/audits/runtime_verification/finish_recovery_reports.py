"""Finalize current-run evidence and retain the older historical ledger."""
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT/'docs/audits'
E = D/'runtime_verification'
FLOW = 'runtime_verification/runs/20261110T130556Z-dbe51341'

ledger = f'''# Current execution — existing login recovered, 2026-11-10

This section supersedes the historical midnight-run ledger below. A is existing5175/8003/rsint_20261110b:55446. B is fresh disposable PostgreSQL on55481 or a new unique random port. C is the original read-only project. Tests can see native loopback in this session; there was no socket/administrator blocker.

| Check | Actual outcome | Runtime and evidence |
|---|---|---|
| Full backend `python -m pytest tests -o addopts='' -q` | **422 passed, 0 failed, 2 skipped**, 19 warnings,138.45s | B, rsmission_final_regression:55481, `runtime_verification/backend-suite-final.log` |
| Full root `python -m pytest tests -o addopts='' -q` | **213 passed, 0 failed, 0 skipped**,2 warnings,5.67s | B test-owned temp files, `pipeline-suite-current-fixed.log`; stock model path explicitly supplied |
| React `npm run test` | **19 passed,0 failed,0 skipped**,3 files | `frontend-tests-final.log` |
| React `npm run lint`; `npm run typecheck`; `npm run build -- --outDir <new verification output>` | PASS | `frontend-lint.log`, `frontend-typecheck.log`, `frontend-build.log`; build includes TypeScript |
| PWA `npm run test` | **9 passed,0 failed,0 skipped**,2 files | `pwa-tests.log` |
| PWA `npm run lint`; `npm run build -- --outDir <new verification output>` | PASS; build includes TypeScript | `pwa-lint-final.log`, `pwa-build.log` |
| Actual live Chromium login | **5/5 journeys** first run and **5/5 repeat**; no JS page errors | A, `live-browser-enrollment-result.json`, `live-browser-result.json`; current screenshot requires completed data loading |
| Recorded + camera focused HTTP/model/browser | **2 passed**,17 warnings,47.21s | B, `full-feature-journeys.log` |
| Independent new-cluster auth/seed/model/browser repeat | **44 passed,0 failed,0 skipped**,17 warnings,67.30s | B2 rsmission_verify_0136cfcfa3:37651; [{FLOW}/commands.json]({FLOW}/commands.json) records exact UTC start/end/exit/duration, including clean owned shutdown |
| Python compilation | PASS | `compile.log`; backend/app, backend/alembic, roadsentinel, new scripts |
| Targeted Ruff | PASS after corrections | `python-quality.log`; reviewed changed lookup/migration/test/pipeline/helper files; whole-tree style cleanliness is not claimed |
| Guarded repair inspection | PASS; inspection-only after repair | `recovery-final-inspection.log`; exact native identity verified |
| Live migration/RLS | rsint_case2→0022 after verified backup/restore/rehearsal;32 named FORCE RLS tables retained | `live-security-after.json`; no live reset/seed/password overwrite |
| Reference source preservation | **608/608 hashes + both HEADs unchanged** | `reference-preservation-final.json` |

The44-test repeat is a subset of the backend suite, not44 additional unique tests. Skipped legacy real tests use separate opt-in flags and an in-tree model requirement; `test_real_yolo_e2e` and `test_offline_analytics_real_video` remain skipped. The newer mission tests actually ran the model and browser in the422/44 results. Supervision ByteTrack and SQLAlchemy Result.tuples deprecation warnings remain; no test was weakened to suppress them.

## Exact reproducible backend command from this run

```bash
cd /home/justin7m8/Documents/roadsentinel-integration/backend
PYTHONDONTWRITEBYTECODE=1 \\
RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx \\
RS_MISSION_REAL=1 \\
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://rslogin_testroot@127.0.0.1:55481/postgres \\
RS_TEST_DATABASE_NAME=rsmission_final_regression \\
RS_TEST_ALLOW_DATABASE_RESET=rsmission_final_regression RS_TEST_EXPECTED_PORT=55481 \\
PYTHONPATH=.. ../.venv.integration/bin/python -m pytest tests -o addopts='' -q
```

55481 is this mission's disposable cluster, never the user's55446 database. After cleanup, use `.venv.integration/bin/python scripts/verify-integration.py backend` or `... flows` from the project root to create a fresh uniquely named cluster. It records commands/exit codes and closes only its own servers. No broad DATABASE_URL fallback is accepted by the test fixtures.

Other actual commands:

```bash
PYTHONDONTWRITEBYTECODE=1 RS_YOLOX_MODEL_PATH=/home/justin7m8/Documents/roadsentinel/models/yolox_s.onnx .venv.integration/bin/python -m pytest tests -o addopts='' -q
PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH node frontend/e2e/live-login-recovery.mjs
.venv.integration/bin/python scripts/verify-integration.py flows
```

The live browser script reads only the protected verified credentials and writes authenticators privately; its public trace omits bodies/headers/cookies/secrets. The wrapper logs print no passwords. Final individual result file timestamps are captured in `test-artifact-ledger.json`; these are completion/file-modification times, not invented command start times. Only the new repeat harness has instrumented UTC start/end telemetry.

## Failure history retained and resolved

- First recovery restore rehearsal failed on missing backend PYTHONPATH. No live writes occurred; fixed root+backend import path, reran full backup/restore/rehearsal before live apply. `recovery-apply.log` vs `recovery-apply-verified.log`.
- Initial broad root run lacked legacy itsdangerous and stock model resolution; itsdangerous2.2.0 was added only to integration test requirements/venv. Explicit checked readonly stock-model mapping and stale unsupported.pt test assertions were corrected. A later run accidentally omitted RS_YOLOX_MODEL_PATH:3 failed/210 passed; rerun with documented setting:213 passed. Both logs retained.
- Targeted Ruff initially reported formatting/unused imports and fixture subprocess annotations; reviewed fixes now pass. `.venv.integration` itself does not include Ruff; the already isolated `/tmp/rsint-venv/bin/ruff` was used. No original venv mutation.
- PWA lint found one existing Vite config formatting error; fixed using its installed Prettier; final lint passes. React empty-data spinner was exposed by actual screenshot inspection, fixed with explicit loaded state, then browser assertions strengthened.

## Scope boundaries

Positive recorded incident fixture is SYNTHETIC TEST, generated from a licensed frozen real frame. Real moving replay produced detections/tracks but zero eligible live incident events. No accuracy score is claimed. Full configuration/approval via API is proved, while two-admin browser configuration editing and live positive event export remain open. Existing integration password/MFA/login/dashboard and process-restart session are independently verified on A; fixture feature journeys are on B. No conflation.

---

# Historical ledger preserved below

'''
p = D/'TEST_EXECUTION_LEDGER.md'
if not p.read_text().startswith('# Current execution'):
    p.write_text(ledger+p.read_text())

old = D/'REMAINING_FEATURES_MASTER_BACKLOG.md'
if not (E/'REMAINING_BACKLOG_BEFORE_RECOVERY.md').exists():
    shutil.copyfile(old,E/'REMAINING_BACKLOG_BEFORE_RECOVERY.md')
items = [
('Complete recorded journey in Chromium','P0','A10,A12,A14,A15,A23','2–4 days','frontend/e2e/mission-review.mjs;frontend/src/pages/VideoAnalysisPage.tsx;backend/tests/test_mission_vertical.py','HTTP upload/analysis/first promotion and API export work; browser rejection/note/playback work. Missing one browser-only upload→analysis→first promotion→approval→export→archive journey.','Extend the current harness with two MFA-authenticated contexts and native file upload; assert persisted result, archive lookup and downloaded package hashes.','Start with one browser file upload and assert201 plus the owned recording card.','Do not access another tenant media; invalid role, duplicate promotion and missing clip must remain denied.','Entire supported recorded workflow passes in Chromium with recorded/synthetic labels and real persistence.'),
('Crash-safe evidence and retained restart','P0','A10,A11,A19,A23,A33','3–6 days','backend/app/services/offline_promotion.py;backend/app/services/evidence.py;backend/app/services/offline_video_storage.py','Orderly persistence and live auth restart are proven. Abrupt ciphertext/DB commit interruption and reopened feature case after process restart remain unverified.','Add durable pending-object bookkeeping or transactional reconciliation for only newly owned media; inject faults before/after file+DB commit, restart, verify one alert and intact authorized evidence.','Fault-inject the first promotion ciphertext write in a disposable DB.','Never delete pre-existing files; simulate storage outage, rollback and duplicate retry; bound reconciliation pages.','No leaked orphan media, duplicate decisions or inaccessible committed evidence after repeated interruptions.'),
('Positive managed camera incident','P0','A05,A10,A11,A16,A24','3–5 days plus lawful fixture','roadsentinel/pipeline.py;roadsentinel/rules.py;backend/tests/test_managed_live_runtime.py','Moving model replay has zero eligible incidents. Recorded synthetic positive and signed live control/preview are independently verified.','Obtain an authorized annotated fixture that triggers a supported non-speed rule; run actual managed inference and signed bounded event media through operator case review/export. If using synthetic tracks, keep explicit separate SYNTHETIC TEST proof.','Verify candidate interval/geometry on a licensed clip before adding managed assertions.','Never reduce thresholds solely to force a result, invent calibration or relabel replay as external live.','At least one explainable model-derived managed-source candidate persists with correct revision/source/encrypted media and human decision.'),
('Two-admin browser control editor','P1','A04,A16,A24','2–4 days','frontend/src/components/CameraControlPanel.tsx;frontend/e2e/camera-control-runtime.mjs;backend/app/services/camera_config.py','Browser registration+preview and real API draft/validation/independent approval/activation/revision2 pass. End-to-end browser editing/approval/rollback remains.','Extend existing component/harness with separate reviewer session, JSON geometry validation, expected revision conflicts and explicit active/applied badges.','Create one draft via the UI and compare backend version contents.','Self approval403, invalid polygon, unapproved activation, stale revision and cross-tenant camera must fail.','Two browser identities configure, approve, activate, observe ACK and rollback with audited history.'),
('Multi-camera soak and worker recovery','P0','A03,A24,A33','3–6 days','roadsentinel/live.py;roadsentinel/remote_config.py;backend/app/services/camera_control.py','Single-source reconnect/stale expiry/re-enable and duplicate worker refusal pass; two-camera sustained capacity and abrupt worker death not measured.','Run two controlled replay sources with bounded memory/queue counters; crash one worker; observe expiry and reassignment without affecting other camera.','Measure baseline process RSS/CPU for one and two10-minute sources on hardware with adequate headroom.','No unrelated process termination, unbounded retry, stale healthy image or duplicate event flood.','Document measured capacity/backpressure/loss; one-camera failure stays isolated and all resources close.'),
('External-source authorization and SSRF','P1','A03,A20,A24,A31','2–5 days plus external permission','roadsentinel/consent.py;roadsentinel/sources.py;backend/app/services/camera_control.py;cameras/romanian-source-registry.json','EXTERNALLY BLOCKED: no source-specific processing/record/store/export authorization. Discovery catalog does not grant rights.','Secure written scope and approved endpoint, then add controlled DNS/redirect/allowlist threat tests before permitted live validation.','Review one owner-issued authorization without retrieving stream media.','No private-IP redirect, metadata access, token scraping, TLS bypass or recording beyond scope.','Documented permission plus stable authorized stream and negative SSRF tests; otherwise remains blocked.'),
('Original upload retention and quotas','P1','A10,A20,A23','3–5 days','backend/app/services/offline_video_storage.py;backend/app/services/retention.py;backend/app/api/offline_video.py','Encrypted media and evidence retention paths exist; total tenant quotas, canceled-job/intermediate expiry and long-term hold behavior remain incomplete.','Add explicit per-tenant byte/job quotas and reversible retention scheduling, with legal holds and bounded cleanup on own fixtures.','Test quota refusal before persisting a new temporary upload.','Held evidence cannot expire; interrupted cleanup cannot leak decrypted material or affect another tenant.','Bounded usage and documented policy; expiry/hold/cancel tests pass without touching existing user media.'),
('Representative evaluation and model governance','P1','A02,A04,A06,A07,A08,A09,A21,A22','1–3 weeks plus labeled data','models/registry.json;training;roadsentinel/rules.py;docs/LIMITS.md','EXTERNAL DATA BLOCKER: no representative annotated incident set or accepted target metrics. Timing/counts are not accuracy.','Collect licensed labeled day/night/rain/occlusion clips; measure precision/recall/false alerts per hour and count error by scene; review model/ruleset activation.','Define one annotated obstruction dataset and freeze hashes/expected intervals.','No uncalibrated legal speed claim, persistent person identity or silent model fallback.','Reproducible independent metrics with confidence/limitations and approved deployment thresholds.'),
('Secure PWA HTTPS/patrol acceptance','P1','A01,A13,A17,A27,A28,A29','2–5 days','secure-pwa/src;deploy;frontend/e2e/pwa-walk.mjs','PWA9 unit tests, lint/type/build pass; actual HTTPS installation/patrol/push/accessibility journey not run this time.','Use test-owned trusted local TLS origin, real MFA, role-specific patrol assignment and reconnect/session handling; no public secrets in service worker cache.','Authenticate a patrol fixture via real PWA QR/TOTP under test TLS.','No camera/admin privilege, evidence caching, generic push detail leakage or cross-tenant assignment.','Installable authenticated PWA supports actual scoped tasks and negative/security/browser checks.'),
('Deployment, keys, audit custody and legal review','P2','A18,A19,A20,A26,A27,A30,A32,A35','1–3 weeks plus organizational owners','deploy;backend/app/core/crypto.py;backend/app/core/audit_anchor.py;docs/ARCHITECTURE_TARGET.md','Local backup restore rehearsed; no production KMS/HSM, external audit custody, OIDC/FIDO2, DPIA/legal approval or production deploy proof.','Separate scoped projects: isolated restore/deploy drill, external key provider contract, independent audit anchor, approved IdP and legal processing policies.','Run deploy/readiness/restore on a new cluster without originals, or define a mock KMS contract test first.','No production compliance/admissibility claim; external enforcement remains disabled/operator record only.','Explicitly approved production acceptance with restorable backups, key custody and independent audit/organizational decisions.'),
]
body=['# Remaining features master backlog — after real login recovery','','Updated2026-11-10. Login is FIXED and VERIFIED on the existing integration, not a pending task. Password unchanged; MFA enabled. Both selected fixture flows pass in disposable resources; broader feature completeness remains PARTIAL. Historical backlog retained in runtime_verification/REMAINING_BACKLOG_BEFORE_RECOVERY.md. Rough estimates below are not delivery commitments.','','## Delivered prerequisites','','Narrow NOLOGIN RLS lookup repair,0022 backup/restore-rehearsed live upgrade, partial/idempotent seed, real four-role login/QR enrollment, permissions, recovery-code acknowledgement, empty-dashboard loading, dedicated runtime and safe startup helper. No database reset or password replacement.','','## Next ten tasks in order','']
for i,(name,priority,ids,estimate,files,state,approach,first,boundary,done) in enumerate(items,1):
    body += [f'### B{i:02} {name}',f'Priority {priority}; requirements {ids}; rough estimate {estimate}.',f'Current: {state}',f'Owners: `{files}`.',f'Implementation: {approach}',f'First small test: {first}',f'Authorization/failure constraints: {boundary}',f'Definition of done: {done}',f'Suggested Codex sub-prompt: Implement B{i:02} in the integration workspace using existing canonical services; preserve original roots/DBs, FORCE RLS/MFA/CSRF/consent; begin with the first test above and report actual runtime/fixture evidence.','']
rows=list(csv.DictReader((D/'README_COVERAGE_MATRIX.csv').open()))
body += ['## Every mandatory category — current gap/next acceptance','']
for r in rows:
    if r['id'].startswith('A'):
        body += [f"### {r['id']} {r['requirement']}",f"Status **{r['current_status']}**; priority {r['priority']}. Owners/tests: `{r['code_owner']}`; `{r['test_path']}`.",f"Next: {r['next_acceptance']}",f"Limits: {r['verification_limit']}",'']
old.write_text('\n'.join(body))

accept='''# Current selected-feature acceptance — 2026-11-10

Existing login PASS on A: actual5175→8003→rsint_20261110b:55446, four roles QR/TOTP/recovery acknowledgement, normal TOTP challenge, protected dashboard, refresh/restart/logout. Wrong password401; privilege denials403;32 FORCE RLS tables and runtime NOBYPASSRLS retained.

| ID | Observed acceptance | Result |
|---|---|---|
| F1-01 | Real YOLOX-S/ByteTrack on explicitly synthetic licensed frozen-frame derivative;60 samples; nonempty candidates | PASS fixture; no real incident accuracy |
| F1-02 | Owned upload/crop/analysis via HTTP; explicit operator promotion; recorded/synthetic source; encrypted redacted playable JPEG/MP4 | PASS B |
| F1-03 | Duplicate returns same alert; cross-tenant404; patrol/auditor403; private media denied | PASS B |
| F1-04 | Chromium candidate resubmission→alert→actual rejection→case note→protected playback | PASS B; first creation/upload done via HTTP |
| F1-05 | Admin license grant, self-approval denied, independent export approval, package download, manifest/member SHA-256 | PASS HTTP B; no signed/external custody claim |
| F1-06 | Whole case/archive/browser export and restart/crash durability | NOT FULLY TESTED |
| F2-01 | Actual admin browser registration; genuine two-admin API draft/validate/submit/approve/activate | PASS B; not every control editor action in browser |
| F2-02 | HMAC lease before source open, real model, ACK1, changing operator browser preview | PASS LOCAL RECORDED REPLAY |
| F2-03 | Competing actual worker refused before source open; revision2 independent activation→fresh lease/ACK | PASS B |
| F2-04 | Forced source outage→reconnecting→expired preview404→real recovery; disable/re-enable/final pause | PASS B |
| F2-05 | Eligible model-derived managed incident/evidence/case export in one run | NOT VERIFIED; moving replay had0 eligible events |
| F2-06 | Two-camera soak, abrupt worker crash/expiry, external authorized live | NOT TESTED / EXTERNAL RIGHTS BLOCKED |

Broader Feature1 PARTIAL; Feature2 PARTIAL. Actual fixture component gates pass; missing gates are not marked green. See FULL_INTEGRATION_E2E_VALIDATION.md and its repeatable44-test command.

---

# Historical acceptance checklist

'''
p=D/'TOP_TWO_FEATURE_ACCEPTANCE.md'
if not p.read_text().startswith('# Current selected-feature'):
    p.write_text(accept+p.read_text())

security='''# Current security/privacy regression — 2026-11-10

Existing integration login recovery PASS. Exact identity verified live before changes; private dump restored and migration rehearsed on an isolated cluster. All original row digests preserved at migration boundary. Existing passwords untouched; four accounts enrolled through genuine MFA afterwards. A migrated to0022. Full backend422 passed/2 opt-in skipped; root213; React19; PWA9. Whole-tree/static/production security certification is not claimed.

| Boundary | Current evidence and limits |
|---|---|
| RLS |32 named ENABLE+FORCE tables on A; runtime app and old migrator NOBYPASSRLS. Dedicated NOLOGIN column-limited lookup owner only. Hash-column and schema-CREATE access denied; no role members. See live-security-after.json and test_lookup_ownership.py. |
| Tenant | Native principal drives tenant context; cross-tenant promotion/media negative HTTP passes; broader isolation suite passes. Identifier lookup does not return password hashes/media. |
| Password/MFA | All9 hashes matched saved password before repair. Four Unit A roles enrolled using QR/TOTP; normal challenge and wrong password verified in live Chromium. TOTP replay/recovery/CSRF/session tests pass. MFA exemption false. |
| CSRF/cookies | Existing middleware retained. Real cookie-preserving browser login, refresh, logout; negative Origin/token tests pass. Local HTTP Secure=false was already configured for loopback; production Secure/TLS defaults not weakened. |
| RBAC | UI uses backend permissions/roles, hides unauthorized requests; live users/audit/events negative checks. Auditor remains auditor, patrol remains patrol. Backend remains authoritative. |
| HMAC/lease | Exact-body signature, nonce/time/camera/account checks remain. Real signed managed config/heartbeat/preview, duplicate worker denial, ACK/revision2 and stop/re-enable tested. Managed positive incident remains unverified. |
| Evidence | Real recorded promotion writes encrypted redacted media; authenticated playable retrieval, tenant denial, independently approved hash-verified export pass. Redaction is heuristic, not complete anonymization; package manifest is unsigned. |
| Audit | Auth/MFA/decisions/configuration repair audited through existing service. Hash chain exists; no external independent custody anchor. |
| Consent/SSRF | Explicit local replay grant and loopback source; no external camera access or assumed rights. External DNS/redirect threat matrix and permission remain unverified. |
| Retention/recovery | Live DB backup restored/verified; no reset. Evidence crash orphan reconciliation, quotas and long-term retention soak remain backlog items. |
| Secrets | Password unchanged in0600 credential file. QR/seeds/recovery codes are only in0700/0600 ignored private authenticator directory; no screenshots of enrollment. Public traces contain paths/status only. Development TOTP helper uses actual enrolled factor. |
| Originals |608 source hashes and both HEADs unchanged; no original DB writes, no original dependency install, NO GITHUB PUSH. |

No facial recognition, persistent person identity, automatic enforcement, invented violations, certified speed, DPIA/legal compliance or production readiness is claimed.

---

# Historical security report

'''
p=D/'SECURITY_PRIVACY_REGRESSION.md'
if not p.read_text().startswith('# Current security/privacy'):
    p.write_text(security+p.read_text())

for filename,appendix in [
('FEATURE_01_AI_INCIDENT_TO_OPERATOR.md','''## Current execution proof — 2026-11-10

The existing native application's login now passes real password/MFA/dashboard verification. The expanded disposable-model test now performs the actual rejection and case observation in Chromium, rather than merely displaying an already rejected incident. Subsequent duplicate decision409 proves persisted UI action. HTTP first upload/promotion and independently approved SHA-256 export remain, with tenant/role denials. Latest full backend422 passed/2 skipped; independent fresh-cluster auth+flows44 passed. Frozen positive produced60 model samples and8 candidates in the focused run; prior9 was historical variation, not accuracy ground truth. Whole browser upload/export/archive/restart and abrupt evidence crash remain unverified. See ../audits/FULL_INTEGRATION_E2E_VALIDATION.md for exact scope and commands.
'''),
('FEATURE_02_AUTHORIZED_LIVE_CAMERA.md','''## Current execution proof — 2026-11-10

The managed test no longer injects preapproved camera/config/grant rows. Actual MFA browser registration creates the camera; authenticated source/grant/draft/validate/submit APIs, separate admin approval and activation create runnable state. Real worker obtains lease/ACK1 and changing operator browser preview. Competing worker is refused before source open. A second separately approved config stops old worker and is ACKed by a fresh lease. Forced socket interruption expires preview and recovers; disable, independent re-enable and final pause all pass. Orderly worker exit now sends a stopped heartbeat, allowing immediate lease replacement. Actual moving replay produced zero eligible incident events; no external/live-incident export claim. Full feature remains PARTIAL pending positive managed incident, full two-admin browser editing, soak/capacity and authorized external source. See ../audits/FULL_INTEGRATION_E2E_VALIDATION.md and fresh44-test evidence.
''')]:
    p=ROOT/'docs/implementation'/filename
    s=p.read_text()
    if '## Current execution proof — 2026-11-10' not in s:
        p.write_text('> Current evidence: the dated current-execution appendix below supersedes historical fixture-only/blocked-auth statements.\n\n'+s+'\n'+appendix)

p=ROOT/'API.md'
s=p.read_text()
if '## Integrated development authentication and review contracts' not in s:
    p.write_text(s+'''\n## Integrated development authentication and review contracts

The secure backend is authoritative; legacy shared-password examples above do not describe its authentication. In the integrated React UI, `POST /api/login {operator: email, password}` sets a short-lived pending-MFA cookie and returns `mfa_required` plus `mfa_enrollment`. It does not issue an authenticated user session before the second factor. Native `POST /api/auth/login {email,password}` returns `enrollment_required` instead. Both require existing CSRF/Origin rules.

For first enrollment: pending enrollment cookie → `POST /api/auth/mfa/enroll/start` returns private QR SVG data URI/secret → `POST /api/auth/mfa/enroll/confirm {code}` returns8 private recovery codes and session cookies. UI waits for recovery acknowledgement before navigation. For enrolled accounts: `POST /api/auth/mfa/verify {code}` (or recovery_code) returns204. `GET /api/auth/me` supplies actual role/permissions;401 means no valid authenticated session. `POST /api/logout` compatibility response200 and native `/api/auth/logout`204 revoke the session. Wrong password401; failed MFA never grants access. Never log QR/secrets/codes.

Explicit recorded review: `POST /api/recordings/{recording_id}/analyses/{run_id}/candidates/{index}/promote {reason,synthetic_test?}` requires owned completed analysis, video-analysis and alert-create permission, CSRF and an eligible obstruction/queue candidate. It returns the canonical alert with recorded provenance; repeated promotion returns the same ID. Foreign tenant404; forbidden role403; invalid/noneligible/unfinished state yields a bounded validation/conflict error. Audit action is emitted by the existing offline promotion service. Authenticated event/evidence routes expose protected redacted keyframe/clip, never public raw upload URLs. See the current architecture map and FULL_INTEGRATION_E2E_VALIDATION.md for tested control-plane revision/lease/HMAC routes.\n''')

# Exact completion timestamps/results for retained log files; no secret content is copied.
artifacts=[]
for p in sorted(E.glob('*.log')):
    text=p.read_text(errors='replace')
    summaries=[line for line in text.splitlines() if (' passed' in line and (' in ' in line or 'Tests' in line)) or line.startswith('PASS existing integration:')]
    artifacts.append({'artifact':str(p.relative_to(ROOT)),'completed_mtime_utc':__import__('datetime').datetime.fromtimestamp(p.stat().st_mtime,__import__('datetime').UTC).isoformat(),'observed_summaries':summaries[-8:]})
(E/'test-artifact-ledger.json').write_text(json.dumps(artifacts,indent=2))
print('Ledger, backlog, acceptance, security, implementation/API documents updated')
