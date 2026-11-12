# Local development on Linux (no Docker, no sudo)

## PostgreSQL for the backend tests (user-level conda env)
```bash
conda create -n rs-pg -c conda-forge postgresql -y          # installed PostgreSQL 18.6 here (CI uses 16)
P=~/miniconda3/envs/rs-pg/bin
echo devpg > /tmp/pgpw && $P/initdb -D ~/.rs-pg-data -U postgres --auth=scram-sha-256 --pwfile=/tmp/pgpw
$P/pg_ctl -D ~/.rs-pg-data -o "-p 55432 -c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp" -l ~/.rs-pg-data/log.txt start
export RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres:devpg@127.0.0.1:55432/postgres
```
The password `devpg` is a throwaway for a localhost-only test cluster. Stop with `$P/pg_ctl -D ~/.rs-pg-data stop`.

## Backend
```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r backend/requirements.lock pytest httpx ruff black mypy
cd backend && ../.venv/bin/python -m pytest -p no:warnings      # 319 passed (PostgreSQL 18.6)
```
## Frontends (Node 22)
```bash
export PATH=~/miniconda3/envs/rs-node22/bin:$PATH
(cd frontend && npm ci && npx tsc -b && npm run lint && npm test && npm run build)
(cd secure-pwa && npm ci && npm run lint && npm run typecheck && npm test && npm run build)
```
