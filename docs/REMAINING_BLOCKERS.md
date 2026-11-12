# Remaining blockers

## 2026-11-07 HLS/catalog implementation update

- HLS source handling is implemented in `roadsentinel/sources.py` and passes a bounded local
  playlist/decode fixture (24 source tests pass). This does not establish that any Romanian
  HLS source is current, decodable, vehicle-bearing, or permitted for processing.
- The authenticated backend discovery endpoint and UI integration are implemented, but this
  session did not exercise them against PostgreSQL/Chromium: configured local PostgreSQL
  endpoints were unavailable. The 35-row registry validates directly from JSON/Pydantic.
- Romanian candidates remain disabled; no physical camera is attached. Next action is to run
  the backend discovery and browser checks on the disposable test DB, then obtain an owned
  camera or source-specific processing basis before attempting any third-party frame decode.

## 2026-11-07 physical-live source status

- No local optical capture device was available. `find /dev -maxdepth 1 -name 'video*' -print`
  returned no paths; the bounded probe `timeout 15s .venv/bin/python -m scripts.probe_uvc_camera
  --device-index 0 --seconds 3` exited 2: `CAMERA_UNAVAILABLE: camera device /dev/video0 is
  missing`. Thus physical-live inference/vehicles/browser preview/persistence remain blocked.
- An explicit `device:N` UVC integration path, V4L2 capture, backend source-health schema support,
  no-calibration detection-only support and local profile now exist. Replay is never selected as a
  fallback. See `LIVE_CAMERA_OPERATOR_GUIDE.md`.
- Romanian source pages remain candidates only. LINX identifies municipal-monitoring imagery and
  copyright protection; InfoBuz describes selection-triggered embeds that appear when permitted;
  WebcamRomania identifies original feed owners. No documented automated-processing basis was
  found and no stream was opened. See the 2026-11-07 follow-up in `EXACT_ROMANIAN_CAMERA_URL_AUDIT.md`.
- **Next action:** connect an owned USB camera able to view a lawful scene, or document a permitted
  source endpoint and its processing scope. Then run the real pipeline through signed ingestion,
  PostgreSQL and authenticated Chromium. Recorded loopback E2E is replay evidence only.

This list separates code work from conditions that require an external owner, approved data, or
local infrastructure access. No item below is resolved merely by adding code.

| Blocker | Affected tasks | Required evidence / owner | Current status |
|---|---|---|---|
| Docker socket access denied | RS-002, RS-008, RS-014 | Check Docker from the user's normal host terminal; if that works, sandbox mediation is the likely difference. Do not change privileged groups or daemon configuration without approval. | `docker info` and `docker ps` fail with API permission denied. Socket is mode 0660, owner nobody, group nogroup/GID 65534; this process lists GID 65534, so simple missing supplementary group membership does not explain the denial. Host terminal access cannot be tested from this session. Compose not started; native local stack remains usable. |
| Model-generated incident and review path | RS-007, RS-008 | Genuine candidate on authorized footage, generated from model tracks, then secure ingest, PostgreSQL, and operator review; evaluate false positives/misses. | Production `RuleEngine` generates a deterministic reverse-motion `SYNTHETIC TEST` candidate through signed ingest, PostgreSQL, operator APIs, archive search, and audit. Latest real YOLO E2E separately injected a marked synthetic event and verified authenticated browser rejection plus DB status/audit. Real replay emitted zero candidate; model-track candidate accuracy remains unverified. |
| Per-frame detection persistence | RS-007, RS-008 | Decide retention and schema/query requirements for bbox-level detection history; add bounded tenant-scoped storage if approved. | Live API persists model identity/hash, class track totals, observation totals, source health, latency, memory, and crossing counts in existing camera JSONB. Per-frame boxes/confidence/track data stay in the optional local JSONL log. |
| Live annotated preview and worker controls | RS-007, RS-008, RS-017 | Worker start/stop/restart controls and physical camera input remain open. | Authenticated camera preview now serves the latest redacted/annotated JPEG from a tenant+camera-scoped in-memory store (four-second TTL, one latest-only worker queue). The actual YOLO loopback-replay E2E passed and Chromium verified changing frame sequence/timestamp and saved an overlay screenshot. External feeds remain disabled; no physical `/dev/video*` camera was present at environment inspection. Worker lifecycle controls remain unimplemented. |
| Camera source and rule configuration UI | RS-009, RS-017 | Audited source registration, enablement/authorization workflow, threshold/rule/zone/line editor, versioning, and running-worker config refresh. | Existing camera editor changes audited metadata only. Camera YAML and code still own source/rule/geometry config; admin UI does not create or tune worker sources. |
| Pipeline event publishing integration | RS-007, RS-008 | Exercise pipeline's tracked detector output, evidence generation, event metadata enrichment, clip-window delay, and RemoteSink publisher with deterministic synthetic tracks. | The production RuleEngine and AlertGate now generate/pass a deterministic synthetic candidate into signed ingest, DB, operator review, archive and audit. The real YOLO replay generated no incident; the actual pipeline evidence/clip publisher glue is not yet demonstrated with a generated event. |
| Legacy root API TestClient stalls | RS-003, RS-008 | Resolve the local async-client/event-loop compatibility issue and rerun the legacy suite with bounded timeouts. | Fresh `timeout 15s .venv/bin/python -X faulthandler -m pytest -q tests/test_api.py -x` again exited 124 with no response. Earlier faulthandler and minimal FastAPI TestClient / httpx ASGITransport probes stalled; FastAPI 0.143.3, Starlette 1.8.0, httpx 0.28.1, httpx2 2.16.0, AnyIO 4.15.1. Root cause remains unisolated. The secure backend network integration tests and the new Uvicorn E2E pass independently. |
| Backend test fixture recreates `rs_test` | RS-008, RS-010–013 | Always point it at a disposable PostgreSQL instance/database. | Safe process demonstrated: full 392-test backend suite and 4 new heartbeat tests ran against an isolated `/tmp` cluster; do not reuse the developer database. |
| Romanian camera processing rights and full source verification | RS-006, RS-007, RS-009 | For each owner, applicable license/terms or authorization covering machine analysis, permitted protocol/rate, transient frame handling, preview display and retention; then bounded frame/decode verification. | Exact 16 owner-supplied page URLs audited in `docs/EXACT_ROMANIAN_CAMERA_URL_AUDIT.md`. Iași's exact supplied HLS master answered HTTP 200 and advertised a 1920×1080/20fps variant, but no child playlist or media was fetched; WebcamRomania terms state feeds belong to original operators and are shown via embeds. LINX pages state copyright and municipal-network origin; InfoBuz embeds only feeds configured as permitted. No source-specific analysis permission was found. All external cameras stay disabled. OpenCam/ARGOS child maps could not be enumerated due inspection-tool cache misses. |
| Physical local camera | RS-007, RS-017 | Operator connects an owned USB/phone/RTSP camera and validates it locally. | No `/dev/video*` device was present in the checked host environment. A continuous loopback MJPEG replay has passed, but is a clearly marked recorded replay, not a physical live camera. |
| GPU acceleration | RS-005, RS-007 | Working NVIDIA driver/CUDA runtime or another verified supported accelerator provider. | NVIDIA PCI device is present, but `nvidia-smi` cannot communicate with a driver and ONNX Runtime exposes only Azure/CPU providers. Do not install or change system drivers without approval; current inference remains CPU-only. |
| Representative labeled traffic dataset | RS-005–007 | Licensed/consented multi-condition video, labels, provenance, and leakage-safe split. | Not identified; public camera pages are not sufficient. |
| Detection acceptance thresholds | RS-005 | Product/domain owner approval for per-class precision/recall, false alerts/hour, and counting tolerances. | Awaiting owner input. |
| Privacy/legal governance | RS-009, RS-013 | Legal basis, DPIA, purpose limitation, retention schedule, and operational data handling approved by the responsible organization. | Not present in repository. |
| Production key service | RS-010 | Organization selects and provisions KMS/HSM/Vault and recovery/dual-control process. | No infrastructure selection. Local key-provider work does not meet this requirement. |
| Independent audit anchor | RS-011 | Independently administered immutable storage/signing key and retention policy. | Local Ed25519 JSONL adapter is implemented for development only; no external anchor configured. |
| Independent security assessment | RS-012 | Qualified reviewer and remediation retest. | Not performed. |
| Production environment and restore drill | RS-014–015 | Approved hosting, persistent storage, secret store, monitoring/on-call channel, and restore target. | Not available/verified; no deployment performed. |
| Git metadata write access | Local branch/checkpoint organization | Workspace administrator must make `.git` writable if local branches/commits are desired. | Read-only; remain on current branch without commits. |
| Real push-notification delivery | RS-015/018 | Approved browser/device and organizational push endpoint. | Not verified. |
| Software/model/dataset licensing decision | RS-004, RS-006 | Legal review of repository license absence and each dataset/model license. | Ultralytics avoided; YOLOX Apache-2.0 repository and CC BY 3.0 sample were used with provenance documented. Broader legal review remains; this is not a legal determination. |

## Safe local alternatives

- Use synthetic fixtures and explicitly licensed local video files for connector, tracking, and
  UI tests.
- Use a new isolated database name/instance for integration tests; never point tests at a valuable
  developer database.
- Build local-only anchor and key-provider interfaces with development implementations and clearly
  state their security limits.
- Treat unapproved camera records as disabled metadata entries with no source URL and no worker.
# Current physical-live camera blocker — 2026-11-07

- **No local optical capture device is available:** `find /dev -maxdepth 1 -name 'video*' -print`
  returned no entries. `timeout 15s .venv/bin/python -m scripts.probe_uvc_camera --device-index 0 --seconds 3`
  exited 2 with `CAMERA_UNAVAILABLE: camera device /dev/video0 is missing`. No real physical-live
  frames, vehicle detections, browser preview, or live-camera persistence can be claimed.
- **Romanian candidates remain ineligible for analysis:** the latest bounded review of the owner
  supplied listing pages found no published machine-processing scope/allowed endpoint. LINX text
  identifies municipal monitoring imagery and a copyright notice; WebcamRomania pages distinguish
  original owners and directory/embed presentation; InfoBuz says its embeds load on selection and
  only permitted feeds appear. No feeds were opened or decoded. See `EXACT_ROMANIAN_CAMERA_URL_AUDIT.md`.
- **Implemented local prerequisite path:** explicit `device:N` source validation, OpenCV V4L2 open,
  supervised live-reader path, backend `device` health schema, no-calibration detection-only support,
  and `cameras/local-uvc.yaml`. It does not silently fall back to a video replay. Plug in an owned
  UVC camera, ensure `/dev/videoN` access, run the documented bounded probe, then run the existing
  real-model signed-ingest/browser E2E with that source. A camera aimed at roadway must have an
  appropriate lawful/privacy basis.
- **Next user action:** connect an owned USB webcam that can lawfully observe traffic, or provide a
  documented eligible source/authorization and approved endpoint. Until then, the true-live-camera
  acceptance gate stays **BLOCKED**, while the recorded-replay proof remains valid only for replay.

