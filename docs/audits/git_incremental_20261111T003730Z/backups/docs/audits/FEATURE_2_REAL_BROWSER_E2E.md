# Feature 2 — camera browser control and supervised local replay

Updated 2026-11-10T23:54:00.244161+00:00 (local date 2026-11-11, Europe/Bucharest).

Runtime A: existing UI5175 → API8003 → `rsint_20261110b@127.0.0.1:55446`, app `rsint_app_261110b`, Alembic0022.
Runtime B: new uniquely named clusters, databases and test-owned files; actual identities are in each run's `database.json`.
Runtime C: both original source trees/databases, read-only and never used for writes.
All browser actions use genuine Chromium156.0.8078.4 via Playwright, real Vite/FastAPI/PostgreSQL, no network interceptions or mocked success responses.
[Live identity/proxy/RLS proof](runtime_verification/browser-20261111T011541+0200/active-runtime-final.json); [timestamped screenshot hashes](REAL_BROWSER_SCREENSHOTS/2026-11-11/index.json).


**Controlled runtime/configuration journey: PASS. Complete all-UI onboarding: PARTIAL. External live: BLOCKED (no documented source-specific rights).** The source is LOCAL RECORDED REPLAY of a licensed moving excerpt32–35s, not a physical or external live camera.

[fresh passing runtime/browser log](runtime_verification/runs/20261110T234129Z-259e8c90/camera.log); [exact timings/command](runtime_verification/runs/20261110T234129Z-259e8c90/commands.json); [owned disposable DB](runtime_verification/runs/20261110T234129Z-259e8c90/database.json).

| Acceptance ID | Actual action/assertion | Result |
|---|---|---|
| F2-01 | Tenant admin browser creates name/slug/location | PASS, POST cameras201, registration/form screenshots |
| F2-02 | Adopt/source reference/CC BY scope/time/retention/export grant | PASS through real admin API; UI editor remains PARTIAL |
| F2-03 | Actual JSON geometry editor: road polygon, direction, rules, thresholds, targetFPS/model/hash, approved count line | PASS, invalid JSON refused; editor/draft screenshots; validated counting_lines added to canonical schema |
| F2-04 | Validate/submit immutable revision1 | PASS browser; submission alone does not run |
| F2-05 | Distinct reviewer approves and activates | PASS separate browser principal; proposer self-approval API403 |
| F2-06 | Browser Start with approved private local YAML | PASS actual `/api/cameras/{id}/worker/start`; legitimate scoped HMAC identity; no injected preapproved DB rows |
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

Run uses actual stock model `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`, CPUExecutionProvider, changing licensed moving footage; whole-scene road geometry is an artificial positive stimulus. A pedestrian detection is not proof of a traffic violation. Candidate label remains SYNTHETIC TEST + LOCAL RECORDED REPLAY in preview, alert and evidence metadata. Approved counting lines are now validated server-side and replace local profile lines, avoiding two conflicting configuration sources.

Worker Start originally inherited the API environment. `camera_workers._worker_environment` now allowlists only needed OS/model/ingest settings, excluding database credentials, session/evidence keys, S3/cloud/optional AI tokens. Scratch output is under the private supervisor directory, coordinated by `RS_PIPELINE_WORK_DIR` in pipeline/media. A mismatch between the new staging root and media.key_for was caught by actual incident ingestion and corrected. Logs are unbuffered for diagnostics. BoundedWorker cancels queued uploads/retry waits on permission/revision loss; accepted evidence is preserved and no late alerts are allowed after disable.

Repeated camera harness tasks reuse per-role legitimately MFA-authenticated session state stored0600 in the unique test directory, each in a fresh browser context. This avoids exercising the production login throttle dozens of times; limits remain unchanged. The first login for each principal still uses actual password/TOTP.

Canonical lifecycle: session+CSRF admin camera/config routes → independent approve/activate → private source profile validated under cameras/ → browser `/worker/start` → existing pipeline RemoteSink HMAC config/lease/ACK/heartbeat/preview/events → protected `/api/cameras/{id}/preview` → canonical alerts/casework. `camera-control` APIs remain authoritative for desired/applied state; health readiness is not camera liveness. Config2 and rollback produce new real ACKs, not optimistic UI labels.

Remaining: full source authorization UI, visual geometry UX, source retry parameter reconciliation, multi-camera/long soak, encrypted/expiring retry staging and crash-orphan cleanup, production process supervision and external rights. Test-owned profiles/processes/clusters are cleaned; no user camera is stopped or reconfigured.
