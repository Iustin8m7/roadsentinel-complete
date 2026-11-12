"""Build a dated, source-attributed browser handoff without copying secrets or media packages."""

import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "docs/audits"
E = D / "runtime_verification"
SESSION = E / "browser-20261111T011541+0200"
RUNS = E / "runs"
F1 = RUNS / "20261110T232618Z-eb8e75d7"
CAMERA = RUNS / "20261110T234129Z-259e8c90"
BACKEND = RUNS / "20261110T234143Z-edae720a"
FRONT = RUNS / "20261110T232408Z-16c65bc9"
PWA = RUNS / "20261110T232408Z-c6fd661f"
NOW = datetime.now(UTC).isoformat()


def rel(path):
    return path.relative_to(D).as_posix()


def link(path, label=None):
    return f"[{label or path.name}]({rel(path)})"


def write(name, body):
    (D / name).write_text(body.strip() + "\n")


def require_pass(folder, name):
    records = json.loads((folder / "commands.json").read_text())
    row = next(row for row in records if row["name"] == name)
    if row["exit_code"] != 0:
        raise SystemExit(f"Cannot document a passing {name}: {folder}")
    return row


for folder, suite in ((F1, "browser"), (CAMERA, "camera"), (BACKEND, "backend")):
    require_pass(folder, suite)
auth = json.loads((SESSION / "auth-final-code/live-browser-result.json").read_text())
assert len(auth["accounts"]) == 5 and not auth["errors"]
assert all(row["passwordAccepted"] and row["logoutRevokedSession"] for row in auth["accounts"])
f1 = json.loads((F1 / "complete-browser-result.json").read_text())
runtime = json.loads((SESSION / "active-runtime-final.json").read_text())
model = f1["moving"]["modelSha256"]
pipeline = max(
    (p.parent for p in RUNS.glob("20261110T23*/pipeline.log") if "221 passed" in p.read_text()),
    key=lambda p: p.name,
)
for folder in (FRONT, PWA):
    for name in ("test", "lint", "build"):
        require_pass(folder, name)

shots = D / "REAL_BROWSER_SCREENSHOTS/2026-11-11"
shots.mkdir(parents=True, exist_ok=True)
index = []
for source, group in ((SESSION / "auth-final-code/screenshots", "A-auth"), (F1 / "screenshots", "B-recorded"), (CAMERA / "screenshots", "B-camera")):
    for original in sorted(source.glob("*.png")):
        target = shots / (group + "-" + original.name)
        shutil.copyfile(original, target)
        index.append({
            "file": rel(target), "source": rel(original), "runtime": group,
            "captured_utc": datetime.fromtimestamp(original.stat().st_mtime, UTC).isoformat(),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
(shots / "index.json").write_text(json.dumps(index, indent=2))
write("REAL_BROWSER_SCREENSHOTS/2026-11-11/README.md", "# Fresh Chromium screenshots\n\n"
      "A-auth is the existing 5175/8003/55446 runtime. B-recorded and B-camera use separate disposable databases. "
      "QR/manual secrets, recovery codes and MFA inputs are masked before screenshots. "
      "The moving source is licensed; synthetic stimuli and local replay remain labeled.\n\n"
      + "\n".join(f"- [{row['file'].split('/')[-1]}]({row['file'].split('/')[-1]}) — {row['captured_utc']}; source `{row['source']}`" for row in index))

common = f"""Updated {NOW} (local date 2026-11-11, Europe/Bucharest).

Runtime A: existing UI5175 → API8003 → `rsint_20261110b@127.0.0.1:55446`, app `rsint_app_261110b`, Alembic0022.
Runtime B: new uniquely named clusters, databases and test-owned files; actual identities are in each run's `database.json`.
Runtime C: both original source trees/databases, read-only and never used for writes.
All browser actions use genuine Chromium{(SESSION/'chromium-version.txt').read_text().strip()} via Playwright, real Vite/FastAPI/PostgreSQL, no network interceptions or mocked success responses.
{link(SESSION/'active-runtime-final.json', 'Live identity/proxy/RLS proof')}; {link(shots/'index.json', 'timestamped screenshot hashes')}.
"""

write("REAL_BROWSER_AUTH_MFA_VERIFICATION.md", f"""# Real-browser authentication and MFA — PASS

{common}

{link(SESSION/'auth-final-code.log', 'Fresh native browser log')}; {link(SESSION/'auth-final-code/live-browser-result.json', f'{len(auth["requests"])} sanitized request outcomes')}; {link(shots/'A-auth-live-operator.png', 'operator dashboard')}.

| Criterion | Result | Actual assertion |
|---|---|---|
| Blank login and accessible labels | PASS | `/login`, Utilizator, Parolă, Intră, no page JS errors |
| Incorrect password | PASS | Actual password POST401; protected auth/me401; generic error, no session |
| Password alone cannot authenticate | PASS | Correct POST200 returns MFA challenge; auth/me remains401 |
| Invalid TOTP | PASS | First operator challenge deliberately submits invalid code, receives401 |
| Valid enrolled TOTP | PASS | Four role-specific fresh contexts plus repeat operator; real challenge accepted |
| Operator/admin protected UI | PASS | `/app`, populated server-backed dashboard and navigation |
| Patrol | PASS | `/app`, only permitted navigation; admin route blocked |
| Auditor | PASS | `/app/audit`, audit data, camera/admin write denied |
| Refresh/new tab | PASS | Valid session remains associated with original identity |
| Logout/back/direct protected URL | PASS | Logout invalidates session, auth/me401; UI returns to login |
| New account first enrollment | PASS in B | Real QR setup, TOTP confirmation,8 recovery codes, explicit acknowledgement; me401 before factor |
| Unit B resource probing | PASS in B API/RLS tests | Source-job/camera/alert/media/case/export ownership enforced; not a separate Unit B browser tour |
| Expired-session browser clock advance | NOT RUN | Invalid token tests exist; no long idle browser soak |
| Full accessibility/mobile/HTTPS install | NOT RUN | Keyboard-labelled tested screens only; no compliance certification |

Native accounts: operator.a@roadsentinel.local, admin.a@roadsentinel.local, patrol.a@roadsentinel.local, auditor.a@roadsentinel.local, tenant unit-a. Password remains in `backend/.integration-test-credentials.json`0600 and is unchanged. Existing factors are preserved; tests did not reset them. Native TOTP replay waits for the real next step. B fixtures may reset their own last-used step for repeated fixture logins; no production bypass exists.

MFA seeds, cookies and recovery codes are never report inputs. Protected local authenticator files are under `backend/.integration-authenticators/`0700. The corresponding private HTML QR can be imported into the user's authenticator. The command in FINAL_BROWSER_HANDOFF prints a TOTP only when run by the user locally.

Login root cause and completed repair: FORCE RLS applied to a non-BYPASS SECURITY DEFINER owner, hiding already existing tenants and users. Duplicate slug was evidence of hidden data, not absence. Six identifier lookups now have a dedicated NOLOGIN, column-limited owner; application/migrator remain NOBYPASSRLS. Existing passwords/MFA were preserved. See INTEGRATED_LOGIN_RECOVERY_REPORT.md and migration0022. The UI also now maps actual native roles/permissions, sends auditors to audit, waits for recovery acknowledgement, and finishes an empty dashboard load.

HTTP development uses loopback with the configured non-Secure development cookie mode; production Secure/SameSite/CSRF/MFA controls were not globally relaxed. Browser mutations use CSRF tokens, protected endpoints enforce role policy, and no UI password/MFA material appears in screenshots.
""")

moving = f1["moving"]
write("FEATURE_1_REAL_BROWSER_E2E.md", f"""# Feature 1 — real browser recorded-video journey

{common}

**Selected complete fixture journey: PASS. Broader feature: PARTIAL.** Moving video proves actual detection/tracking/analytics. The separately frozen positive proves the incident workflow on SYNTHETIC TEST material. Neither proves real incident accuracy.

{link(F1/'commands.json', 'Executed command/timing')}; {link(F1/'database.json', 'disposable DB')}; {link(F1/'browser.log', 'passing browser test')}; {link(F1/'complete-browser-result.json', 'asserted results and request statuses')}.

Inputs: Editor, Street traffic.webm, CC BY3.0, https://commons.wikimedia.org/wiki/File:Street_traffic.webm . Local source `/tmp/Street_traffic.webm`, SHA256 `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`. No unauthorized stream was fetched. Moving derivative30s/300frames/10FPS/960×540. Positive36s/180 repeated licensed frames/5FPS/640×360, explicitly frozen synthetic stimulus. Repeatable preparation: `.venv.integration/bin/python scripts/prepare-browser-fixtures.py`; outputs and checksums in ignored `data/integration-browser-fixtures/manifest.json`.

Actual model: Megvii YOLOX-S COCO ONNX, SHA256 `{model}`, CPUExecutionProvider, Supervision ByteTrack. No fabricated detections, tracking IDs or accuracy labels. COCO vehicle IDs2,3,5,7 remain mapped to car,motorcycle,bus,truck; person0 is only a camera rule input.

| Acceptance ID | Browser/API/model assertion | Result/evidence |
|---|---|---|
| F1-01 | Menu → Analiză video; actual file chooser upload; crop confirmation | PASS, moving-upload.png, POST recordings201 |
| F1-02 | Draw count line with mouse; request3FPS; actual job202/progress | PASS, moving-job-progress.png |
| F1-03 | Moving inference/tracks | PASS, {moving['frames']} samples, {moving['heatmapObservations']} actual vehicle observations; {moving['counts']['unique_track_ids_by_class']} observed tracker IDs by class |
| F1-04 | Chronology/playable annotated output | PASS, output duration within500ms of30s, sampled timeline/audio not preserved; moving-annotated-result.png |
| F1-05 | Heatmap and counting | PASS, nonzero canvas/data; {moving['counts']['line_crossings']} line crossings, real PTS/track/class/confidence rows; moving-heatmap-counts.png |
| F1-06 | Frozen stimulus actual model/rules | PASS, {f1['processedFrames']} samples, {f1['candidates']} obstruction candidates; artificial stationary input, no real violation |
| F1-07 | Review-only before explicit promotion | PASS, synthetic checkbox + reason + actual first promotion; line counts stay analytics |
| F1-08 | Duplicate promotion | PASS neighboring mission tests; one canonical alert per candidate, durable unique bridge; not9 alerts from one click |
| F1-09 | Source/severity/reason | PASS, SYNTHETIC TEST + RECORDED badges, model/run/PTS provenance, no LIVE label |
| F1-10 | Redacted encrypted keyframe/clip, authenticated playback | PASS, actual browser video ready/duration;2 canonical evidence records; RSE1 in mission/model tests |
| F1-11 | Decision/note/bookmark | PASS, browser rejection dialog, persisted rejected state, observation note, current-time bookmark |
| F1-12 | Independent sensitive action | PASS, separate admin browser approves export; own approval403 in neighboring API tests |
| F1-13 | Browser package download | PASS, awaiting approval → approved → run → authenticated download |
| F1-14 | Independent integrity verification | PASS, manifest digest/all members; edited copy rejected; canonical bytes unchanged |
| F1-15 | Real backend OS restart | PASS, changed PID, same DB/keys/storage/session; rejected case, note and media survive; ciphertext hashes identical |
| F1-16 | Archive and logout | PASS, Romanian query `oprite` retrieves same case; logout204/auth-me401 |
| F1-17 | Corrupt media/disconnected upload | PASS, visible rejection/no false success; normal upload succeeds after reconnect |
| F1-18 | Cross-tenant/patrol/auditor/CSRF denial | PASS backend integration negatives; not each repeated in Chromium |
| F1-19 | Interrupted analysis worker/DB commit/export staging crashes | NOT RUN comprehensively; safe crash-orphan recovery remains backlog |
| F1-20 | Rights/export grant entry entirely through UI | PARTIAL; an actual admin API grant is a test setup precondition; source-rights editor is missing |
| F1-21 | Ground-truth incident accuracy/speed evidence | BLOCKED by absent representative labels/calibration; never claimed |

CPU observations in the selected run: mean model latency {moving['counts']['mean_model_latency_ms']:.2f}ms, p95 {moving['counts']['p95_model_latency_ms']:.2f}ms. This is local runtime performance, not accuracy or scaling. Track fragmentation/reclassification means IDs and raw observations are not true unique-vehicle counts.

Fixed actual cadence defect: anchoring each next sample to `last_pts + 1/fps` accumulated rounding (75 samples/30s requested3FPS, compressed25s output). `offline_analysis` now anchors slots to first source PTS and skips actual gaps without accumulating frame-rounding drift; browser regression asserts90 samples and duration. Source WebM declares1000 nominalFPS despite real30FPS decode cadence, so the fixtures normalize cadence explicitly and code uses decoded PTS.

Canonical routes: `/api/recordings`, `/api/recordings/{{id}}/analyses`, `/api/analyses/{{id}}`, analytics/candidates under `/api/recordings/{{id}}/analyses/{{run}}`, explicit `/candidates/{{index}}/promote`, `/api/events/{{number}}/decision`, `/notes`, `/bookmarks`, `/exports`, `/api/approvals/{{id}}/approve`, `/api/exports/{{id}}/run|link|download`, protected `/api/media/{{id}}`. Session identity supplies tenant, body tenant is not trusted. Sources: offline_video.py, offline_analytics.py, offline_promotion.py, investigation.py, casework.py, evidence.py; frontend VideoAnalysisPage, OfflinePromotion, AlertDetailPage and CaseWorkspace.

Missing broader coverage: resumed/chunked large uploads are unsupported, per-tenant quota/temporary staging expiry and complete crash matrix need work, raw rights grant remains API-driven, all event types/real-world precision and lawful deployment remain unvalidated. No original uploads/evidence were removed.
""")

write("FEATURE_2_REAL_BROWSER_E2E.md", f"""# Feature 2 — camera browser control and supervised local replay

{common}

**Controlled runtime/configuration journey: PASS. Complete all-UI onboarding: PARTIAL. External live: BLOCKED (no documented source-specific rights).** The source is LOCAL RECORDED REPLAY of a licensed moving excerpt32–35s, not a physical or external live camera.

{link(CAMERA/'camera.log', 'fresh passing runtime/browser log')}; {link(CAMERA/'commands.json', 'exact timings/command')}; {link(CAMERA/'database.json', 'owned disposable DB')}.

| Acceptance ID | Actual action/assertion | Result |
|---|---|---|
| F2-01 | Tenant admin browser creates name/slug/location | PASS, POST cameras201, registration/form screenshots |
| F2-02 | Adopt/source reference/CC BY scope/time/retention/export grant | PASS through real admin API; UI editor remains PARTIAL |
| F2-03 | Actual JSON geometry editor: road polygon, direction, rules, thresholds, targetFPS/model/hash, approved count line | PASS, invalid JSON refused; editor/draft screenshots; validated counting_lines added to canonical schema |
| F2-04 | Validate/submit immutable revision1 | PASS browser; submission alone does not run |
| F2-05 | Distinct reviewer approves and activates | PASS separate browser principal; proposer self-approval API403 |
| F2-06 | Browser Start with approved private local YAML | PASS actual `/api/cameras/{{id}}/worker/start`; legitimate scoped HMAC identity; no injected preapproved DB rows |
| F2-07 | Worker lease before source, exact model/hash/geometry, ACK1 | PASS real subprocess, real signed config/heartbeat/ACK |
| F2-08 | Moving authenticated preview | PASS2 distinct frame hashes/capture times, decoded image dimensions, actual YOLOX/ByteTrack, replay badge |
| F2-09 | Signed model-derived event | PASS actual person detection with SYNTHETIC TEST whole-scene road geometry; correct local_replay/revision/model digest;2 encrypted RSE1 media |
| F2-10 | Human review/case/export | PASS browser evidence playback/rejection; note/independent approved ZIP export and manifest verification through real API (camera export not repeated in browser) |
| F2-11 | Two actual workers contend | PASS loser exits before another source connection |
| F2-12 | Revision2 independently browser approved | PASS old process stops, UI Start creates new worker/lease, ACK2 |
| F2-13 | Source socket disconnect | PASS authoritative reconnecting, preview404, browser shows reconnecting screenshot |
| F2-14 | Source recovery | PASS actual frames/healthy/replay; recovered browser state screenshot |
| F2-15 | SIGKILL only owned worker | PASS real90-second lease expires, stale preview denied, new epoch and ACK2; no shortened TTL |
| F2-16 | Disable stops real processing | PASS accepted-alert count unchanged after disable; worker exits; independent re-enable/self-enable403 |
| F2-17 | Browser rollback revision1 | PASS old worker exits; fresh browser Start → real lease/ACK1 |
| F2-18 | Final browser disable | PASS disabled badge and actual worker exit |
| F2-19 | Scoped worker environment | PASS child /proc environment lacks DB/admin/master keys; only model/runtime+HMAC passed |
| F2-20 | Stale/unapproved config/model, role/tenant, HMAC replay | PASS backend/unit negative tests; not all UI forged cases repeated |
| F2-21 | Two-camera sustained resource isolation | NOT RUN; single-camera RSS/latency measured, no scaling claim |
| F2-22 | Visual drag/drop camera polygon editor/source-grant UI | PARTIAL; current approved geometry editor is JSON, not a visual zone editor |
| F2-23 | External live camera | BLOCKED; no public-camera fetch or assumed authorization |

Run uses actual stock model `{model}`, CPUExecutionProvider, changing licensed moving footage; whole-scene road geometry is an artificial positive stimulus. A pedestrian detection is not proof of a traffic violation. Candidate label remains SYNTHETIC TEST + LOCAL RECORDED REPLAY in preview, alert and evidence metadata. Approved counting lines are now validated server-side and replace local profile lines, avoiding two conflicting configuration sources.

Worker Start originally inherited the API environment. `camera_workers._worker_environment` now allowlists only needed OS/model/ingest settings, excluding database credentials, session/evidence keys, S3/cloud/optional AI tokens. Scratch output is under the private supervisor directory, coordinated by `RS_PIPELINE_WORK_DIR` in pipeline/media. A mismatch between the new staging root and media.key_for was caught by actual incident ingestion and corrected. Logs are unbuffered for diagnostics. BoundedWorker cancels queued uploads/retry waits on permission/revision loss; accepted evidence is preserved and no late alerts are allowed after disable.

Repeated camera harness tasks reuse per-role legitimately MFA-authenticated session state stored0600 in the unique test directory, each in a fresh browser context. This avoids exercising the production login throttle dozens of times; limits remain unchanged. The first login for each principal still uses actual password/TOTP.

Canonical lifecycle: session+CSRF admin camera/config routes → independent approve/activate → private source profile validated under cameras/ → browser `/worker/start` → existing pipeline RemoteSink HMAC config/lease/ACK/heartbeat/preview/events → protected `/api/cameras/{{id}}/preview` → canonical alerts/casework. `camera-control` APIs remain authoritative for desired/applied state; health readiness is not camera liveness. Config2 and rollback produce new real ACKs, not optimistic UI labels.

Remaining: full source authorization UI, visual geometry UX, source retry parameter reconciliation, multi-camera/long soak, encrypted/expiring retry staging and crash-orphan cleanup, production process supervision and external rights. Test-owned profiles/processes/clusters are cleaned; no user camera is stopped or reconfigured.
""")

suite_rows = []
for folder in (BACKEND, F1, CAMERA, pipeline, FRONT, PWA):
    for row in json.loads((folder / "commands.json").read_text()):
        suite_rows.append(f"| `{row['name']}` | `{row['start']}` | {row['duration_s']}s | {row['exit_code']} | {link(folder/(row['name']+'.log'))} |")
write("TEST_EXECUTION_LEDGER_UPDATED.md", f"""# Fresh browser mission execution ledger

{common}

| Suite | Fresh outcome | Evidence |
|---|---|---|
| Entire backend |423 passed,0 failed,2 skipped | {link(BACKEND/'backend.log')} |
| Entire root/pipeline |221 passed,0 failed,0 skipped | {link(pipeline/'pipeline.log')} |
| Focused browser recorded |1 passed,0 failed,0 skipped | {link(F1/'browser.log')} |
| Focused camera browser/real worker |1 passed,0 failed,0 skipped | {link(CAMERA/'camera.log')} |
| React tests |24 passed,0 failed,0 skipped | {link(FRONT/'test.log')} |
| React lint/build incl.TypeScript |PASS | {link(FRONT/'commands.json')} |
| Secure PWA tests |9 passed,0 failed,0 skipped | {link(PWA/'test.log')} |
| Secure PWA lint/format/build incl.TypeScript |PASS | {link(PWA/'commands.json')} |
| Native Chromium auth |5 role journeys passed,0 JS page errors | {link(SESSION/'auth-final-code.log')} |
| Fresh migrations |base→0022 in each B cluster; one head; lookup-owner/RLS assertions | backend/new cluster logs |
| Live schema |0022,32 named ENABLE+FORCE RLS tables, app NOBYPASS, tenant-negative read | {link(SESSION/'active-runtime-final.json')} |

The two focused cases are included in the423 backend total; do not add them as distinct unique tests. Backend count rose from historical419/422 to423 because the full process-restart browser journey was added. Root count rose213→214 for cancellation, then221 for approved counting-line validation/reconciliation. React count24 includes provenance/redaction regressions; PWA remains9. Warnings are actual ByteTrack removal/SQLAlchemy Result.tuples deprecations, not accuracy warnings suppressed to pass.

Two legacy backend tests remain skipped by their own opt-ins: test_real_yolo_e2e requires RS_RUN_REAL_YOLO_E2E and an in-tree weight/media path; test_offline_analytics_real_video requires RS_OFFLINE_ANALYTICS_REAL_VIDEO. This run does not claim those legacy harnesses passed. The new mission/browser/camera tests genuinely execute the stock model and Chromium separately. PWA HTTPS installation and field accuracy are NOT RUN.

| Command stage | UTC start | Duration | Exit | Bounded log |
|---|---|---|---|---|
{chr(10).join(suite_rows)}

Repeat from integration root: `python3 scripts/verify-integration.py backend`, then `pipeline`, `frontend`, `pwa`; focused `browser` and `camera` create independent owned clusters. Requirements are .venv.integration, Node22, local licensed source, configured verified model, ffmpeg and installed Playwright Chromium. No environment defaults can reset the existing native DB; the runner clears RS_/VITE_/DATABASE_URL, uses unique guarded names/ports and stops only its own cluster.

Failed experiments are retained. Earlier camera-ui-start run failed on duplicate/obscured selectors (harness), then private media-root mismatch (fixed pipeline/media), then repeated browser password logins hit existing throttle (fixed session reuse, not weakened limits). Full run20261110T233508Z-7edbc976 had422 pass/1 fail/2 skip at that checkpoint; the final full result above supersedes it. Earlier requested3FPS run produced75 frames and has been replaced by the90-frame regression proof. Failed login-navigation wait assumptions and nominal source timestamp scan were corrected without fabricating results.

No secrets/cookies/QR seeds/ZIP media are copied into this ledger. Temporary test evidence warnings are intentional: B uses a temporary store and verifies persistence across process restart, not across fixture teardown. Native A data is preserved.
""")

# Preserve all original IDs and untested statuses. Add scoped evidence; a composite requirement
# is not promoted to all-green because one tested subflow passed.
matrix = D / "README_COVERAGE_MATRIX.csv"
rows = list(csv.DictReader(matrix.open()))
fields = list(rows[0])
assert len(rows) == 185 and len({r['id'] for r in rows}) == 185
mapping = {
    'A02': ('roadsentinel/detector.py; roadsentinel/pipeline.py; backend/app/services/offline_analysis.py', 'backend/tests/test_browser_complete_journey.py; backend/tests/test_managed_live_runtime.py', 'FEATURE_1_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A03': ('roadsentinel/sources.py; roadsentinel/replay.py', 'backend/tests/test_managed_live_runtime.py', 'FEATURE_2_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A04': ('backend/app/services/camera_config.py; roadsentinel/remote_config.py', 'tests/test_counting_config.py', 'FEATURE_2_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A10': ('backend/app/services/evidence.py; backend/app/services/offline_promotion.py', 'backend/tests/test_browser_complete_journey.py', 'FEATURE_1_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A15': ('frontend/src/components/CaseWorkspace.tsx; backend/app/api/investigation.py', 'backend/tests/test_browser_complete_journey.py', 'FEATURE_1_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A16': ('frontend/src/components/CameraControlPanel.tsx; backend/app/services/camera_workers.py', 'backend/tests/test_managed_live_runtime.py', 'FEATURE_2_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A18': ('backend/app/services/auth.py; frontend/src/pages/LoginPage.tsx; backend/app/services/lookup_roles.py', 'frontend/e2e/live-login-recovery.mjs; backend/tests/test_lookup_ownership.py', 'REAL_BROWSER_AUTH_MFA_VERIFICATION.md', 'VERIFIED REAL END-TO-END'),
    'A35': ('backend/app/api/camera_control.py; backend/app/api/investigation.py; frontend/src/components/CaseWorkspace.tsx', 'backend/tests/test_managed_live_runtime.py; backend/tests/test_browser_complete_journey.py', 'README_COVERAGE_UPDATE.md', 'PARTIAL'),
    'A23': ('frontend/src/pages/VideoAnalysisPage.tsx; backend/app/services/offline_analysis.py', 'backend/tests/test_browser_complete_journey.py', 'FEATURE_1_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'A24': ('roadsentinel/live.py; roadsentinel/remote_config.py; backend/app/services/camera_workers.py', 'backend/tests/test_managed_live_runtime.py', 'FEATURE_2_REAL_BROWSER_E2E.md', 'VERIFIED REAL INPUT PARTIAL'),
    'REQ-0088': ('backend/app/services/auth.py; frontend/src/pages/LoginPage.tsx', 'frontend/e2e/live-login-recovery.mjs', 'REAL_BROWSER_AUTH_MFA_VERIFICATION.md', 'VERIFIED REAL END-TO-END'),
}
for row in rows:
    if row['id'] in mapping:
        owner, test, evidence, status = mapping[row['id']]
        row.update(code_owner=owner, test_path=test, evidence_link=evidence, current_status=status)
        row['verification_limit'] = 'Scoped current Chromium/model/DB proof; wider category limitations remain in linked acceptance matrix.'
    if row['id'] in ('REQ-0012', 'REQ-0024', 'REQ-0035', 'REQ-0051', 'REQ-0091'):
        row['evidence_link'] = 'REAL_BROWSER_AUTH_MFA_VERIFICATION.md'
        row['verification_limit'] = 'Actual integration auth/roles/session pass; composite PWA/TLS/legacy routes not all retested.'
with matrix.open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
counts = dict(sorted(Counter(row['current_status'] for row in rows).items()))
write('README_COVERAGE_UPDATE.md', f"""# README acceptance reconciliation — fresh browser mission

{common}

All185 existing IDs are preserved (150 source paragraph/table records +35 category records). **These are coverage records, not185 passing feature tests.** Current status totals: `{json.dumps(counts, sort_keys=True)}`. Full before audit remains immutable; old after/ledger statements are retained as historical checkpoints with a current superseding notice. Model performance is not accuracy; synthetic incident and local replay remain explicit.

Current README{len((ROOT/'README.md').read_text().splitlines())} lines, API{len((ROOT/'API.md').read_text().splitlines())} lines. README's stale assertion that native auth still required repair was corrected after actual four-role Chromium proof. Other prior statements claiming zero eligible camera events/API-only approval/CLI-only start are superseded by FEATURE_2_REAL_BROWSER_E2E.md. Full source rights and visual camera editor remain incomplete, so they were not turned green.

| Requirement | Source/code | Executed proof | Remaining criterion |
|---|---|---|---|
| A02/A04/A23 | detector/offline_analysis/VideoAnalysisPage | moving30s,90 samples, actual IDs/countline/heatmap/browser playback | ground-truth counting/scene calibration |
| A03/A16/A24/A33 | sources/camera_config/camera_workers/remote_config | browser register/config/independent approval/Start/ACK/revision/rollback/outage/disable | rights UI, multicamera soak, staging cleanup |
| A05–A09 | rules/offline candidates | stationary positive on frozen real-model pixels; pedestrian positive on artificial zone | all real incident classes, false-alert rates |
| A10/A11/A15 | ingest/evidence/investigation | signed replay candidate, RSE1, actual review, independent package SHA verification | encrypted retry staging, crash-orphan matrix, independent custody |
| A12–A14 | alert/detail/archive | actual rejection/note/bookmark and archive after OS restart | patrol assignment/push/PWA browser coverage |
| A18/A26 | auth/db/lookup_roles/migrations | native four-role MFA, fresh enrollment B, isolated repeat/partial seed,32 FORCE RLS | production external identity/HTTPS/long idle soak |
| A17/A27/A28 | Vite/client/PWA/tests | real backend proxy,24/9 client tests, lint/type/build,423/2 backend,221 root | installed PWA, responsive/accessibility audit, deployment/CI |
| A19/A20/A21/A22/A30–A32 | key/privacy/model/legal docs | safeguards retained, digest pinned, external AI not enabled | KMS/anchor/legal/representative metrics/external consent |

Each untouched row retains its conservative earlier status; no claim is made that every linked-spec statement received a new browser assertion. For precise scope, use F1-01–21 and F2-01–23 in the two browser reports, not a count of modules or HTTP200s. Residual items are ranked in REMAINING_FEATURES_MASTER_BACKLOG.md.
""")

write('FINAL_BROWSER_HANDOFF.md', f"""# Operator handoff — existing browser login verified

Open **http://127.0.0.1:5175/login**. Backend **http://127.0.0.1:8003**; exact verified DB **rsint_20261110b,127.0.0.1:55446**, revision0022. Operator **operator.a@roadsentinel.local**, tenant **unit-a**, no tenant input required. Admin **admin.a@roadsentinel.local** also verified. Password remains in protected `backend/.integration-test-credentials.json`0600; it is deliberately not reproduced here.

MFA is enabled and already enrolled. Open private `backend/.integration-authenticators/operator.a.html` locally and import its QR into your authenticator, then enter its current code. Or, in your own local terminal only:

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/integration_totp.py operator.a@roadsentinel.local
```

The verification ends with logout; your browser starts a new legitimate MFA session. {link(shots/'A-auth-live-operator.png', 'fresh native operator dashboard')}; {link(SESSION/'auth-final-code.log', 'five native login journeys')}.

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

Feature1 selected fixture journey passes; full product remains PARTIAL for source-rights UI, complete failure/retention matrix and real-world incident validation. Feature2 controlled replay passes; all-UI onboarding remains PARTIAL because adoption/source grant setup is API-driven and geometry is JSON, not a visual editor. External camera is BLOCKED by rights. No production/legal/accuracy claim. No GitHub write or original project/database change; {link(SESSION/'reference-preservation.json', '608 source hashes and both HEADs unchanged')}.

Read first: REAL_BROWSER_AUTH_MFA_VERIFICATION.md, FEATURE_1_REAL_BROWSER_E2E.md, FEATURE_2_REAL_BROWSER_E2E.md, TEST_EXECUTION_LEDGER_UPDATED.md, README_COVERAGE_UPDATE.md and REMAINING_FEATURES_MASTER_BACKLOG.md.
""")

# Superseding notices keep prior detailed evidence inspectable instead of rewriting history.
notice = (f"> Current browser verification ({NOW}): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), "
          "[fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. "
          "Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.\n\n")
for name in ('POST_INTEGRATION_README_AUDIT_AFTER.md', 'TEST_EXECUTION_LEDGER.md',
             'FULL_INTEGRATION_E2E_VALIDATION.md', 'ACTUAL_BROWSER_LOGIN_EVIDENCE.md',
             'FINAL_LOGIN_HANDOFF.md', 'FINAL_ENGINEERING_HANDOFF.md',
             'POST_INTEGRATION_RUNTIME_VERIFICATION.md', 'OPERATOR_DEMO_QUICKSTART.md'):
    file = D / name
    text = file.read_text()
    if not text.startswith('> Current browser verification'):
        file.write_text(notice + text)
for name, report in (('FEATURE_01_AI_INCIDENT_TO_OPERATOR.md', 'FEATURE_1_REAL_BROWSER_E2E.md'),
                     ('FEATURE_02_AUTHORIZED_LIVE_CAMERA.md', 'FEATURE_2_REAL_BROWSER_E2E.md')):
    file = ROOT / 'docs/implementation' / name
    text = file.read_text()
    marker = f"> Fresh browser mission evidence: [../audits/{report}](../audits/{report}). "
    if not text.startswith(marker):
        file.write_text(marker + 'Prior acceptance/count statements below are preserved historical checkpoints.\n\n' + text)
print('Generated dated browser reports, screenshots/index and scoped185-row reconciliation.')
