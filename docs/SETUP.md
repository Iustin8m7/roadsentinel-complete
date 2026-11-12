# Setup (Linux, macOS, Windows)

**Verified on Linux (Ubuntu 24.04) only.** The macOS and Windows commands are the equivalent ones but were not run for this branch; the Python scripts (`scripts/demo.py`, `scripts/backup.sh` is bash and needs WSL/Git Bash on Windows) avoid shell-specific features where possible.

## Prerequisites
* Python 3.12 (`uv` recommended), Node.js 22 (>= 22.12), PostgreSQL 16+ (the suite passed on 18.6; CI is configured for 16.10), `ffmpeg` for the pipeline.
* Docker is optional (the compose stack was not run for this branch).

## PostgreSQL without Docker or root
| OS | How |
|---|---|
| Linux / macOS | `conda create -n rs-pg -c conda-forge postgresql -y`, then `initdb -D ~/.rs-pg-data -U postgres --auth=scram-sha-256 --pwfile=<file with a throwaway password>` and `pg_ctl -D ~/.rs-pg-data -o "-p 55432 -c listen_addresses=127.0.0.1" start` (exact commands used here: `docs/LOCAL_DEV_LINUX.md`). Or Homebrew `brew install postgresql@16` |
| Windows | Installer from postgresql.org (or `choco install postgresql16`), or WSL2 with the Linux commands |

Use a **localhost-only** cluster with a throwaway password for development. Never reuse it.

## Backend and tests
```bash
uv venv --python 3.12 .venv                      # Windows: same command; activate with .venv\Scripts\activate
uv pip install --python .venv/bin/python -r backend/requirements.lock pytest httpx ruff black mypy
export RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres:<pw>@127.0.0.1:55432/postgres   # PowerShell: $env:RS_TEST_ADMIN_DATABASE_URL="..."
cd backend && ../.venv/bin/python -m pytest -p no:warnings      # Windows: ..\.venv\Scripts\python
```
Pipeline/root tests (no torch needed): `uv pip install --python .venv/bin/python -r requirements-api.txt opencv-python-headless pyyaml numpy pytest ruff && .venv/bin/python -m pytest tests`.

## Frontends
```bash
cd frontend  && npm ci && npx tsc -b && npm run lint && npm test && npm run build
cd secure-pwa && npm ci && npm run lint && npm run typecheck && npm test && npm run build
```
Browser walks (routes × roles, axe, console errors, strict CSP): `cd frontend && npx playwright install chromium && npm run test:e2e && npm run test:e2e:pwa` (the PWA walk needs `secure-pwa` built first).

## Local demo with synthetic data
```bash
python scripts/demo.py --admin-url postgresql://postgres:<pw>@127.0.0.1:55432/postgres            # strict: TOTP required
python scripts/demo.py --profile demo --admin-url …                                               # password-only for a stage demo, local only
cd frontend && npm run dev          # UI on :5173, proxies /api to :8000
```
The script writes `.env.demo` (git-ignored), creates the database and roles, seeds data marked SINTETIC and prints a one-time password.

## Detection pipeline
```bash
uv pip install --python .venv/bin/python -r requirements.txt     # pulls torch/ultralytics (large)
scripts/download_data.sh                                         # Linux/macOS/Git Bash: sample clips
.venv/bin/python -m roadsentinel.pipeline cameras/demo-highway.yaml --no-wandb --max-seconds 10
```
Not run in this environment: everything that needs torch (see docs/FINAL_STATUS.md).
