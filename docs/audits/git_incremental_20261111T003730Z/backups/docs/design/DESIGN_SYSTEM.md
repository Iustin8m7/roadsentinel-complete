# RoadSentinel design system

Applies to `frontend/` (dispatcher, Tailwind 4) and `secure-pwa/` (plain CSS). Both load the same tokens.

## Tokens
Single source: `design/tokens.css`. Copies: `frontend/src/styles/tokens.css`, `secure-pwa/src/tokens.css`.
`node scripts/check-tokens.mjs` fails when a copy drifts and when any text/status token drops below 4.5:1 on the three surfaces, in light and dark.
Edit `design/tokens.css`, run `npx prettier --write design/tokens.css` (secure-pwa's prettier), copy to both apps, run the check.

| Group | Tokens |
|---|---|
| Surfaces | `--bg-void` page, `--bg-panel` cards, `--bg-elevation` raised/inputs, `--border-line`, `--border-subtle` |
| Text | `--text-primary`, `--text-secondary`, `--text-muted` (all >= 4.5:1 on every surface) |
| Action | `--action`, `--on-action`, `--focus-ring` |
| Severity | `--sev-critical`, `--sev-high`, `--sev-medium`, `--sev-info`, plus `--ok`, `--danger-bg` |
| Scale | spacing 4/8/12/16/24/32/48, radii 4/6/10, shadows 1/2, motion 120/200 ms, type 12/13/14/16/20/28 |
| Density | `data-density="compact\|comfortable"`; `--target-min` is 24 px (44 px on coarse pointers) |

Themes: follows the system (`prefers-color-scheme`); `data-theme="light|dark"` on `<html>` overrides it. The toggle (system, light, dark) stores only `rs-theme` in localStorage; `public/theme-init.js` applies it before first paint (external file, no inline script). `prefers-reduced-motion` zeroes transitions and animations. `:focus-visible` has a 2 px ring on every control.

In `frontend/`, Tailwind's `@theme inline` maps the tokens: `bg-void`, `bg-panel`, `bg-elevation`, `border-border`, `text-text-primary|secondary|muted`, `bg-accent text-on-accent`, `text-critical|warning|caution|info|ok`, `bg-danger`. No hex colours in components; charts and SVG use `var(--...)`.

## Severity and honesty
- Priority is never colour alone: critical = filled triangle, high = diamond, medium = dot, info = dashed ring, always with the Romanian label (Critică, Ridicată, Medie, Informativă). Map markers use the same shapes plus an alert count.
- Evidence chips (from the API `redaction` field): `full` = REDACTAT (euristic); `heads_only` = REDACTAT (euristic): doar capete (plates may be visible); `none` = FĂRĂ REDACTARE; missing = REDACTARE NECONFIRMATĂ. Mock mode shows SINTETIC / DEMO. Never "AI confirmed", never compliance claims.
- Unfinished or mock-only screens carry a "Demonstrativ" banner (mock mode only; hidden in real mode).
- Times are `dd.MM.yyyy HH:mm:ss`, Europe/Bucharest, and the zone is named where times are shown.

## Components
`frontend/src/components/ui.tsx`, `forms.tsx`, `Dialog.tsx`, `SeverityBadge.tsx`, `ThemeToggle.tsx`, `EvidencePlayer.tsx`; `secure-pwa/src/ui.tsx`.

| Component | States covered |
|---|---|
| Button (primary, secondary, confirm, reject, danger, ghost) | default, hover, focus-visible, disabled, loading (`aria-busy`) |
| Field + TextInput/TextArea/select, OtpInput | label always visible, hint, error (`role=alert`), invalid |
| Dialog / ConfirmDialog | native `<dialog>`: focus trap, Esc, inert background, focus restore; Cancel is focused first; error shown inside |
| PriorityBadge / StatusBadge / Chip | text + shape + colour |
| Banner (info, warn, error), EmptyState, ErrorState (retry), Skeleton | polite/assertive live regions |
| Table -> card list (secure-pwa `table.cards`, <= 640 px) | caption, `scope`, `data-label` |
| EvidencePlayer | play/pause, frame step, 0.25-2x, fullscreen, real slider with visible focus; shortcuts only while focus is inside the player |
| Shell | skip link, one `<main>` focused on navigation, per-route `document.title`, rail (>= 1024), icon rail (640-1023), bottom tab bar (phone), connection indicator, tz clock |

## Responsive and accessibility rules
Targets >= 44 px on touch, >= 24 px otherwise; `100dvh`; safe-area insets; reflow to 320 px; text selection enabled; every icon-only control has an `aria-label`; dialogs for every irreversible decision (reject, deny, revoke, export). WCAG 2.2 AA checked by axe in the Playwright walks (see below).

## Checks
- `node scripts/check-tokens.mjs`
- `frontend`: `npm run typecheck && npm run lint && npm test && npm run build`
- `secure-pwa`: `npm run typecheck && npm run lint && npm test && npm run build`
- Walks (Playwright, Chromium, API stubbed in the browser; fail on console errors, uncaught errors, requests to other origins, axe violations, missing/duplicate `h1`/`main`, horizontal overflow):
  `cd frontend && npm run test:e2e` (mock + real mode, light/dark, desktop/mobile), `npm run test:e2e:pwa` after `cd ../secure-pwa && npm run build`. Add `-- --shots` to write screenshots to `docs/design/screens/`.
  Browser install without touching the home directory: `PLAYWRIGHT_BROWSERS_PATH=$PWD/node_modules/.pw-browsers npx playwright install chromium`.


## v2 "Night Watch" (branch design/wow)
Direction and rationale: `WOW_DIRECTION.md`. Summary of what changed on top of the system above:
- **Tokens v2** (`design/tokens.css`, same copy/check flow): ink dark (`--bg-void #070b14`), signal azure `--action` + `--accent-2` violet (decorative gradient `--grad-brand`), colour-blind-safe `--chart-1..6`, depth tokens (`--glass-bg`, `--glass-line`, `--aurora-a/b`, `--grid-line`, `--grain-opacity`), meaning-bound glows (`--glow-signal|crit|high`), `--ease-out`, `--motion-slow`, `--radius-xl`, `--fs-3xl/4xl`.
- **Type**: Space Grotesk (display, numbers; `@fontsource-variable`, bundled; frontend via npm, secure-pwa via copied woff2 in `public/fonts`), Geist (text), Geist Mono (data). Utilities: `font-display`, `.num`, `.eyebrow`.
- **Surfaces**: `.card`, `.card-raised`, `.glass` (only palette, dialogs, toasts, user menu, login card), `.sev-edge[-critical|-high|-medium|-info]`, body stage = aurora + grid + bundled grain (`/img/grain.svg`).
- **Motion**: `.rise`, `.page-in`, `.stagger`, `.shimmer` (skeletons), `.press`, `.crit-pulse` (3 loops, critical only), hero `.hero-edge/.hero-node/.hero-scan`, chart `.bar-grow/.donut-arc`. Numbers tween via `AnimatedNumber`.
- **Calm mode**: `data-calm="on"` on `<html>` (persisted `rs-calm`, applied pre-paint by `theme-init.js`; toggle in both apps). Removes glow, aurora, grid, grain, blur, entrance and ambient animation. `prefers-reduced-motion` does the same.
- **Components added**: `CommandPalette` (Ctrl/Cmd+K, native dialog, combobox/listbox), `CalmToggle`, `AnimatedNumber`, `HeroGraph` (decorative SVG road graph, parallax via CSS variables), `Illustrations` (RadarArt, FolderArt, SignalLostArt), Logo v2. Stats charts are hand-drawn SVG (recharts removed).
- Honesty is unchanged: decorative art is `aria-hidden` and labelled as decorative on the login page; KPIs/charts bind to API data only; no bounding-box overlay exists because the API provides no box data.
- Visual check: `cd frontend && node e2e/shots.mjs [--only login,queue,case,cameras,archive,stats,audit] [--vps desktop] [--themes dark]` writes to `docs/design/screens-wow/` (mock data). PWA: `SHOTS_DIR=../../docs/design/screens-wow node e2e/pwa-walk.mjs --shots`.
