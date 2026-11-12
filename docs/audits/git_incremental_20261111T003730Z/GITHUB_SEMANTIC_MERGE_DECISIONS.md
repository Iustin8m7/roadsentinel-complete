# Semantic merge decisions — pinned 47e3e85

This is an incremental behavior merge into the existing integration, not a replacement checkout. [The coverage CSV](GITHUB_COMMIT_AND_FILE_COVERAGE.csv) assigns a decision to all 60 final-delta files and all 33 reachable commits. [The parent/file inventory](commit-file-inventory.json) records nested merge effects; individual textual diffs are under `commit_diffs/`. The binary final delta and exact target assets are retained separately. Intermediate curation IDs and duplicated merge content were not applied twice.

## Camera configuration and onboarding (#43)

The source editor now uses the integrated authenticated `/api/camera-control/catalog`, source/grant APIs and immutable JSONB configuration versions. Existing draft/validate/submit/distinct-approve/activate/rollback and fenced worker ACK remain authoritative. No new configuration table, schema branch or migration was introduced. Source `yolo11s.pt` defaults were adapted to the existing verified `stock-yolox-s` ONNX registry; no Ultralytics dependency/fallback was introduced.

`CameraControlPanel` retains the advanced JSON workflow and adds the source visual editor and source-rights forms. The existing integration create dialog is retained and now explicitly requests managed onboarding: disabled until rights/configuration/reviewer/runtime gates pass. The legacy API create default is unchanged for compatibility. Independent Romanian source discovery/provisioning and worker telemetry were preserved.

The editor supports polygon drawing/moving/numeric points/direction, calibration, thresholds, capability-gated rules, undo/redo and keyboard point movement. Integrated counting lines are retained and editable with the same reference-pixel coordinates. An incompatible backdrop aspect ratio blocks saving; unavailable frames use a neutral disclosure. Background media is authenticated or a documented recording. This does not certify calibration or source rights.

A real Chromium failure exposed fixed-position dialogs captured inside a transformed, clipped camera card. The control panel now portals to `document.body`; the nested editor uses the modal focus stack. The previous layout failure screenshot is retained rather than discarded. A second actual runtime failure exposed `min_y: null` from the editor reaching a numeric worker comparison: `load_camera` now normalizes a local copy to zero without mutating the approved revision. Both changes have direct regressions.

## Camera recordings and history (#42)

Tiles now expose an authorized recording action, explicit recording/live distinction, an actual player with close/error/retry and an honest placeholder. The integrated media mechanism remains signed, user-bound, tenant-scoped, audited and encrypted. Generic public file paths were not introduced.

Authenticated single-byte Range support was added to the canonical `/api/media/{id}` route, after the existing authentication/signature/RLS/visibility checks. Actual variant size is verified by streaming authenticated decryption; the requested slice is then streamed without a plaintext temporary file or unbounded plaintext buffer. Multiple/invalid/unsatisfiable ranges return 416. This performs two decryption passes for a ranged request: correct but not an optimized indexed encrypted-video store.

Inspection also found managed whole-camera video ingestion lacked the revision/lease and recording-scope gates already applied to incidents. Managed video PUT now requires a current worker epoch/revision and an active `events_and_recordings` grant; `RemoteSink` signs and supplies those query fields. Revocation denies previously issued recording URLs and hides the listing URL. Incident evidence remains subject to its separate case/retention policy.

The source camera-history improvement was adapted to the integration's existing private text search/saved searches. Tile `Istoric` uses an exact camera slug, and `/api/archive/search` enforces the camera filter server-side with cursor pagination. Camera display names remain labels, not an approximate free-text ownership filter.

## Detector boxes and rendering (#40)

The source uses a different detector/tracker interface. The installed Supervision 0.30.7 `ByteTrack.update_with_detections` returns the input detection rows selected by its association, attaching IDs; it does not replace their geometry with Kalman predictions. The integration already renders fresh detector coordinates. Importing upstream's nearest-overlap/predicted-box fallback would weaken this property and require an incompatible detector path.

The new regression uses the actual installed tracker, checks exact current detector pixels, identity/class/confidence, crossing observations and empty-detection frames. Unmatched predictions are not presented as fresh observations. The compatible highlight improvement was ported: flagged boxes draw last with a stronger outline and label plate, preserving class/ID/confidence for ordinary observations. The offline backend already associates IDs to original detection coordinates. No inference outputs were manufactured.

## Playback chronology (#39)

The source's default half-speed evidence viewer is now 1×. Explicit slow motion remains available. Existing integrated frame-timestamp-derived clip FPS is retained, with encoded 3/10/25 FPS regressions and actual Chromium elapsed-time versus media-time checks. Clip loading is bounded; failed/decode-error clips can be retried.

Remaining limitation: live clips use a constant-rate encoding derived from the observed timestamp span. They preserve aggregate duration, not every irregular inter-frame gap. The late timing audit also removed the viewer's midpoint/30FPS guesses: new clips carry encoded cadence and actual event offset, offline clips use their existing start metadata, and unknown legacy offsets/cadence disable precise jump/step controls. Thumbnails use clip-relative time rather than inventing a capture wall clock. Exact VFR gap preservation remains follow-up work. Original protected evidence was not remuxed or overwritten.

## Landing, reviewed alerts, casework and reports (#36–#38, #41)

The public source layout/fonts/complete connectors were ported. Public media has independently verifiable CC BY 3.0 provenance instead of assuming the source stock assets are licensed for redistribution. Replacement clips use actual YOLOX-S detections, heuristic redaction and a LOCAL RECORDED REPLAY watermark. Public confirm/reject buttons are explicitly a local simulation and create no tenant decisions. No measured speed or genuine incident is claimed.

The source curated event IDs/reclassification/replay behavior is restricted to explicit mock mode plus curation opt-in. It cannot reset or hide an operational tenant's confirmed/rejected observations. Rejected alerts retain server status, stay out of the open queue and sort behind unresolved records. No fabricated patrol layer or operational KPI was imported. Known demonstration camera names are visibly prefixed DEMO without changing actual source metadata.

Plain Romanian summaries, conditional full-redaction wording, case confirmations and export-verification messages are merged into existing casework. Existing MFA, notes/bookmarks, independent export approval, encrypted media, hash verification, archive and immutable audit behavior remain. Unknown audit actor roles are not fabricated. Existing integrated Settings already gives more conservative privacy/legal wording and hides fictional users outside mock mode, so it supersedes the smaller source wording change.

The one-page report uses authorized loaded records, explicit denominator/timezone/context and no official-traffic-statistics claim. Chromium PDF generation verifies one A4 page for the controlled data set. This is not proof that an arbitrary number of camera/type rows fits one page; large-data report pagination remains future work.

## Deliberate non-copies

- Source browser/worker scripts assume older demo credentials/token/key/profile/DB state. The integrated runner instead creates new guarded databases, genuine MFA accounts, real browser actions, actual ONNX workers and scoped private credentials. The source scripts are review artifacts, not supported integration commands.
- Source map HTML marker construction/external basemap was not substituted for existing safe DOM text markers and the integration's schematic/offline map. No external camera was contacted.
- Upstream `G-ledger.md` is historical evidence, archived with its original source. It does not count as executed integration tests.
- No package manifest, lockfile, model registry, migration lineage, private credentials, existing media/evidence or original worktree was overwritten.

## Late lifecycle test repair

A repeat exposed a misleading test helper lifecycle: reconfiguration/rollback browser tasks could launch another API in the same fixture process, whose teardown stopped the worker. Those tasks now use the existing running API, and the helper rejects accidental parallel lifecycle creation while workers exist. The worker must actually observe the new approved revision and exit; the test still requires exit0. Managed SIGTERM additionally cancels unaccepted retry work instead of waiting indefinitely. Both the failed repeat and corrected same-API execution are preserved in the ledger.
