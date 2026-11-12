# Baseline (branch design/pro-ui, from main a2c870d)

Environment: Node v20.20.2, npm 10.8.2 (secure-pwa Dockerfile/CI use Node 22.12). Dependencies installed locally with `npm ci` (node_modules is git-ignored). Nothing was fixed.

| App | typecheck | lint | unit tests | build |
|---|---|---|---|---|
| frontend/ | pass | **FAIL** 8 errors (6x no-explicit-any in ArchivePage/IasiMap/TacticalMap, prefer-const in ui.tsx:17, unused `decided` in hooks/index.ts:101) | pass 6/6 (1 file) | pass |
| secure-pwa/ | pass | pass (eslint + prettier) | **FAIL to start**: vitest worker crashes loading `undici` (`Cannot read properties of undefined (reading 'bind')`) on Node 20; 0 tests ran. Likely Node-version mismatch (CI uses Node 22); to be re-run on Node 22 | pass |

Bundle sizes before redesign (build output):
- frontend: index.js 1,268.78 kB (gzip 386.25), IasiMap.js 160.71 kB (gzip 47.26), index.css 62.37 kB (gzip 11.10), IasiMap.css 15.61 kB (gzip 6.46). Vite warns chunk >500 kB.
- secure-pwa: index.js 286,341 B, index.css 2,515 B, sw.js ~17 kB; precache 12 entries 293.63 KiB.

Not run: backend pytest, Playwright smoke (frontend/scripts/smoke.mjs is known stale), root tests/.
