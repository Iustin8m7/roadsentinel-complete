# End-to-end local demo evidence

## 2026-11-07 registry and HLS adapter follow-up

The HLS adapter now has local fixture coverage (24 source tests pass), and the candidate
registry loads as 35 validated records. Frontend typecheck, Vitest (15 passed), lint, and
production build passed. The discovery endpoint's authenticated PostgreSQL/browser path was
not executed in this session because the configured database servers were unavailable. This
follow-up produced no new Romanian video evidence and does not alter the replay-vs-live status
below.

## 2026-11-07 physical-live result

**BLOCKED by missing hardware/source prerequisite.** No `/dev/video*` path was present. The bounded
UVC probe exited 2 with `CAMERA_UNAVAILABLE: camera device /dev/video0 is missing`. No physical
frame was captured, so there is no honest LIVE overlay/API/PostgreSQL/Chromium screenshot or metric.
The recorded loopback replay evidence below remains a successful but distinct replay demonstration;
its artifacts must not be presented as a physical camera. See
`LIVE_CAMERA_OPERATOR_GUIDE.md` for the exact plug-and-probe action.

## Replay regression after source-label change — 2026-11-07

Command from `backend/` against the disposable `/tmp` PostgreSQL cluster (port 55438):

```bash
RS_RUN_REAL_YOLO_E2E=1 RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
  ../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

Final run: **exit 0, 1 passed**. The initial rerun failed only because the browser assertion still
looked for the prior ambiguous text `REPLAY local`; it was changed to assert `RECORDED REPLAY`
within the preview region. The next run then encountered a strict-locator ambiguity because the
label appears in three UI locations; the assertion was scoped to the preview region and rerun.
Final browser evidence: `REAL_API_CAMERA_DETAIL_OK detections=146 crossings=2
heartbeat_refresh_ms=1196`, `REAL_API_ANNOTATED_PREVIEW_OK`, `REAL_API_SYNTHETIC_ALERT_REVIEW_OK`
(rejected), and 26 Romanian candidate entries / zero enabled. This source is still the explicit
loopback recorded-video replay.

The latest persisted checkpoint reported 65 frames, 318 detections, 23 observed tracks, two line
crossings, 1.593 processing FPS, inference p50/p95/p99 85.65/103.09/118.39 ms, and process peak RSS
347.5 MB. The process log had a larger cumulative count at shutdown because telemetry is sampled
while processing continues; the API snapshot is the value independently asserted against its
tenant-scoped camera record. Local screenshot:
`data/vision/evidence/recorded-replay-overlay-2026-11-07.png`, SHA-256
`8ecb11f1420fea210943ba5ee60ee16eae3fb3e2748962636250e8b1dd252314`.

Last verified: 2026-11-06. All work and artifacts remain local.

## Real inference and browser overlay

Command, run from `backend/`, using the disposable local PostgreSQL test cluster at port 55438:

```bash
RS_RUN_REAL_YOLO_E2E=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

Latest result: **exit 0, 1 passed**. The test launches the actual local replay relay, YOLOX-S ONNX
pipeline, FastAPI server, isolated PostgreSQL schema/data, authenticated Chromium operator and
frontend. No API response route is stubbed in this test.

Observed persisted sample at the UI/API assertion:

| Metric | Value |
|---|---:|
| Processed frames | 64 |
| YOLO detections | 326 |
| Observed ByteTrack IDs | 25 |
| Configured line crossings | 2 (bus) |
| Sampled pipeline FPS | 1.566 |
| Inference latency p50/p95/p99 | 88.61 / 102.62 / 105.40 ms |
| Peak process RSS | 369.8 MB |
| Source health | healthy; 1920×1080; 0 failures; 0 reconnects |
| Source label | `RECORDED REPLAY` (loopback MJPEG from licensed recorded clip) |

The browser observed actual changing annotated JPEG frame timestamps/sequences and actual API-backed
camera counters. The JPEG is tenant/camera authenticated, is transient in a 4-second in-memory
buffer, and is not persisted to PostgreSQL. The rendered image shows redacted YOLO boxes/classes,
confidence, tracker IDs, configured count line and UTC frame timestamp.

Historical screenshot `data/vision/evidence/real-yolox-loopback-replay-final-e2e-2026-11-06.png` was omitted from this snapshot. Its historical claim is not current-run evidence; see `audits/screenshots/recorded-review.png` for this mission's separate executed recorded-source test.

Latest local artifact: `data/vision/evidence/real-yolox-loopback-replay-catalog-e2e-2026-11-06.png`,
SHA-256 `6241f4ab2274e5ecac0d12d7e84e41ef824731d17fb579866fa36a756665111f`. Final source-tree run:
`data/vision/evidence/real-yolox-loopback-replay-final-e2e-2026-11-06.png`, SHA-256
`7389edd0a2fc9eb0ccd5618a7578044c628628ae09bb4ac469bd651bad886e6d`. Earlier capture:
`data/vision/evidence/real-yolox-loopback-replay-2026-11-06.png`, SHA-256
`d32e7c04d4326a8626dd1ed9a1e101ffb8bc8b6041d80554dbcfddb933f268c7`.

## Synthetic candidate review (explicitly not a real incident)

The same E2E test creates a deterministic wrong-way trajectory marked `SYNTHETIC TEST`, passes it
through the production `RuleEngine`/`AlertGate`, signs and posts it to the real ingest endpoint,
persists it to the isolated database, then opens the authenticated alert in Chromium and rejects
it. PostgreSQL assertions verify the rejected status and audit record. This proves the review path;
it does not prove that YOLO found an incident in the recorded footage. The actual YOLO replay emitted
zero incident candidates.

## Limits and blockers

- Input is an attributed CC BY 3.0 recorded San Francisco street clip replayed over local MJPEG. It
  is not a physical camera, an external live source, or a Romanian traffic camera.
- Counts are detector/tracker observations, not ground-truth-validated vehicle counts. Track IDs
  may fragment and are not guaranteed unique vehicles.
- No labeled incident clip was available; real-footage incident generation remains unverified.
- No `/dev/video*` physical camera was available. The NVIDIA PCI GPU was present but driver and
  ONNX CUDA provider were unavailable; the run used CPU inference.
- External Romanian candidates remain disabled. Exact source dispositions and permission findings
  are in [the exact URL audit](EXACT_ROMANIAN_CAMERA_URL_AUDIT.md).

Additional implementation and performance details: [YOLO inference report](YOLO_REAL_INFERENCE_REPORT.md).
