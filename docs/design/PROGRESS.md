# PROGRESS (branch design/wow, from design/pro-ui; LOCAL ONLY: no push/fetch/gh)

Resume rule: read this file, `git log --oneline`, continue at "Next". Node must be v22.x. The previous phase log is in git history (`git show design/pro-ui:docs/design/PROGRESS.md`).

## Done (all committed locally)
1. `WOW_DIRECTION.md` (art direction "Night Watch"), tokens v2, Space Grotesk bundled, global CSS layer, calm mode.
2. Core components v2: buttons (sheen, press), cards, glass dialogs/menus/toasts, badges as pills, skeleton shimmer, illustrated empty/error states, command palette (Ctrl+K), animated numbers.
3. Login: hero with animated SVG road graph (decorative, labelled), headline + honest value proposition, glass login card, MFA step; shell: new rail with active marker, top bar with palette trigger, connection pill, tz clock, calm + theme toggles, page transitions.
4. Dashboard: command-center header sentence from real counts, KPI tiles (critical glows and pulses 3x), severity-edge alert feed (list never shifts, new alerts behind chip), preview with HUD frame, schematic map panel (road graph glow, pulsing critical markers). Case file: cinematic player (HUD brackets, glass play button, gradient scrubber with event marker, 44 px controls, glowing filmstrip), glass sticky decision bar on phones, animated audit timeline.
5. Stats rewritten as hand-drawn SVG (donut, bars, sequential single-hue heatmap, hover readout); recharts removed. Cameras (hover lift, honest empty tiles), archive (command-bar search, interpretation chips, animated results, empty-state illustration), audit/settings via restyled panels. 404/403/route error pages redone.
6. secure-pwa: same tokens, fonts, aurora/grid/grain, glass auth card and dialogs, bottom nav with inline-SVG icons, 44 px targets, CSS-only press feedback, calm toggle, compact phone top bar.
7. Polish pass from screenshots (mobile top bar, queue time column, camera tiles, case title wrap, pwa toggles/nav). Screenshots: `docs/design/screens-wow/`. `DESIGN_SYSTEM.md` has the v2 section.

## Decisions / interpretations (logged, no questions asked)
- `frontend-design` skill was not available; aesthetic decisions made directly.
- Kept Geist for text (already bundled) and added only Space Grotesk as the display face.
- Stats charts: dropped recharts for custom SVG (honest data unchanged, bundle smaller).
- Bounding-box overlays: not drawn, the API has no box data. Event marker on the scrubber stays at clip middle (pipeline cuts +-3 s around the event, as before).
- secure-pwa: no lucide (pinned security app, no new npm dependency); 4 inline SVG icons instead; fonts copied as woff2 (no new package).
- Mock case route in the walk was `/app/alerte/1` (a 404 in mock); changed to `RS-2026-4101` so the mock case file is really exercised.
- Walk now also runs axe + h1 check on `/login`.

## Gate (Node v22.23.4)
- frontend: `tsc -b` ok, eslint 0, vitest 9/9, `vite build` ok, `node e2e/walk.mjs` 0 failures (165 s).
- secure-pwa: typecheck ok, lint+prettier ok, vitest 8/8, build ok, `node e2e/pwa-walk.mjs` 0 failures.
- `node scripts/check-tokens.mjs` ok.
- Bundle (gzip): frontend entry JS 128.03 -> 133.13 kB (raw 402.24 -> 413.72 kB), CSS 45.23 kB raw -> 66.43 kB raw (12.80 kB gzip), +3 Space Grotesk woff2 (18.9 + 22.3 + 6.7 kB, loaded by unicode-range). StatsPage chunk 385.49 -> 10.53 kB (recharts removed). Lazy chunks unchanged otherwise (IasiMap 156.67, LivePlayer 398.85 only with VITE_LIVE_STREAM=1). secure-pwa entry JS 301.00 -> 303.35 kB raw (94.85 kB gzip), CSS 17.57 kB, precache 14 -> 16 entries, 314.89 -> 366.17 KiB.

## Not done / unverified
- 60 fps and "no layout shift" are not measured (no profiler run); only reasoned from CSS-only/transform animations.
- Walks stub the API in the browser; real backend, real SSE, real clip playback (frame stepping, scrubber with a real clip) and MFA end-to-end are UNVERIFIED. The mock clip is unavailable, so the player controls were only seen in their disabled state.
- Light-theme contrast verified by token check and axe in the walks, not by manual review of every state.
- Hover previews on cameras are image zoom only (no live preview). Camera "map view" reuses the existing map. Ctrl+K palette lists pages, up to 5 open alerts and a free-text archive search.
- Rules/Patrols/Settings only inherit the new surfaces (mock-only screens, not redesigned).
- `offline.html` of secure-pwa unchanged. Gateway CSP untouched. Previous-phase unverified items still apply.

## Next (if continuing)
Run both walks against the real backend (docker-compose); profile the dashboard and hero for fps; manual light-theme review; Rules/Patrols redesign or removal; push/PR only when the owner says so.

## How to run
- `cd frontend && npm run dev` (add `VITE_USE_MOCKS=1` for demo data), `npm run build`, `npm run test:e2e`.
- `cd secure-pwa && npm run dev` / `npm run build && cd ../frontend && npm run test:e2e:pwa`.
