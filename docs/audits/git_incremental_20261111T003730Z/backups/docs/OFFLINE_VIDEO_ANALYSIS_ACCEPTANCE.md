# Offline video analysis — implementation evidence

Updated 2026-11-08 (local checkout; local-only work).

## Current result

The authenticated React route and tenant-scoped backend implementation are present. The UI supports
WebM/MP4 upload, real decoded thumbnail, user-confirmed normalized crop, optional per-run counting
line, queued analysis/cancel/progress, transient preview, run history, and authenticated MP4
playback/export. The backend streams uploads to a private temp file, validates media with ffprobe,
encrypts source and output with the existing tenant file-encryption format, persists recordings and
analysis runs in PostgreSQL, and uses a bounded single-thread analysis queue. Processing uses the
installed YOLOX-S ONNX model, ByteTrack, vehicle-class filtering, detector-based redaction, and
FFmpeg H.264 output explicitly labeled `RECORDED ANALYSIS`.

**This feature is not end-to-end verified yet.** No PostgreSQL listener or PostgreSQL server tools
were available in this execution environment. `docker info` also returned permission denied, even
when retried outside the filesystem sandbox. Therefore the migration, authenticated API workflow,
persisted jobs, worker progress/cancellation, media Range playback, and authenticated browser flow
have not been run here. The backend authorization integration test is collected but not executed.
No mock browser result is being counted as acceptance evidence.

## Actual input and detector evidence

Command executed successfully (exit 0):

```sh
PYTHONPATH=. timeout 35s ./.venv/bin/python scripts/offline_video_preflight.py
```

The script opens both user recordings locally, probes container metadata, decodes five real frames
spread across each file, runs the actual YOLOX-S ONNX model on those pixels, and writes local
annotated JPEGs/contact sheets plus `data/offline-analysis/preflight/preflight.json`. The script
does not alter either source file. These are sparse detector samples, not complete analysis runs;
their observation totals are not unique-vehicle counts, and no ByteTrack/crossing result is claimed.

Model: `models/yolox_s.onnx`, SHA-256
`c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`; provider: CPU
(`CUDAExecutionProvider` is not installed in the current ONNX Runtime).

| Recording | SHA-256 | Container metadata | Sample PTS (s) | YOLO vehicle observations | Median sample inference |
|---|---|---|---|---:|---:|
| `Screencast from 2026-11-08 00-05-47.webm` | `9e169a0a4eb8dffd785e556b013081f2041f1eb8e02f0e59ad8bc60a844a5ca0` | VP8, 1050×589, 514.058442 s, 353/12 nominal container fps | 0.983, 128.058, 255.988, 383.936, 507.127 | 78 | 11.844 inferences/s (five sparse calls) |
| `Screencast from 2026-11-08 00-20-53.webm` | `145210060d405a01347a6f3070c7a9186b244ff753fd7d7d69fa2c3b7fb24a05` | VP8, 1050×589, 362.727116 s, 179/6 nominal container fps | 1.007, 91.559, 183.086, 274.715, 361.199 | 116 | 12.681 inferences/s (five sparse calls) |

The hashes, decoded PTS and per-sample class observations are recorded in the ignored local
`data/offline-analysis/preflight/preflight.json`. One-second sampled full-frame hashes differed in
30/30 adjacent comparisons for each recording; that only proves the screen recording changed. It
does not measure the traffic camera's optical refresh cadence. The browser capture frame includes
potential player/UI overlays. The product defaults to an unconfirmed full-frame crop and requires
the operator to draw/confirm the traffic-only ROI before analysis.

The sample contact sheets are under ignored `data/offline-analysis/preflight/`. They are local
preflight artifacts, not screenshots of the RoadSentinel operator UI and not output videos.

## Code and focused verification

- `backend/app/models/offline_video.py`, `backend/alembic/versions/0014_offline_analysis.py`:
  tenant-scoped durable recording/run records and RLS migration.
- `backend/app/services/offline_video_storage.py`: private per-tenant encrypted media storage and
  authenticated chunk-range decryption.
- `backend/app/services/offline_analysis.py`: bounded local queue, YOLOX-S/ByteTrack processing,
  progress, cancellation, redacted previews and sampled-timeline H.264 output.
- `backend/app/api/offline_video.py`, `backend/app/schemas/offline_video.py`,
  `backend/app/core/policy.py`, `backend/app/core/audit.py`, `backend/app/main.py`: authenticated
  endpoints, DTO validation, permission checks, audit, router and shutdown integration.
- `frontend/src/pages/VideoAnalysisPage.tsx`, `frontend/src/App.tsx`,
  `frontend/src/layouts/AppLayout.tsx`, `frontend/src/lib/api.ts`,
  `frontend/src/lib/permissions.ts`: the operator workflow and authenticated upload client.
- `tests/test_offline_video_core.py`: crop/request bounds, encrypted range/tamper behavior,
  line-segment crossing, safe filename and actual ffprobe media validation fixture.
- `backend/tests/test_offline_video_authz.py`: MFA client authorization and cross-tenant hiding
  assertions; collected, not run because its session fixture drops/recreates `rs_test` and no
  isolated PostgreSQL instance was available.

Executed checks (all listed commands exited 0):

```text
PYTHONPATH=backend ./.venv/bin/python -m pytest tests/test_offline_video_core.py tests/test_detector.py -q
  15 passed; 1 existing Supervision ByteTrack deprecation warning.
./.venv/bin/ruff check backend/app/api/offline_video.py backend/app/models/offline_video.py backend/app/schemas/offline_video.py backend/app/services/offline_analysis.py backend/app/services/offline_video_storage.py backend/alembic/versions/0014_offline_analysis.py backend/tests/test_offline_video_authz.py scripts/offline_video_preflight.py tests/test_offline_video_core.py
  All checks passed.
PYTHONPATH=backend ./.venv/bin/python -m compileall -q backend/app/api/offline_video.py backend/app/models/offline_video.py backend/app/schemas/offline_video.py backend/app/services/offline_analysis.py backend/app/services/offline_video_storage.py backend/alembic/versions/0014_offline_analysis.py
  Passed.
cd frontend && npm run typecheck
  Passed.
cd frontend && npm run lint
  Passed.
cd frontend && npm test
  2 test files, 15 tests passed.
cd frontend && npm run build
  Passed; production assets emitted, including VideoAnalysisPage chunk.
cd backend && PYTHONPATH=. ../.venv/bin/python -m pytest tests/test_offline_video_authz.py --collect-only -q
  1 authorization test collected; not executed.
git diff --check
  Passed.
```

## Acceptance matrix

| Requirement | State | Evidence / remaining action |
|---|---|---|
| Both exact inputs remain unchanged and are accepted by local decoder | **Verified for read/decode** | ffprobe metadata, SHA-256 and five YOLOX samples per file above. Browser upload endpoint itself is not yet exercised. |
| Real YOLOX-S inference on pixels from each input | **Verified for sparse samples** | 78 and 116 actual model observations. This is not a full analysis or tracking result. |
| Confirmed traffic-only crop | **Implemented, unverified in browser** | UI starts at full frame and requires an explicit saved confirmation. |
| Durable tenant-scoped recordings and runs | **Implemented, DB unverified** | Migration and ORM present; no local PostgreSQL available. |
| Actual ByteTrack on both screen recordings | **Unverified** | Detector adapter tests pass, but no recorded-file track sequence has been executed. |
| Progressive annotated previews and cancellation | **Implemented, unverified** | Requires a live API process and database. |
| Complete playable authenticated annotated output | **Implemented, unverified** | H.264/Range path has not yet been run or browser-tested. No output artifact exists. |
| Authenticated operator browser workflow | **Unverified** | No Chromium session against the real API/DB; no UI screenshot claimed. |
| Database-backed auth, RLS and cross-tenant behavior | **Test authored, unverified** | Run the collected backend test only with a disposable PostgreSQL admin URL; its fixture recreates `rs_test`. |
| Remote Git/network publication | **Not performed** | No remote Git commands, deployment, or media upload were used. |

## Next local verification

Bring up a **disposable PostgreSQL instance** reachable to the backend and tests, configure the
project's normal local secrets and database URLs, apply migrations, then run the authorization test
against that disposable database. Do not point `RS_TEST_ADMIN_DATABASE_URL` at a valuable database:
the existing backend test fixture drops and recreates database `rs_test`. After that, start the
supported FastAPI and React services, import both original WebM files in the page, set and save an
operator-reviewed crop for each, and run both full analyses. Verify the DB rows, actual fresh preview
sequences, cancellation/restart behavior, ffprobe output metadata, authenticated HTTP Range response,
and Chromium playback before promoting any of these unverified rows to passed.
