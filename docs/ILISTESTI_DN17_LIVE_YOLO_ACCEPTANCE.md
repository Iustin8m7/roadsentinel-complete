# Ilișești DN17 live snapshot / YOLO acceptance

Observed locally on 2026-11-07 (UTC). This is specific to candidate `RO-DN17-WCR-001`; the prior-day timelapse is a separate replay and was not used.

## Result

- **Transport:** WebcamRomania’s target page publishes a periodically refreshed JPEG (`1280×720`, provider `Last-Modified: 2026-11-07 22:01:27 UTC`). This is a snapshot source, not continuous video.
- **Provider cadence:** `scripts/probe_ilisesti_source.py --interval-s 60 --timeout-s 8` decoded one JPEG at 22:08:29 UTC; at the second request the provider returned `304 Not Modified`. The server-reported age was 482 seconds. No second distinct image/version was observed.
- **Actual inference:** `scripts/infer_ilisesti_snapshot_once.py` acquired one provider image at 22:17:54 UTC (image age 987 seconds), then ran the configured YOLOX-S ONNX weights on that image. Model SHA-256: `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`; active provider `CPUExecutionProvider`; capture 0.5698 s; inference 0.1203 s (8.315 inference FPS for this single image); detector output: 2 car detections. This is one-image inference, not a measured continuous source cadence or a claim of ground-truth vehicle count. No image or output frame was saved.
- **GPU:** Project ONNX Runtime 1.23.2 exposes `AzureExecutionProvider` and `CPUExecutionProvider`, not CUDA. The inference correctly disclosed the CPU fallback. NVIDIA hardware visibility was not treated as proof of CUDA inference.
- **Official embed:** Chromium navigated to the provider’s published embed, but it rendered only two Webcam România logo images (`/player/assets/images/logowr.png`), not the Ilișești snapshot. The app therefore exposes the official camera page link and does not present that embed as a camera player. Browser verification command below passed this fallback behavior; it did not verify external live imagery in the app.
- **Authorization:** A private ignored local attestation exists at `cameras/.local/ilisesti-dn17-attestation.json` (mode `0600`). It records only the owner’s offline written-approval attestation and the narrow local transient processing scope; it contains no approval document. It is not versioned or independently verified.
- **Storage:** Single-image probe/inference did not retain frames. Recording, export and redistribution remain disabled in the Ilișești profile. Replay is disabled and no timelapse/video file was used.

## Acceptance assertions

| Assertion | Result |
|---|---|
| A01 exact source/ID and profile, no second profile | Implemented; backend/database uniqueness not exercised |
| A02 snapshot distinguished from timelapse | Verified from the target provider page and separate timelapse URL |
| A03 bounded source retrieval/decode | Passed: provider HTTP 200, JPEG decoded `1280×720` |
| A04 two distinct fresh images | Not verified: 60-second conditional recheck returned 304 |
| A05 YOLOX on authentic Ilișești input | Passed once: CPU ONNX inference on the published snapshot; 2 car detections |
| A06 signed preview/heartbeat persisted to PostgreSQL | Not verified: no PostgreSQL service reachable in this environment |
| A07 React with real API and annotated changing frames | Partial: authenticated-route browser fixture passed; it used stubbed API, and provider embed contains no camera image |
| A08–A10 actual worker Start/Stop/Restart via browser/API | Not verified: requires reachable PostgreSQL and real API session |
| A11 stale/unchanged snapshot not reused as a new frame | Covered by source adapter behavior and passing unit tests; provider returned 304 |
| A12 relevant regressions | Targeted tests pass below; database-backed tests could not initialize |
| A13 no remote Git operations | Confirmed; none performed |
| A14 private approval/credentials not logged or committed | Confirmed; local attestation ignored, mode 0600; no credentials used |
| A15 no replay or synthetic image represented as live | Confirmed |

## Commands and results

- `timeout 30s ./.venv/bin/python scripts/infer_ilisesti_snapshot_once.py` — exit 0; one authentic image processed; stdout reported measured model/source data and aggregate detections only.
- `PYTHONPATH=. timeout 90s ./.venv/bin/python scripts/probe_ilisesti_source.py --interval-s 60 --timeout-s 8` — exit 0; one decode plus conditional 304; no distinct update.
- Focused source/detector/worker tests with local socket fixture excluded — **73 passed, 1 deselected**. The excluded local HLS fixture was run separately with network permission — **1 passed**. These fixture tests are not Ilișești video evidence.
- `PYTHONPATH=backend ./.venv/bin/python -m pytest backend/tests/test_live_preview.py -q` — **4 setup errors** because PostgreSQL at `127.0.0.1:5432` was unavailable. No test database was dropped or modified.
- `PLAYWRIGHT_BROWSERS_PATH=/home/justin7m8/.cache/ms-playwright PATH=/home/justin7m8/miniconda3/envs/rs-node22/bin:$PATH timeout 180s npm run test:e2e -- --cameras-only --ilisesti-player` — **0 failures** for the authenticated-route fixture, source attribution, external fallback, and exclusion of the branding-only embed. The API in this E2E path is stubbed; no screenshot or camera image was saved.
- Frontend `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build` — exit 0; **15 Vitest tests passed**.
- Ruff, Python byte-compilation, `node --check frontend/e2e/walk.mjs`, `git diff --check` — exit 0.

## Remaining external/runtime requirements

1. The provider must publish at least two changed, sufficiently recent snapshots (or a documented continuous transport) before this can be called a reliably live feed or support meaningful ByteTrack motion tracking.
2. A reachable disposable PostgreSQL and configured authenticated local API are required to verify provisioning, signed preview persistence, React API frames, and real worker Start/Stop/Restart. The local service state available to this run had no PostgreSQL or Uvicorn process.

Until those gates pass, status is **snapshot source + one real YOLO inference; no verified continuous live telemetry path**.
