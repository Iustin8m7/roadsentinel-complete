# WOW_DIRECTION — "Night Watch"

Branch `design/wow`. One direction, committed to. (No `frontend-design` skill was available in this environment; decisions below are mine.)

## Concept and mood
A control room at 3 a.m.: deep ink-blue glass, one luminous **signal** colour, and the city drawn as a faint road graph that you read by light, not by chrome. Quiet by default, loud only when something is wrong. The first impression is cinematic (hero, glow, depth); the work screens stay disciplined so a dispatcher can stare at them for ten hours. The product is a *road-network sentinel*: the recurring motif is a **node-and-edge graph** (roads as edges, cameras as nodes) and a **scan line** (thin, slow, decorative only).

Rule of thumb: **light means meaning**. Glow appears only on (a) severity, (b) the primary action, (c) the live connection. Everything else is matte.

## Colour (dark first, light refined)
- Dark "ink": void `#070b14`, panel `#0d1422`, raised `#141d2f`, lines `#26344d`. Cool, slightly violet-leaning blue-black; never pure black.
- **Signal** (action): azure-cyan `#4db5ff` with a brand gradient to violet `#8b7bff` (`--grad-brand`, decorative/hero/logo/primary-button sheen only).
- Severity: critical coral-red `#ff5d73`, high amber-orange `#ff9a3d`, medium gold `#f5c542`, info teal `#3fd0c9`; ok `#4cd38a`. Always shape + label too (unchanged rule). Critical is the only colour allowed to pulse/outline-glow in work screens.
- Light "paper daylight": void `#edf1f7`, panel `#fff`, deep-blue action `#0b57d0`; severity darkened to pass 4.5:1. Same structure, glows replaced by crisp tinted edges.
- Colour-blind-safe chart palette (Okabe–Ito derived) as `--chart-1..6`.
- All text tokens verified >= 4.5:1 by `scripts/check-tokens.mjs` in both themes.

## Typography
- **Display & numbers: Space Grotesk** (variable, `@fontsource-variable`, bundled). Used for h1/h2, KPI figures, the wordmark. Tabular figures on.
- **Text: Geist** (already bundled). **Data: Geist Mono** (ids, timestamps, hashes, plates).
- Scale 12/13/14/16/20/28 + display 40/56 on the hero only. Sentence case; tracking only on tiny mono labels.

## Depth system
Four layers: `void` (page, with a faint grid + radial aurora), `panel` (matte card, 1px line + inner top highlight), `raised` (inputs, hover), `glass` (command palette, dialogs, toasts, hero login card: `backdrop-filter: blur`, translucent panel, used only there). Soft glow shadows tied to meaning (`--glow-crit`, `--glow-signal`). A static SVG **grain** file (bundled, 3% opacity) over the void only. 8px rhythm; radii 6/10/16.

## Motion language
Fast, eased out (`cubic-bezier(.2,.8,.2,1)`), 120/200/360 ms. Entrances = fade + 8px rise, staggered 40ms on lists. Numbers tween 400ms. Hero: slow canvas-free SVG road graph, drifting pulses along edges, 1–2% parallax. Work screens: **no ambient animation** except the critical edge pulse (2 loops max-per-new-alert) and the connection dot. Never moves a control the operator is about to click (new alerts are held behind a chip, as before). Everything off under `prefers-reduced-motion`; **Calm mode** (`data-calm`, persisted `rs-calm`) additionally removes glow, aurora, grain, pulses and entrance staggers.

## Iconography
Bundled lucide at 1.75 stroke, 16/18/20 px, `aria-hidden` when paired with text. Severity keeps its shape glyphs (triangle/diamond/dot/dashed ring). Custom inline-SVG logo mark (shield-eye on a road node) and spot illustrations for empty/error states in the same line style (1.5px strokes, signal + muted).

## Imagery / illustration
No photos. Decorative art is abstract: road graph, node halos, scan arcs; always `aria-hidden` and visibly unlike data (no numbers, no labels, no "live" wording). Empty states: line illustrations (radar, folder, signal-lost) in signal-on-ink.

## Honesty guardrails
Hero copy states what the product does (detects candidate events from camera streams, a human decides, decisions are audited), with no counters, no accuracy, no uptime, no compliance claims. Charts/KPIs bind to API data only. Mock screens keep the "Demonstrativ" banner; demo curation stays OFF.
