# Romania incident map — implementation and verification (2026-11-11)

Verdict: PARTIAL. This session added the authenticated map and recording location UI to an existing geolocation backend, but did not verify the full upload-to-marker journey in an integrated Chromium/PostgreSQL environment. The map currently provides aggregate circle markers and an accessible incident list; cluster expansion, individual marker selection on the map, role-tested correction UI, and all B1–B7 browser scenarios remain outstanding.

## Existing architecture found

`/api/recordings` → offline analysis/ByteTrack → candidate → existing promotion → `Alert` + `IncidentGeoSource` → `LocationRevision` resolution → `/api/map/incidents/query` → React map/list. The pre-existing `0023_incident_geolocation.py` migration introduces location revisions with tenant RLS. `geo_reference.py` supplies Natural Earth boundary data. No database migration was added in this session and no integration database was modified. The existing geolocation service treats location from pixels as unknown, version-gates updates, and requires a separate administrator for incident location corrections.

## Changes in this session

- Authenticated `/app/harta-incidentelor` route, permission-aware navigation, Romania boundary and OpenStreetMap tiles, aggregate map markers, filtered list, counters, incident links, unavailable-tile notice, and periodic refresh.
- Recording location card with approved-camera choice, manually selected map point or numeric coordinates, and unknown location choice. It sends revision-gated changes to the pre-existing API. Camera selection explicitly attests its validity at filming time when capture time is unknown.
- Narrow CSP image allowance for the three OpenStreetMap tile hosts. Scripts and other outbound connection sources remain unchanged.

## Provenance and limitations

Video detection does not establish GPS. Camera anchor coordinates describe the camera, not the exact road event. Operator-declared capture time is distinct from upload and detection time. An unknown or moving/composite location should produce no operational marker. Synthetic and replay footage cannot establish real-world model accuracy. External camera rights were not established here.

The current UI does not yet provide a fully reviewed incident-level correction/approval flow or detailed selected marker popups. It renders aggregate cluster centers; the side list preserves distinct incident IDs. It does not provide a complete camera editor for geolocation or verify historical camera movement in a browser. The manually selected pin is clickable but not draggable. The map API, migration, and source linkage were found in the workspace before this session; their operational correctness is not established by the frontend build.

## Fresh commands and results

- `cd frontend && npm run build` — PASS after UI edits, TypeScript and Vite build.
- `cd frontend && npm run lint` — PASS after one lint correction.
- `cd frontend && npm test -- --run` — 12 files, 112 tests PASS.
- `PYTHONPATH=backend:. .venv.integration/bin/python -m pytest tests/test_offline_heatmap.py tests/test_pipeline_event_identity.py -q` — 7 PASS.
- An initial pytest invocation without `PYTHONPATH` failed import collection; rerun above passed.
- `backend/tests/test_security_headers.py` was requested but does not exist; no test ran.
- Fresh integrated PostgreSQL migration, API, YOLOX execution and Chromium B1–B7 scenarios: NOT EXECUTED in this session. Existing screenshots in this workspace are historical baseline evidence and are not claimed as proof of this map UI.

## Safe next verification

Use the repository's isolated PostgreSQL and browser harness; do not point it at an operational database. Verify migration `0023` on throwaway data, then run the backend contract/security suites and a genuine browser login/MFA/upload/location/promotion/map sequence. The UI is built in `frontend/dist`. Do not publish until all B1–B7 and tenant isolation checks are green.

No GitHub push was performed. No original source repository, media, model weights, or database was modified by this session.
- `PYTHONPATH=backend:. .venv.integration/bin/python -m pytest backend/tests/test_headers_push.py -q` — BLOCKED at fixture setup: local PostgreSQL on the default test port was unavailable; 14 tests errored before execution. This command was not rerun against an alternate database, to avoid touching an unidentified database.
- `PYTHONPATH=backend .venv.integration/bin/python - <<'PY' ...` — 5 direct schema assertions passed for known point, 0/0, out-of-range, NaN, and reversed bbox. This is schema-only evidence, not database or API evidence.

No new UI screenshots, HAR, browser console count, browser version, source/job/incident IDs, or migration revision from a fresh run are available. B1–B7 are NOT EXECUTED. The historical baseline cited above is from before this UI work and does not establish current regression status.

## Continuation (2026-11-11)

Added direct protected incident detail and append-only location history API routes, plus a camera position history route. The map now renders individual incident markers, a selected-incident panel, correction proposal form, pending approval controls, draggable pins, history, and server-bound date/type/county/camera/viewport filters. This code is built but not validated against a live database. The browser and end-to-end acceptance remain unverified.

The supported `python scripts/verify-integration.py auth` disposable database harness failed before starting PostgreSQL: `socket.socket()` raised `PermissionError: Operation not permitted` in this sandbox. This is process-level network/socket isolation, not a missing database password or a PostgreSQL test failure. No test database was touched. `python scripts/verify-integration.py frontend` completed test, lint, and build successfully; its fresh evidence is under `docs/audits/runtime_verification/runs/20261111T180215Z-ea3efaf7/`. A later local `npm run build && npm run lint && npm test -- --run` also passed (12 files, 112 tests). No Chromium was run because serving the integrated app requires the same blocked socket capability.

The full source-rights declaration workflow for offline uploads, end-to-end candidate promotion browser proof, and service restart/cross-tenant database proof are still unimplemented or unverified. Do not use this handoff as a release approval.
