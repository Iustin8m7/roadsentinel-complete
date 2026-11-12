# Dependency update plan (Dependabot branches are NOT merged)

Order is by risk, lowest first. "Test first" is the exact check to run on a throwaway branch
before accepting. All Dependabot branches are from 2026-10-17..31 and reviewed from their diffs.

| # | Update | Risk | Decision | Test first |
|---|---|---|---|---|
| 1 | `github_actions/codeql-action/init` + `/analyze` 4.39.0 → 4.39.1 | low (patch; both must match) | merge together | CodeQL workflow run |
| 2 | `actions/setup-python` 7.0.0 → 7.1.0 | low | merge | CI `backend`, `pipeline` jobs |
| 3 | `actions/upload-artifact` 4.6.2 → 7.0.2 | low-medium (3 majors; only SARIF upload) | merge after a CodeQL run | CodeQL run keeps its artifacts |
| 4 | `npm-minor` group in `secure-pwa` (react-router-dom, typescript-eslint, vite patch/minor) | low | merge | `cd secure-pwa && npm ci && npm run lint && npm run typecheck && npm test && npm run build` + walk |
| 5 | `caddy` 2.10.2 → 2.11.6 (`deploy/docker-compose.yml`) | low-medium | merge, and bump `deploy/railway-web/Dockerfile` (not covered by Dependabot) | `caddy validate` of both Caddyfiles; stack smoke job |
| 6 | `typescript` 6.0.3 → 7.0.2 (`secure-pwa`) | medium-high (new compiler; `typescript-eslint` support unverified) | **close for now** | needs typescript-eslint release that supports 7 |
| 7 | `python` 3.12 → 3.15 (`backend/Dockerfile`) | high (`requires-python >=3.12,<3.13`, wheels for cryptography/psycopg/pydantic unverified) | **close** | revisit after 3.13/3.14 is the validated target |
| 8 | `node` 22 → 25 (`secure-pwa/Dockerfile`) | high (odd-numbered, non-LTS) | **close**; use the current LTS only | CI uses Node 22 |
| 9 | `postgres` 16 → 18 (`deploy/docker-compose.yml`) | high (data-directory layout change, two majors, CI stays on 16) | **close**; do deliberately with a `pg_upgrade` plan | restore a backup into 18, run the full backend suite against 18 |

Gaps: Dependabot does not watch `frontend/` (the deployed police UI), root `requirements*.txt` or
`deploy/railway-web/Dockerfile`; add those ecosystems to `.github/dependabot.yml` when GitHub use resumes.

Local note: the backend suite passed (328 tests) on PostgreSQL 18.6 as well as being configured for 16 in CI,
which is evidence for item 9 but not a replacement for the restore test.
