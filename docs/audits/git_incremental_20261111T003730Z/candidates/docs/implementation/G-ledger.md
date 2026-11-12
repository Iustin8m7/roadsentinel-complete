# Workstream G: recorded-video analysis (A) and camera administration (B)

Feature B was merged to `main` on 2026-11-10 at the owner's instruction ("merge into main and
deploy"), which replaced the no-push rule of the specification that started this work. Feature A is
not started. The specification was pasted on 2026-11-10 and is cut off at test `B-T01`; a second,
wider specification pasted the same day is cut off inside its Feature 10. Sections after those
points are unknown.

Status words: DONE (evidence named), PARTIAL, MISSING, BLOCKED. Nothing is DONE without a test or a
browser run named next to it.

## Baseline (read from the code on 2026-11-10)

| Topic | What exists | Where |
|---|---|---|
| Detector | Ultralytics YOLO11 + ByteTrack. There is no YOLOX or ONNX path in this repository; the specification's "existing YOLOX-S ONNX path" does not exist, so the existing detector is kept. | `roadsentinel/pipeline.py` |
| Processing location | The API has no model and no ffmpeg. Detection runs on a separate machine that signs requests with a service-account key. | `roadsentinel/sink.py`, `backend/app/api/ingest.py` |
| Events, evidence | Signed ingest of event + key frame + clip, encrypted per tenant, signed media links. | `backend/app/services/evidence.py` |
| Casework | Notes, bookmarks, decision, follow-ups, legal hold, export with second-admin approval, offline package verification. | `backend/app/api/investigation.py`, `casework.py`, `services/exports.py` |
| Camera control plane | Source registration, grants, immutable config versions, server validation (bounds, area, self-intersection, rule requirements), fingerprint, diff, four-eyes approval (database CHECK), activate, rollback, worker lease / ack / heartbeat, derived runtime state. | `backend/app/services/camera_control.py`, `camera_config.py` |
| Camera UI | Status, worker metrics, grants (read only), version list with validate / submit / approve / reject / activate / rollback, diff. A draft is typed as raw JSON. | `frontend/src/components/CameraControlPanel.tsx` |
| Disposable stack | Fresh database, two administrators, API, built UI, API harness and headless browser check. | `scripts/e2e/run_camera_control_e2e.sh` |

## Feature A: recorded video to casework

| Requirement | Current | Status | Work |
|---|---|---|---|
| Browser upload of a recording, validated | nothing | MISSING | upload sessions (chunked, digest, quota), MP4 probe with `services/mp4.py`, encrypted storage |
| Durable analysis job with real progress | nothing | MISSING | job table, state machine in the service layer, lease + fencing, worker API |
| Real inference on the upload | pipeline only reads a local file from a camera YAML | MISSING | analysis worker on the processing machine: claim, download, run, report |
| Annotated playback, counts, heatmap, timeline | nothing | MISSING | result artifacts + summary JSON, results page |
| Candidates, review-only by default | events go straight to the alert queue | MISSING | candidate table, explicit promotion (idempotent), provenance `RECORDED` / `SYNTHETIC TEST` |
| Case notes, decision, approval, export | exists for events | PARTIAL | reuse after promotion; show recorded provenance in case and export |
| Operator pages reachable from navigation | nothing | MISSING | "Analize" section |

## Feature B: camera administration

| Requirement | Status on 2026-11-10 | Evidence |
|---|---|---|
| Add a camera in the UI (starts "in configuration", never enabled) | DONE | G-B3 |
| Register a source in the UI; a wrong scheme is refused and not stored | DONE | G-B3 |
| Record and revoke a permission in the UI; revocation blocks an approved camera | DONE | G-B3 |
| Visual editor: zones, travel direction, calibration quad, far limit; drag, add / remove corner, arrow keys, typed coordinates, undo / redo, a no-mouse path | DONE | G-B1, G-B3 |
| Coordinates stored in reference-frame pixels at any display size | DONE | G-B1 (unit), G-B3 (drawn at 1440 px, dragged at 1100 px) |
| Rule form built from the server's catalogue; a rule that lacks calibration, a zone, a direction or frame rate is disabled with the reason | DONE | G-B1, G-B2, G-B3 |
| Thresholds with units and the server's bounds; problems listed and linked to the shape; saving blocked while any exists | DONE | G-B1, G-B3 |
| Save draft, submit, diff, approve by a different administrator, activate, rollback | DONE (existing backend, now driven from the editor) | G-B3 |
| Requested / applied / in effect shown apart | DONE | G-B1 (`configStage`), G-B3 |
| Worker applies the exact revision | DONE for the config handshake (real `remote_config` client: fetch, fingerprint check, ack, heartbeat). The detector run with a remote config is covered by the existing `camera_detector_e2e.py`, not re-run here. | G-B3 |
| Backdrop is a real frame of the camera | PARTIAL: the editor shows a frame of the camera's uploaded recording or its last alert key frame when one exists; the E2E camera has neither, so the run draws on an empty stage | manual look on the dev stack |
| Dry run of a draft on recorded media | MISSING: depends on Feature A's job engine | |
| Lanes, crosswalks, exclusion masks, counting lines | NOT IN SCOPE OF THE ENGINE: `roadsentinel/rules.py` knows two zone kinds (carriageway, emergency lane); the editor offers exactly what the validator and the worker accept | `camera_config.catalog()` |

Known gaps found on the way, not fixed: `bg-deep-void` is used in 24 places but the theme defines
only `--color-void`, so those backgrounds are transparent (the editor uses `bg-void`). The primary
button style is light grey with white text and reads as disabled.

## Order of work

1. B: done as listed above.
2. A: NOT STARTED. Migration 0011, upload sessions, job table and state machine, analysis worker
   on the processing machine, results, candidates, promotion, operator pages. Nothing of Feature A
   exists in this worktree yet.
3. B dry run on top of the A job engine.

## Test ledger

| Id | What | Command | Result |
|---|---|---|---|
| G-B1 | Editor logic: pointer mapping, geometry checks, rule gating, defaults, undo, revision stage | `cd frontend && npm run test` | PASS, 99 tests (21 new in `lib/cameraConfig.test.ts` and `lib/cameraControl.test.ts`) |
| G-B2 | Catalogue endpoint states what the validator enforces; its defaults are valid; 401 without a session | `pytest tests/test_camera_control.py -k catalogue` | PASS |
| G-B3 | Browser, real API, fresh database, two administrators, worker handshake: draw, edit, gate, submit, self-approval refused, diff, approve, activate, apply, rollback; new camera from the UI; revoke | `PG_PORT=55491 scripts/e2e/run_camera_control_e2e.sh` | PASS (`E2E CAMERA CONTROL: PASS`, `E2E CONFIG EDITOR: PASS`) |
| G-R1 | Regression: whole backend suite | `pytest` in `backend/` with `RS_TEST_ADMIN_DATABASE_URL` on a throwaway PostgreSQL 16 | PASS, 669 |
| G-R2 | Regression: pipeline suite | `pytest tests` | PASS, 143 |
| G-R3 | Frontend typecheck, lint, build | `npm run typecheck && npm run lint && npm run build` | PASS |

Provenance of G-B3: LOCAL REPLAY reference and a permission labelled test-only; no camera or
third-party stream is contacted; no detector inference runs in it (config handshake only).
