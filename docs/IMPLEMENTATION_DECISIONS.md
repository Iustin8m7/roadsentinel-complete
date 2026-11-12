# Implementation decisions

Local implementation log for the enterprise work. This file records choices made from repository
evidence; it does not imply external legal, camera-owner, or infrastructure approval.

| Date | Decision | Rationale / consequence |
|---|---|---|
| 2026-11-06 | Keep work on the current `release/ready` branch because `.git` is read-only. | The repository began clean at `f225bfd`. A safe local branch could not be created; do not attempt to alter refs or commits through another path. |
| 2026-11-06 | Preserve FastAPI/PostgreSQL/SQLAlchemy/Alembic, React/TypeScript, YOLO/OpenCV, RLS, encrypted evidence, and HMAC ingestion. | This is the established architecture and no evidence currently justifies a rewrite or service split. |
| 2026-11-06 | Treat `backend/` as the authoritative system of record; `secure-pwa/` is the bundled secure client; `frontend/` is the separate operator client; `web/` and `roadsentinel/server.py` are legacy demo only. | Matches the Compose topology and handoff. API contract consolidation must preserve compatibility until verified clients migrate. |
| 2026-11-06 | No remote camera source is enabled by implementation defaults. | A public viewing page does not grant automated processing/recording rights. Remote sources require documented written permission and source checks. |
| 2026-11-06 | Local video and synthetic sources are the repeatable integration path. | They permit deterministic testing without unauthorized third-party footage. |
| 2026-11-06 | Do not run backend tests until their hard-coded `rs_test` database target is proven disposable. | `backend/tests/conftest.py` drops and recreates that database. Avoid destroying a developer database. |
| 2026-11-06 | Do not start Compose until Docker socket access is available and existing local volumes/containers are inspected. | `docker info` currently fails with permission denied; a stack startup could touch persistent local state. |
| 2026-11-06 | Keep network sources disabled unless camera-specific written authorization is complete. | `roadsentinel.sources.SourceSpec` requires consent metadata and explicit enablement; candidate ranking cannot override missing permission. No external URL is probed by the connector tests. |
| 2026-11-06 | Add a local signed audit checkpoint adapter, but do not treat it as a production independent anchor. | Ed25519 signatures and monotonic sequence checks provide reproducible local verification; same-host key and JSONL storage can be rewritten together. External custody and immutable storage remain a production prerequisite. |
| 2026-11-06 | Bound per-session analytics track state and status payload size. | Long-running camera workers must not grow their tracked-ID cache without limit, and the secure heartbeat accepts bounded per-line summaries. |
| 2026-11-06 | Treat capture open/read exceptions as reconnectable source failures. | RTSP/HLS/HTTP still feeds can fail differently from local clips; `LiveReader` now applies bounded backoff and counts failures without exposing endpoint strings. |
| 2026-11-06 | Saved archive searches belong to the authenticated user and store parsed filters, not raw query text. | Queries can contain personal data; search interpretation remains local, records are tenant-RLS scoped and owner-filtered, and use is audit logged. |
| 2026-11-06 | Demo alert curation requires both mock mode and explicit opt-in. | Hard-coded fixture IDs and manual labels must never hide or rewrite authoritative backend records, even if a deployment build accidentally includes the curation flag. |
| 2026-11-06 | Archive search uses signed keyset cursors bound to tenant and normalized filters. | Stable paging avoids loading the 200-row cap as a single page; cursor contents omit raw query text, expire after one hour, and reject cross-tenant/filter reuse. |
| 2026-11-06 | Aggregate dashboard statistics in SQL under the existing RLS and object scopes. | Avoid loading full alert ORM rows (including ciphertext and details) into API memory just to count categories; keep the existing response contract. |
| 2026-11-06 | Limit the new camera administration screen to audited registry metadata edits. | Backend `cameras:manage` remains authoritative; name, location, coordinates, and timezone use the existing audited camera PATCH. Source URLs, enablement, detection rules/zones, and approval history require separate configuration/versioning work and are not exposed by this editor. |
| 2026-11-06 | Resolve the root test helper import locally instead of making root `tests/` a Python package. | `backend/tests/` is already a package named `tests`; adding another package marker caused pytest collection collisions. The rates tests now import the root helper module directly, and combined collection succeeds without changing backend package structure. |
| 2026-11-06 | Keep both root test helper imports local to pytest's root test path. | `test_rules_rates.py` and `test_calibration.py` previously imported `tests.*`, which collided with the backend's package. Direct local module imports allow both packages' tests to be collected together; root regression run excluding the legacy API suite passed 132 tests with 2 skips. |
| 2026-11-06 | Do not install detector packages or fetch model weights during this resume. | PyTorch, Ultralytics, Supervision, and local weights are absent, network access is restricted, and weights/licensing plus representative evaluation data are not approved. Continue with local/synthetic validation and keep real inference explicitly unverified. |
| 2026-11-06 | Make Ultralytics an import-time optional dependency for non-inference pipeline utilities, but fail fast when `run()` is invoked without it. | This keeps source/config helpers and detector-independent checks usable while preserving the hard requirement for real YOLO at processing time. The new guard is tested before camera config/source access; no inference fallback or fabricated detections are introduced. |

New decisions should include the affected components, validation, and any consequences for tenant
security, data retention, or compatibility.

