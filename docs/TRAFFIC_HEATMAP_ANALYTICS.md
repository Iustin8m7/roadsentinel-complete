# Recorded video traffic analytics

## Architecture decision

Analytics are derived inside the existing offline-analysis worker from the actual
YOLOX-S ONNX detections and the existing ByteTrack update. Each processed sample,
including a successfully processed frame with no vehicle detections, is written to
a versioned JSONL observation artifact. The artifact is finalized only after the
sampled-timeline video and analysis run complete, SHA-256 checked, and encrypted
with the existing tenant media key. PostgreSQL stores the tenant/run-bound artifact
key, digest, byte size, schema version, observation count, and completion state on
the existing `analysis_runs` row. This avoids duplicating per-frame boxes in JSONB
or adding a second observation table. Artifacts are bounded to 128 MiB and are
available only through authenticated, tenant-scoped API routes.

Each row stores its media PTS, source frame index, monotonic sample sequence and
vehicle observations. Person detections are excluded. A track ID is nullable and
attached only when a ByteTrack box nearly matches the detector box. A track ID is
an observed tracker identity, not a validated unique vehicle.

## Coordinates and time

Persisted bounding boxes and bottom-center anchors use normalized coordinates on
the original, full recording canvas. The worker adds the integer crop origin to
ROI detector pixels exactly once, clips to source dimensions, and normalizes by
source width/height. The UI displays the authenticated redacted representative
frame at its original aspect ratio, then stretches the row-major heatmap matrix
over that same full-frame canvas and draws the run crop boundary. CSS resizing
does not change normalized source locations.

Time values are recording-relative PTS seconds, not wall clock. Timeline buckets
are half-open `[start,end)` intervals (with the recording's exact final endpoint
included in the last interval). Processing cadence is not the source video's
nominal frame rate. Existing offline output remains a sampled-timeline video and
does not preserve audio.

## Metrics

* **Observation density:** one unit per included YOLOX vehicle observation.
  Anchors are deposited into an aspect-adapted grid, Gaussian-blurred with sigma
  `max(0.65 grid cells, radius × grid width)`, masked to the run crop and
  renormalized to preserve the included observation total. The default radius is
  3% of source width. Color intensity is normalized to the maximum in the current
  filter selection (`per_filter_max`); the UI discloses that filtered selections
  rescale independently. Zero cells are transparent.
* **Estimated visual presence seconds:** each sample receives the positive PTS
  interval to the next sample only when that interval is at most 2.5 seconds;
  duplicate, non-monotone or larger gaps receive zero. The final sample receives
  at most `1 / requested_sample_fps`, capped at 2.5 seconds. The weight is also
  clipped at the selected interval end. This is a sampled visual-presence
  estimate, not physical road occupancy or exact dwell time.
* **Timeline:** bins report detector observations and estimated presence seconds
  by vehicle class, plus processed-frame coverage. Empty processed bins are
  distinct from bins with no processed samples.

Neither metric establishes unique-vehicle counts, throughput, speed, congestion,
law violations, or incident truth. A configured line crossing is separately
reported by the existing offline pipeline and remains unvalidated geometry.

## Privacy, access and lifecycle

The observation artifact inherits the private tenant-encrypted offline media
storage. The current offline-analysis feature has no recording/run purge workflow;
therefore artifact cleanup on retention or deletion remains a lifecycle gap shared
with source/output media and must be implemented before operating under a finite
retention policy. Analytics API access uses the existing
`videos:read` permission and tenant-scoped video/run lookup; cross-tenant IDs
return not found. Responses are not cached publicly. The representative frame is
decoded from the encrypted recording on request, redacted using configured
redaction mode, and returned as a private no-store JPEG. Analytics require a
completed run with a finalized artifact. Older runs, cancelled jobs and failed
jobs report analytics unavailable and must be reanalyzed; incomplete artifacts
are not treated as zero-valued full results. Aggregate export is not implemented.

## Verification status — 2026-11-08

Real production worker/API and authenticated browser acceptance was run against
both complete user-owned recordings. The application imported original bytes
through its authenticated upload endpoint, confirmed full-frame crop, queued
the actual YOLOX-S + ByteTrack worker, finalized encrypted observation
artifacts, persisted run metadata in PostgreSQL, and served scoped analytics
endpoints. The tests removed only their own encrypted media/artifact objects
and disposable DB rows after the browser session; they did not alter originals.

* Source A: 514.058 s; 522 sampled frames; 6,448 observations (5,982 car,
  150 motorcycle, 182 truck, 95 bus, 39 bicycle); estimated tracker IDs car
  190, truck 25, bus 12, motorcycle 3; density weight 6,448; 6,474 nonzero
  cells. Final full-run browser ID: `8cff88dc-6b3c-4fdd-b689-1fd2508128ae`;
  measured processing 8.59 frames/s, worker duration 61.45 s on the final
  measurement run.
* Source B: 362.727 s; 369 sampled frames; 8,191 observations (7,733 car,
  253 truck, 76 bus, 108 motorcycle, 21 bicycle); estimated tracker IDs car
  235, truck 26, bus 9, motorcycle 1; density weight 8,191; 8,575 nonzero
  cells. Final full-run browser ID: `6585eaa5-f6ec-45ec-8b48-ff4f8979ea05`;
  measured processing 8.40 frames/s, worker duration 44.53 s on the final
  measurement run.
* Both used the user-configured 1 sample/s output profile. Counts are detector
  observations from that sampling, not validated unique vehicles. Tracker IDs
  are approximate; this does not validate traffic counts or scene accuracy.
  The annotated output remains a sampled-timeline video without audio.

Against a fresh disposable UTF-8 PostgreSQL cluster on loopback port 55442,
migrations 0001–0015 applied. The API test checked upload, persisted completed
run, artifact-backed summary/grid/timeline, image frame, HTTP Range 206 for
output video, unauthenticated 401 and cross-tenant 404. Authenticated Chromium
used local FastAPI and Vite (mocks off), logged in using the test operator's
password and TOTP, and displayed a real redacted 1050×589 frame under a nonempty
heatmaps. On the final full Source A browser run it observed 6,448 initial
observations, 5,982 for car-only, 66 in source PTS 0–5 s, a nonempty 6,474-cell
grid, restored analytics after reload, unauthenticated 401 and no console
errors. Source B showed 8,191 initial observations, 7,733 for car-only, 120 in
source PTS 0–5 s, a nonempty 8,575-cell grid, restored analytics after reload,
401 unauthenticated and no console errors. On the A browser check, changing
opacity changed canvas alpha sum from 0 to 283,960; mobile canvas width was
732 px. Browser assertions confirmed representative frame natural width 1050.

Local screenshots (sensitive scene imagery; keep local):

* Source A: `/tmp/roadsentinel-offline-analytics-db3ed7cb92e74f968a61e47a20a8e00b/analytics-all.png`, `analytics-car.png`, `analytics-mobile.png`.
* Source B: `/tmp/roadsentinel-offline-analytics-46216bdca5c24fc3819b3ac79bdb8567/analytics-all.png`, `analytics-car.png`, `analytics-mobile.png`.
* A complete full-recording summary JSON is stored beside the Source A screenshots at `/tmp/roadsentinel-offline-analytics-db3ed7cb92e74f968a61e47a20a8e00b/acceptance.json`.

The full-duration model/API and authenticated browser flow is verified for both
recordings. The E2E verified HTTP Range 206 for the output video but did not
assert successful HTML5 decode/seek of the finished output. Long-run recovery
after an actual API process crash, full output playback, all-tenant/media
negative permutations, rule line crossings, and external ground-truth accuracy
remain unverified.

Focused verification:

```bash
PYTHONPATH=.:backend ./.venv/bin/python -m pytest \
  tests/test_offline_heatmap.py tests/test_offline_analytics_artifact.py -v
# 8 passed
cd backend
PYTHONPATH=/home/justin7m8/Documents/roadsentinel \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55442/postgres \
RS_OFFLINE_ANALYTICS_REAL_VIDEO=/tmp/rs-heatmap-inputs/source-a-segment.webm \
RS_OFFLINE_ANALYTICS_BROWSER=1 timeout 300s ../.venv/bin/python -m pytest \
  tests/test_offline_analytics_real_video.py -q -s
# 1 passed; full source A, real API, YOLOX/ByteTrack and authenticated Chromium
```

The same test command was also executed with the exact source B path and
`RS_OFFLINE_ANALYTICS_BROWSER=1`; it passed full video, API and Chromium checks.
Each test fixture drops and recreates `rs_test`; never point it at a developer
database.

Repeat source B by replacing `RS_OFFLINE_ANALYTICS_REAL_VIDEO` with:

```text
/home/justin7m8/Videos/RoadSentinel/Screencast from 2026-11-08 00-20-53.webm
```

The operator flow is available at `/app/analiza-video`: import the WebM, inspect
and confirm the crop, select the 1 sample/s CPU profile, start the recorded
analysis, then choose its **Heatmap și analitice** tab. The run history is
loaded from the authenticated API after page refresh. Do not run the test
fixture against any non-disposable database because it drops `rs_test`.

Frontend checks passed: `npm run typecheck`, `npm run lint`,
`npm run test -- --run` (2 files, 15 tests), and `npm run build` (2,873
modules). Ruff on touched Python modules and `git diff --check` passed. The
repository-wide suite and full-length video jobs were not run.

On 2026-11-08, `scripts/offline_heatmap_sample.py` was run against both exact
owner-provided inputs using the installed CPUExecutionProvider and the model hash
above. The bounded three-PTS spot checks decoded frames at approximately 1s,
midpoint and five seconds before the end. Source A yielded 44 genuine YOLOX
vehicle observations and a nonempty 128-grid in-memory heatmap (total observation
weight 44; 4,718 nonzero cells). Source B yielded 64 observations and a nonempty
heatmap (weight 64; 6,996 nonzero cells). These are three full-frame samples,
not complete-run totals. They are separate from the later 20-second
production-path runs above. The original hashes were rechecked afterward and
still match: A `9e169a0a4eb8dffd785e556b013081f2041f1eb8e02f0e59ad8bc60a844a5ca0`,
B `145210060d405a01347a6f3070c7a9186b244ff753fd7d7d69fa2c3b7fb24a05`.

Reproduce the bounded check with:

```bash
cd /home/justin7m8/Documents/roadsentinel
PYTHONPATH=.:backend ./.venv/bin/python scripts/offline_heatmap_sample.py \
  "/home/justin7m8/Videos/RoadSentinel/Screencast from 2026-11-08 00-05-47.webm"
PYTHONPATH=.:backend ./.venv/bin/python scripts/offline_heatmap_sample.py \
  "/home/justin7m8/Videos/RoadSentinel/Screencast from 2026-11-08 00-20-53.webm"
```
