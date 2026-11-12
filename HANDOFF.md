# RoadSentinel: handoff (state of `release/ready`)

Read next: `docs/IMPLEMENTATION_PROGRESS.md` (what was done and how it was verified), `docs/FINAL_STATUS.md` (real gate numbers and what is unverified), `docs/LIMITS.md` (what the system is not). The old Romanian handoff of 2026-10-18 is archived in `docs/archive/` and is **outdated** (it described a password-only demo).

## What is where
| Folder | What |
|---|---|
| `backend/` | The product API (FastAPI, PostgreSQL with row-level security, MFA, signed ingestion, encrypted evidence, hash-chained audit, four-eyes, retention, patrol workflow). Contract: `API.md`. Tests need PostgreSQL |
| `frontend/` | Operator UI (Vite, React 19). Speaks the `/api/login`, `/api/events`, `/api/stream` dialect. `VITE_USE_MOCKS=1` = labelled demo data |
| `secure-pwa/` | Patrol / auditor / admin app (PWA): MFA enrollment, approvals, audit chain, sessions, retention, account recovery, patrol status |
| `roadsentinel/` | Detection pipeline: rules, tracking, alert gate, live reader/supervisor, model registry, evaluation harness. `server.py` + `web/` are the **deprecated** legacy demo |
| `cameras/*.yaml` | Per camera: video, calibration, zones, rules, thresholds, alert gate, model, `source_consent` |
| `training/` | Fine-tune scripts, `eval.py`, `make_manifest.py`, `check_dataset.py`. Weights and data are git-ignored |
| `models/` | `registry.json` (tracked), weights (ignored), reports, change log |
| `scripts/` | demo, backup/restore, model tools, calibration, secret scan, latency measurement |
| `deploy/` | compose + Caddy (local), `railway-web/` gateway. **Docker was not available** when this branch was built: nothing here was built or run |

## Decisions in force
* MFA is mandatory. `RS_MFA_EXEMPTION_ENABLED` exists for local demos only and is refused in production.
* Deploys are manual (`workflow_dispatch`, type `DEPLOY`) and need a green CI run for the commit. Confirm persistent evidence storage first (`docs/OPERATIONS.md`).
* `frontend/` = operators, `secure-pwa/` = patrol/auditor/admin. `web/` and `roadsentinel/server.py` are frozen.
* Public webcam streams stay off until `source_consent` is filled in the camera file.
* Redaction is on by default and a heuristic; `off` needs `RS_ALLOW_UNREDACTED=1` and shows FĂRĂ REDACTARE.
* Only numbers produced by `training/eval.py` may appear in docs or UI.

## Run it
`docs/SETUP.md` (Linux, macOS, Windows). One command for a local demo with synthetic data: `python scripts/demo.py`.

## Integrating the teammate's model
`docs/MODEL_INTEGRATION.md`.

## Open questions for the owners
1. Written permission from the webcam owner (WebcamRomania / Grand Hotel Traian) and the dataset licences (`docs/DATA_CARD_TEMPLATE.md`).
2. Where the production secrets, master keys, Railway access and the fine-tuned weights are stored besides one laptop.
3. Whether a second tenant admin exists in each unit (account recovery is four-eyes).
4. Legal basis, retention periods and DPIA: none has been decided by this repository.
