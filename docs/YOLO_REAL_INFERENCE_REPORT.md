# Real YOLO inference report

## Romanian HLS adapter status — 2026-11-07

The configured-source layer now recognizes HLS master playlists, selects variants within
configured resolution/bandwidth limits, rejects cross-host resource references by default,
and opens the selected transport through OpenCV/FFmpeg with bounded timeouts. A generated
local MPEG-TS playlist decoded in the 24-test source suite. No third-party Romanian playlist
or segment was decoded; this is not an additional YOLO run and provides no Romanian FPS,
detection, tracking, counting, or authorization evidence. Existing model measurements below
remain CPU recorded-replay measurements.

## 2026-11-07 physical camera availability update

The code now accepts explicit `device:N` UVC input through the existing YOLOX-S ONNX/ByteTrack
pipeline. `cameras/local-uvc.yaml` contains no replay fallback and no invented calibration; rules
are disabled until configured. The bounded probe command
`timeout 15s .venv/bin/python -m scripts.probe_uvc_camera --device-index 0 --seconds 3` exited 2
with `/dev/video0` missing. Zero physical frames were captured; consequently physical-live
detection, boxes, FPS, tracking, persistence and browser evidence are unavailable. The measurements
below remain recorded-video replay results. No NVIDIA driver, global package or system setting was
changed.

Last verified: 2026-11-06 (local CPU run)

## Runtime and provenance

- Detector: Megvii YOLOX-S COCO, ONNX; official release artifact from the [Megvii YOLOX release](https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx).
- Model SHA-256: `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`.
- Runtime: Python 3.12.3 project `.venv`, ONNX Runtime 1.23.2 `CPUExecutionProvider`, Supervision 0.30.7 ByteTrack. No PyTorch/Ultralytics is needed by this path.
- Device: Intel i7-13650HX CPU; NVIDIA driver/GPU unavailable. Peak process RSS was 447.2 MB.
- License: YOLOX repository Apache-2.0. The model is a COCO-trained upstream artifact; retain its provenance and review applicable notices before redistribution. Ultralytics was avoided because its AGPL obligations do not fit the private-development constraint as currently understood. This is not legal advice.

## Input and rights

Input was the recorded Wikimedia Commons file [Street traffic.webm](https://commons.wikimedia.org/wiki/File:Street_traffic.webm), credited there to Editor and marked CC BY 3.0. It depicts a San Francisco street, not a Romanian camera. Local downloaded source SHA-256: `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`. Attribution is required if the footage is redistributed. This was recorded-video replay, not external LIVE or locally captured live simulation.

## Reproduction and observed results

Command (camera config was a local temporary test config; no source URL or credentials):

```bash
RS_SAVE_DETECTIONS=1 timeout --signal=TERM --kill-after=5s 180s \
  .venv/bin/python -m roadsentinel.pipeline /tmp/yolo-commons-smoke.yaml \
  --model models/yolox_s.onnx --no-wandb --imgsz 640 --frame-stride 10 --max-seconds 36
```

The command completed with exit code 0. It processed 105 sampled frames across 34.9 seconds (source cadence about 30 FPS; inference sampling about 3 FPS). Model inference latency: p50 84.57 ms, p95 93.07 ms, p99 106.22 ms. Overall pipeline throughput was 1.84 sampled frames/s including tracking, annotation, and output. No decode failures or reconnects were reported.

- 1,085 tracked observations and 67 unique tracks.
- Track counts by class: bus 13, car 32, truck 16, bicycle 1, person 5.
- Counting-line crossings: 9 total (bus 4, car 4, truck 1; 5 negative and 4 positive direction).
- Per-frame boxes/classes/confidences/track IDs are in ignored local artifact `data/vision/yolo-commons-smoke-1793938099.jsonl` (1,103 JSONL records, including frame records); annotated output is `data/media/yolo-commons-smoke/annotated.mp4` (redaction enabled before rendering).
- Model file and output artifacts are local; no footage or detections were committed.

The tracker/class totals and line-crossing measurements are pipeline outputs, not labeled ground truth. No precision/recall, mAP, tracking quality, count accuracy, or incident accuracy was measured. Congestion rule evaluation ran and produced zero candidates on this clip; that negative result does not validate the rule. No incident event was emitted, so this run did not exercise secure event upload, PostgreSQL persistence, operator review, or dashboard rendering.

## Current acceptance boundary

Verified: actual official weights loaded; real vehicle boxes/classes/confidences produced; ByteTrack IDs and configured line counts produced; measured runtime and memory recorded. A local live-replay → signed API → PostgreSQL → authenticated React telemetry path is also verified below. Still unverified: authorized external Romanian live source, model-generated incident, and incident review using the same live detector output.

## Local live-replay vertical slice (2026-11-06)

The integration test served the licensed clip continuously from a loopback-only MJPEG server
(`roadsentinel.replay`) and consumed it through the supervised network capture adapter. It is marked
`source_replay: true`; this is **not** an external Romanian feed. YOLOX-S/ByteTrack sent signed
heartbeats using a camera-scoped HMAC service account to a real localhost FastAPI server. PostgreSQL
stored telemetry under the camera tenant. The authenticated React app fetched the actual
`/api/cameras` response and rendered camera detail while inference was active.

Run from `backend/` (requires the locally approved sample/model, `.venv`, Node 22, Playwright
browser, and disposable PostgreSQL test cluster on port 55438):

```bash
RS_RUN_REAL_YOLO_E2E=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

Latest result: **1 passed** (2026-11-06). The loopback source served 10 FPS; the CPU pipeline
processed 1.587 FPS. The persisted snapshot reported 65 frames, 342 tracked observations, 26
tracks (bus 11, car 6, truck 9), and two line crossings (bus). Source health was healthy at
1920×1080 with zero reconnects/failures. Real YOLO emitted no incident candidate (`events: 0`).

At persistence, latency p50/p95/p99 was 84.49/99.41/103.85 ms and peak RSS was 346.8 MB. Playwright
saw the next backend heartbeat update reflected in camera detail within 2,387 ms, with 147 cumulative
observations and two crossings. A separate signed `SYNTHETIC TEST` candidate was rejected in the
authenticated browser; the test then asserted PostgreSQL status and audit persistence. This is
heartbeat-change-to-UI-refresh delay, not frame-to-alert latency.

### Authenticated annotated frame evidence (2026-11-06)

The preview path now publishes redacted, annotated JPEG frames through the existing camera-scoped
HMAC identity. The backend keeps only the newest frame per `(tenant, camera)` in memory, with a
four-second freshness TTL and 2 MiB per-frame limit; it does not persist frame JPEGs to PostgreSQL.
The browser retrieves the frame via the authenticated camera detail endpoint, not from the source
URL. UI labels remain `RECORDED REPLAY` for the loopback video source.

Bounded real-model E2E command and result:

```bash
cd backend
RS_RUN_REAL_YOLO_E2E=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

Result: **1 passed**. The browser test waited for successful natural image dimensions and a changed
captured-frame timestamp/sequence, then saved `camera-live-overlay.png` in the pytest temporary
directory; the test output printed the absolute path. The frame annotations include model class,
confidence, tracker ID, count-line labels and an ISO UTC timestamp. This verifies actual changing
annotated YOLO frames in authenticated Chromium during the loopback replay test, alongside real API
and PostgreSQL telemetry. The preview is transient and tenant/camera scoped. It does not prove a
physical camera, external Romanian feed, or persistent image-evidence storage.

At the E2E telemetry snapshot for this run: 63 processed frames, 315 detections, 25 observed tracks,
2 line crossings, ~1.54 CPU pipeline FPS; inference p50/p95/p99 ~86.8/107.2/117.8 ms; process RSS
~344.5 MB. These are a short run on the recorded San Francisco CC BY 3.0 clip and one CPU machine,
not a sustained stability or accuracy benchmark. The source generated no incident candidate.

This is one recorded San Francisco scene on one CPU machine. It does not validate accuracy, tracking
quality, count error against ground truth, multiple-camera capacity, adverse conditions, or incident
precision. Per-camera summaries (class tracks, observation totals, FPS/latency/memory, source health,
model/hash and crossings) use existing tenant-scoped `cameras.status_info` JSONB and `/api/cameras`.
Per-frame boxes/confidences remain in the optional local JSONL detection log; they are not persisted
in PostgreSQL. The integration run enabled only the wrong-way rule and emitted no incident. Synthetic
rule regression coverage is in `tests/test_rules.py` and `tests/test_rules_rates.py`.

### Repeat after camera-catalog UI change (2026-11-06)

The actual-model full E2E was run again after adding the Romanian read-only discovery panel:

```bash
cd backend
RS_RUN_REAL_YOLO_E2E=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

Exit code 0, **1 passed**. The persisted telemetry snapshot reported 64 processed frames, 326
detections, 25 observed track IDs, 2 line crossings (bus), sampled pipeline FPS 1.566, inference
p50/p95/p99 88.61/102.62/105.40 ms, and peak process RSS 369.8 MB. Source health was healthy,
1920×1080, with 0 failures and 0 reconnects; the source was explicitly marked replay. The worker
continued after the browser assertion and later reported 69 frames, 29 tracks and 3 crossings;
these are later cumulative totals, not the same fixed-interval snapshot.

The browser image and overlays are preserved locally at
`data/vision/evidence/real-yolox-loopback-replay-2026-11-06.png` (SHA-256
`d32e7c04d4326a8626dd1ed9a1e101ffb8bc8b6041d80554dbcfddb933f268c7`). It visibly shows model
boxes/labels, ByteTrack IDs, the configured count line, UTC capture timestamp, and replay label.
The screenshot is redacted and local-only. It does not establish detection accuracy.

The final catalog-inclusive browser run passed after correcting its expected candidate-row count to
26. Browser output included `REAL_ROMANIAN_CATALOG_OK entries=26 enabled=0`. Persisted snapshot:
65 frames, 329 detections, 26 tracks, 2 line crossings, 1.592 FPS, p50/p95/p99 inference
87.39/106.24/125.74 ms, RSS 347.1 MB. The final screenshot is
`data/vision/evidence/real-yolox-loopback-replay-catalog-e2e-2026-11-06.png` (SHA-256
`6241f4ab2274e5ecac0d12d7e84e41ef824731d17fb579866fa36a756665111f`).

After moving the catalog module out of the repository's ignored `data/` path, the full E2E was run
once more against the final source tree and passed (exit 0). The browser confirmed 26 candidate rows
with zero feeds enabled. Latest persisted test interval: 66 frames, 336 detections, 26 tracks, 2
crossings; 1.617 FPS, latency p50/p95/p99 86.88/103.95/108.11 ms, peak RSS 344.7 MB; camera-detail
heartbeat refresh was 1,256 ms. The final local screenshot is
`data/vision/evidence/real-yolox-loopback-replay-final-e2e-2026-11-06.png` (SHA-256
`7389edd0a2fc9eb0ccd5618a7578044c628628ae09bb4ac469bd651bad886e6d`).
