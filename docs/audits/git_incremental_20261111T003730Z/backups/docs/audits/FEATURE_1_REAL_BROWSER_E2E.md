# Feature 1 — real browser recorded-video journey

Updated 2026-11-10T23:54:00.244161+00:00 (local date 2026-11-11, Europe/Bucharest).

Runtime A: existing UI5175 → API8003 → `rsint_20261110b@127.0.0.1:55446`, app `rsint_app_261110b`, Alembic0022.
Runtime B: new uniquely named clusters, databases and test-owned files; actual identities are in each run's `database.json`.
Runtime C: both original source trees/databases, read-only and never used for writes.
All browser actions use genuine Chromium156.0.8078.4 via Playwright, real Vite/FastAPI/PostgreSQL, no network interceptions or mocked success responses.
[Live identity/proxy/RLS proof](runtime_verification/browser-20261111T011541+0200/active-runtime-final.json); [timestamped screenshot hashes](REAL_BROWSER_SCREENSHOTS/2026-11-11/index.json).


**Selected complete fixture journey: PASS. Broader feature: PARTIAL.** Moving video proves actual detection/tracking/analytics. The separately frozen positive proves the incident workflow on SYNTHETIC TEST material. Neither proves real incident accuracy.

[Executed command/timing](runtime_verification/runs/20261110T232618Z-eb8e75d7/commands.json); [disposable DB](runtime_verification/runs/20261110T232618Z-eb8e75d7/database.json); [passing browser test](runtime_verification/runs/20261110T232618Z-eb8e75d7/browser.log); [asserted results and request statuses](runtime_verification/runs/20261110T232618Z-eb8e75d7/complete-browser-result.json).

Inputs: Editor, Street traffic.webm, CC BY3.0, https://commons.wikimedia.org/wiki/File:Street_traffic.webm . Local source `/tmp/Street_traffic.webm`, SHA256 `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`. No unauthorized stream was fetched. Moving derivative30s/300frames/10FPS/960×540. Positive36s/180 repeated licensed frames/5FPS/640×360, explicitly frozen synthetic stimulus. Repeatable preparation: `.venv.integration/bin/python scripts/prepare-browser-fixtures.py`; outputs and checksums in ignored `data/integration-browser-fixtures/manifest.json`.

Actual model: Megvii YOLOX-S COCO ONNX, SHA256 `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`, CPUExecutionProvider, Supervision ByteTrack. No fabricated detections, tracking IDs or accuracy labels. COCO vehicle IDs2,3,5,7 remain mapped to car,motorcycle,bus,truck; person0 is only a camera rule input.

| Acceptance ID | Browser/API/model assertion | Result/evidence |
|---|---|---|
| F1-01 | Menu → Analiză video; actual file chooser upload; crop confirmation | PASS, moving-upload.png, POST recordings201 |
| F1-02 | Draw count line with mouse; request3FPS; actual job202/progress | PASS, moving-job-progress.png |
| F1-03 | Moving inference/tracks | PASS, 90 samples, 1013 actual vehicle observations; {'bus': 20, 'car': 37, 'truck': 8} observed tracker IDs by class |
| F1-04 | Chronology/playable annotated output | PASS, output duration within500ms of30s, sampled timeline/audio not preserved; moving-annotated-result.png |
| F1-05 | Heatmap and counting | PASS, nonzero canvas/data; {'a_to_b': 4} line crossings, real PTS/track/class/confidence rows; moving-heatmap-counts.png |
| F1-06 | Frozen stimulus actual model/rules | PASS, 72 samples, 8 obstruction candidates; artificial stationary input, no real violation |
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

CPU observations in the selected run: mean model latency 140.99ms, p95 199.70ms. This is local runtime performance, not accuracy or scaling. Track fragmentation/reclassification means IDs and raw observations are not true unique-vehicle counts.

Fixed actual cadence defect: anchoring each next sample to `last_pts + 1/fps` accumulated rounding (75 samples/30s requested3FPS, compressed25s output). `offline_analysis` now anchors slots to first source PTS and skips actual gaps without accumulating frame-rounding drift; browser regression asserts90 samples and duration. Source WebM declares1000 nominalFPS despite real30FPS decode cadence, so the fixtures normalize cadence explicitly and code uses decoded PTS.

Canonical routes: `/api/recordings`, `/api/recordings/{id}/analyses`, `/api/analyses/{id}`, analytics/candidates under `/api/recordings/{id}/analyses/{run}`, explicit `/candidates/{index}/promote`, `/api/events/{number}/decision`, `/notes`, `/bookmarks`, `/exports`, `/api/approvals/{id}/approve`, `/api/exports/{id}/run|link|download`, protected `/api/media/{id}`. Session identity supplies tenant, body tenant is not trusted. Sources: offline_video.py, offline_analytics.py, offline_promotion.py, investigation.py, casework.py, evidence.py; frontend VideoAnalysisPage, OfflinePromotion, AlertDetailPage and CaseWorkspace.

Missing broader coverage: resumed/chunked large uploads are unsupported, per-tenant quota/temporary staging expiry and complete crash matrix need work, raw rights grant remains API-driven, all event types/real-world precision and lawful deployment remain unvalidated. No original uploads/evidence were removed.
