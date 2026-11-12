# RoadSentinel integration handoff

## Workspace and preservation

This is an independent source integration at `~/Documents/roadsentinel-integration`. It has no `.git`, no link back to the original worktrees, no developer database credentials, no model weights, no uploaded media, and no generated runtime data. `SOURCE_SNAPSHOT_MANIFEST.json` records the copied source file hashes, original worktree status/commit identifiers, and omitted operational files without secret contents. The primary `release/ready` checkout and `roadsentinel-github-review` checkout were treated as read-only.

## Integrated areas

- Retained local recorded-video upload, encrypted storage, crop selection, YOLOX-S ONNX/ByteTrack analysis, PTS-aware playback, persisted candidate/flow events, analytics and Romanian UI. Its route remains `/app/analiza-video`. Offline candidate provenance is available at `GET /api/recordings/{recording_id}/analyses/{run_id}/candidates`, with tenant scope and explicit `offline_recording` / `pending_review` semantics. Candidate observations and line crossings do not create live alerts.
- Added camera control APIs, config version/grant/runtime models and UI panel to the existing Cameras page. Existing camera discovery, preview and worker controls remain. Source grants and backend authorization remain mandatory. The local model registry identifier `stock-yolox-s` is used by the editor.
- Added investigation/case notes, revisions, bookmarks, dossier, export, archive helpers, case links/follow-ups/legal holds, evidence integrity APIs, and all corresponding panels within the existing alert detail workflow. Existing decision UI/API paths remain authoritative.
- Added health/reliability routes and bounded metrics while retaining existing local metrics, ops and readiness routes.

## Migration strategy

The local `0001`–`0015` chain remains unchanged. The camera/control and casework schema was ported as an additive chain `0016`–`0019` with unique revision IDs `rsint_cam1`, `rsint_case1`, `rsint_run1`, and `rsint_case2` after local `0015`. Remote duplicate `saved_searches` creation/removal was omitted because local revision `0013` owns that table. The remote migration’s duplicate `evidence.purged_at` add/drop was omitted because local `0010` owns it. Do not apply this chain to existing deployments until reviewed against their recorded Alembic version, schema, role grants, RLS policies and data. No migration was run against any pre-existing database.

For an eventual owner-approved adoption: take a verified backup, clone the target database into an isolated environment, confirm current revision and catalog objects, apply the additive chain only on the clone, inspect RLS/policies/constraints/grants and compare retained local recording/evidence counts, then prepare a rollback plan. Downgrades only remove newly introduced tables/columns; application data backup remains required. Never run on production without a separate reviewed migration plan.

## Known implementation gaps and blockers

- Offline candidates are exposed as a typed, tenant-scoped review contract and remain separate from live enforcement alerts. Promotion into the existing case authority is intentionally not implemented; a human-confirmed recorded-source promotion flow still needs API/UI design and audit verification.
- The imported camera runtime configuration and current local pipeline have different execution contracts. Camera control state/config lifecycle is present, but a full local-worker config-ack path and authorized recorded fixture activation still require an adapter and isolated runtime validation.
- The evidence service has local crypto/storage compatibility adapters for casework, but storage-duration probing and remote S3 behavior have not been validated in this snapshot.
- This copy excludes the YOLOX-S model weights, uploaded recordings and original evidence by design. Actual inference and media workflow cannot be demonstrated here unless a separately authorized sample and model are staged into this isolated workspace.
- No database or browser validation is claimed until isolated dependencies are available and run.

## Validation record

- Python compile check: passed over `backend/app` and `roadsentinel` after final source changes.
- FastAPI import: passed. Alembic reports one head (`rsint_case2`) with local `0015` followed by four integration revisions.
- Empty-schema `alembic upgrade head`: passed on disposable database `rsint_20261110b` at `127.0.0.1:55446`; required offline/control/case tables were present. Forced RLS was enabled on all 15 checked tenant tables (including local SavedSearch and offline tables).
- Frontend `npm ci --offline` and `npm run build`: passed (TypeScript plus Vite production build).
- Separate runtime smoke: backend `/api/health` returned `{"status":"ok"}`, `/api/health/live` returned `{"status":"alive"}`, and `/api/health/ready` returned `{"status":"ready"}` after adding the missing `metrics_token_value` accessor; frontend returned HTTP 200; browser page title was `Autentificare · RoadSentinel`, CSRF endpoint returned 200, and there were no page errors. CORS preflight allowed `http://127.0.0.1:5175`.
- Operator authentication was not attempted: the disposable DB intentionally has zero tenants/users, so the existing operator account is only in the protected original demo DB. Its DB, credentials and running ports were not accessed or changed. Actual YOLOX-S inference, authorized camera worker acknowledgement, case export, and browser login remain unverified because model/media and existing demo records were excluded.

## Run locally after creating isolated credentials

The current isolated runtime is started with `backend/.env.integration.local` (mode 0600; gitignored), a new disposable database, fresh secrets, and `RS_MFA_EXEMPTION_ENABLED=false`. It is available at `http://127.0.0.1:5175/login`, with API on `http://127.0.0.1:8003`; do not enter production data. The database has no users. For the existing operator account `operator.a@roadsentinel.local`, use the original demo UI at `http://127.0.0.1:5174/login`; its generated demo password was not read or copied during this isolated integration. Obtain it from the credential output/file created by the original `seed(..., users_only=True)` run. If that artifact is unavailable, the operator must be reset only through an explicitly authorized operation on the original demo DB. This integration workspace has no working operator password by design.
