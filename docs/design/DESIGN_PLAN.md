# RoadSentinel — DESIGN_PLAN (Phase 1 result)

> Not done in Phase 1 (read-only mode): baseline `npm ci` / lint / typecheck / test / build. No `node_modules`/`dist` exist, so there are no bundle sizes. These will be recorded as the first commit of the branch (`docs/design/BASELINE.md`).

## 1. Product, roles, tasks
AI traffic-camera alerting: detection → rules → human decision → audit. Human decides; no auto-fines. VLM is OFF (`vlm_available:false`); UI must never say "AI confirmed".
Roles (backend `policy.py`): `system_admin`, `tenant_admin`, `operator` (dispatcher), `patrol` (sees only assigned alerts), `auditor`.

| Role | Top tasks |
|---|---|
| Operator | watch live queue by priority; open case + review evidence; confirm/reject (+action, note); assign patrol; search archive; request unblur/export (four-eyes) |
| Patrol (phone) | get push; open assigned alert; see location/evidence; acknowledge; one-hand navigation |
| Tenant admin | all operator tasks; approve/deny requests (never own); manage users/invites; cameras; service accounts; key rotation |
| System admin | create tenants; users; sessions |
| Auditor | browse audit chain; verify integrity; filter/export (no alert access) |

## 2. Active vs legacy (decision)
- `frontend/` (React19/Tailwind4/zustand, RO copy, map, HLS, SSE, archive search, stats) = **active dispatcher UI** deployed on Railway. Speaks the `/api/events` contract dialect (`contract.py`).
- `secure-pwa/` (React19, plain CSS, MFA, approvals, audit chain, sessions, push, SW) = **security-reference PWA**, in docker-compose + CI, speaks `/api/alerts`+`/api/auth/*`. Natural home of patrol/admin/auditor flows.
- `web/` + `roadsentinel/server.py` = **legacy**, out of scope (no changes).
Reasoning: HANDOFF §0/§4, Railway gateway serves `frontend/`; compose/CI serve `secure-pwa/`. Both get the same design system; API contracts untouched.

## 3. Audit of current state (file-referenced)
**Honesty / claims (highest priority)**
- `frontend/src/lib/demo.ts` + `hooks/index.ts:71`, `store/data.ts:34`: demo curation applied in real mode — ~60 hidden ids, reclassified types, fabricated "acum 4 s" ages, replayed decisions kept only in-browser. Operator sees data that is not true.
- Invented patrols (`DashboardPage.tsx:15-20`, `lib/iasi.ts:76-81`), mock `USERS` shown in Settings in real mode (`SettingsPage.tsx:2`), hand-assigned camera names/GPS overriding API (`lib/iasi.ts`, `adapters.ts`), "v2.4" tag (`AppLayout.tsx:265`), stats "time to react" = wall-clock since event, decorative trend arrows, hard-coded peak hours.
- Compliance/guarantee copy: "Directiva UE 2016/680", "Garanții arhitecturale de conformitate", "nemodificabil" (`SettingsPage.tsx:38-44`, `AuditPage.tsx:80`, `LoginPage.tsx:134`). `secure-pwa`: "Faces and plates blurred (default)" (`AlertsPage.tsx:171`) is false when pipeline runs `RS_REDACTION=off` (demo); "Grants last 30 minutes" hard-coded.
- Backend facts the UI must not contradict: login currently password-only (MFA bypassed on `main`, `auth.py:82`); pipeline stores identical bytes as "original" and "redacted" → **no unblur affordance for pipeline evidence**; `heads_only` means plates visible.
**Broken / inconsistent**
- Tokens: undefined classes `bg-deep-void`, `font-heading`, `shadow-glow-accent`; `accent` redefined to pale grey but pages use `bg-accent text-white` (unreadable) — `ArchivePage.tsx:140`, `ErrorPages`. Two `Button/Badge/Skeleton` sets (`ui.tsx`, `ui-login.tsx`), dead legacy components (`BadgeKpi`, `RibbonHeader`, `RoleBadge`, `CameraMonitor`, `lib/search.ts`).
- `can()` in real mode excludes patrols/rules/settings → permanent 403 while nav/dropdown still link there (`permissions.ts:53`, `AppLayout.tsx:339`). Rules/Patrols are mock-only.
- No MFA UI in `frontend/` though client expects it. `?q=`/`?camera=` never read by Archive.
**States**: `store.error` never rendered; decision failures silent; no loading/empty on most pages; clip-preload overlay blocks whole app (`AppLayout.tsx:180`); `secure-pwa` has unhandled rejections in decide/approvals/audit/sessions, no error boundary.
**A11y**: no focus-visible styles, modals without dialog role/focus trap (`AlertDetailPage:223`, live modal, `secure-pwa Overlays.tsx`), icon buttons only `title`, hover-only controls, global Enter/Space key hijack (`AppLayout:96`, `EvidencePlayer`), 8–11px muted text ~3:1, no reduced-motion, `select-none` on body, nested `<main>`, no per-route titles, unlabeled form fields.
**Mobile**: `frontend/` fixed `h-screen overflow-hidden` shell, non-collapsing sidebar, 380px login, clipped decision buttons; `secure-pwa` tables only, 33px targets, adjacent Confirm/Reject with no confirmation, no safe-area, 5-min idle lock without recovery path.
**Security-relevant**: Leaflet `divIcon` string-interpolates camera/patrol names (`IasiMap.tsx:78-124`) → escape; CSP conflicts: OSM tiles, webcamromania HLS, inline `style=` in divIcon vs strict `style-src 'self'`; Railway gateway CSP has `'unsafe-inline'`. No CI for `frontend/`; `frontend` smoke test is stale.
**Copy**: EN in `secure-pwa` entirely; mixed RO/EN in `frontend` ("CRITICAL / CRITIC", "Audit Log", Online/Offline); inconsistent Confirmat/Confirmată; raw enums; mixed date locale; no timezone label.

## 4. Design direction
- **Language**: calm "operational" — dark default + light theme, neutral slate surfaces, one blue action color, no glow/gradient/pulsing decoration, no uppercase shouting, weights ≤600. Geist/Geist Mono self-hosted (already in repo `frontend/public/fonts`; add to secure-pwa).
- **Severity** (never color alone: icon + label + left bar shape): critical = ▲ filled red-magenta, high = ◆ orange, medium = ● amber, info = ○ blue-teal; palette verified for deuteranopia/protanopia and ≥4.5:1 text.
- **Scale**: 4px spacing (4,8,12,16,24,32,48), radii 4/6/10, elevation 0/1/2 (border-first, shadow only for overlays), motion 120/200ms, disabled under `prefers-reduced-motion`; type 12/13/14/16/20/28 (min 12px; 14px body in dense tables).
- **Density**: comfortable / compact toggle (dispatch default compact, patrol comfortable). Targets ≥44px on touch (≥24px desktop, WCAG 2.2 AA).
- **Icons**: `lucide` (npm, bundled, tree-shaken) in both apps.
- **Voice**: Romanian everywhere, one glossary (Alertă, Eveniment→Alertă, Confirmată/Respinsă/Nouă, Dosar), times `dd.MM.yyyy HH:mm:ss` with `Europa/București (EET/EEST)` shown in header + audit; roles shown by RO label, not enum.
- **Honesty chips**: `DEMO`, `SINTETIC`, `REDACTAT (euristic)`, `FĂRĂ REDACTARE` on evidence; unfinished screens get a persistent "Demonstrativ" banner.

## 5. Design system
- `design/tokens.css` (CSS variables, `:root` light, `[data-theme=dark]`, density attrs) as single source; copied into both apps by a small check script (`scripts/check-tokens.mjs` verifies the two copies are identical — no monorepo tooling). Tailwind 4 in `frontend/` maps `@theme` to these vars; secure-pwa uses them directly. All styling in external CSS → strict CSP stays intact.
- Components (each w/ default/hover/focus/active/disabled/loading/error): Button (primary/secondary/danger/ghost/icon), Input/Textarea/Select/Checkbox/Switch with label+hint+error, OTP input, Table (sticky head, row-select, mobile→card list), PriorityBadge, StatusBadge, RedactionChip, Card, Tabs, Dialog (focus trap, Esc, restore focus, `inert` background), ConfirmDialog (for Reject/Deny/Revoke), Toast (aria-live polite, no focus steal), Banner (stale connection/demo), EmptyState, ErrorState (+retry), Skeleton, Pagination, Filter bar, CommandSearch (NL archive search), Timeline (audit history), EvidencePlayer (play/pause, frame step, speed 0.25–2×, fullscreen, scrubber with visible focus, keyboard map scoped to the player), Kbd hint, ConnectionIndicator.
- **Layout**: desktop ≥1024: left rail (icons+labels, collapsible) + top bar (search, connection, tz clock, user menu) ; tablet 640–1023: rail collapsed to icons; phone <640: bottom tab bar (Alerte, Hartă/Cameră, Căutare, Mai mult), sticky action bar on case file, safe-area insets, `100dvh`.

## 6. Wireframes (key screens)
**Queue / dashboard (desktop)**
```
┌rail┬ Dispecerat ──────────── [🔍 caută…]  ● Conectat  14:32 EET  [Operator ▾]┐
│Al. │ [Critice 2][Ridicate 5][Nesoluționate 9][Decise azi 31]   (date reale)   │
│Cam.├──────────────────────────────────────────┬───────────────────────────────┤
│Arh.│ ▲ Sens interzis  Cam. Unirii  14:31:07 ⏵ │  Previzualizare dosar          │
│Stat│ ◆ Viteză mare    Cam. Podu Roș 14:29:50  │  [clip/frame redactat]         │
│Aud.│ ● Frânare…       …                       │  Tip · Cameră · Ora · Prioritate│
│Set.│ ▌nou: 2 alerte noi ▾ (nu mută lista)     │  [Deschide dosar] [Confirmă]   │
└────┴──────────────────────────────────────────┴───────────────────────────────┘
```
**Case file**
```
← Alerte  #118 ▲ Sens interzis  Nouă      Cam. Piața Unirii · 04.11.2026 14:31 EET
┌ Dovezi ───────────────────────────┐ ┌ Decizie ───────────────┐
│ [player + frame-step + 0.25×]     │ │ (•) Confirmă ( ) Respinge│
│ [REDACTAT (euristic)] [SINTETIC?] │ │ Acțiune: [select]       │
│ filmstrip                         │ │ Notă: [______]          │
└───────────────────────────────────┘ │ [Confirmă…→dialog]      │
┌ Istoric (timeline, UTC+2) ────────┐ │ Cerere acces: unblur/export (doar dacă există original)│
```
**Archive search**: `[ camioane oprite ieri 14–18        ] [Caută]` → interpretation chips ("Interpretat: tip=oprit, 14:00–18:00" removable → re-query), results grid with redaction chip, filter drawer on phone, empty/error states.
**Cameras / map**: list+map toggle; map = self-hosted GeoJSON roads only (no tiles), markers with severity shape+label; camera status uses real heartbeat only; "Demonstrativ" banner for patrol positions (or hidden).
**Admin / audit**: filter bar (action, actor, period) · table (mobile→cards) · `Verifică integritatea` button with result banner (hash head shown) · users/invites (secure-pwa) · approvals queue split Pending/History with decision note and "Needs another approver" state.

## 7. Accessibility & responsive plan (WCAG 2.2 AA)
Contrast ≥4.5:1 text/3:1 UI both themes (tokens validated by script in tests); `:focus-visible` 2px ring offset on every control; skip link, one `<main>`, named `<nav>`, per-route `document.title` + focus to `<h1>` on navigation; full keyboard operation incl. queue (j/k, Enter) with shortcuts disable-able and scoped; dialogs trap/restore focus; live regions for toasts/new alerts (polite, never moves focus); `aria-label` on all icon buttons; table `<caption>/scope`; reduced motion; zoom to 200%/reflow at 320px; target ≥44px touch; text selection enabled; axe checks in Playwright.

## 8. Implementation steps (ordered, each shippable, gate after each)
| # | Step | Effort | Risk (security/tests) |
|---|---|---|---|
| 0 | Branch, baseline report (lint/type/test/build, bundle sizes), freeze tests | 0.5d | none |
| 1 | `tokens.css` + base styles + themes + fonts + token check; remove undefined classes in `frontend/` | 1d | low; visual only |
| 2 | Core components both apps + unit tests (RTL for secure-pwa; vitest+RTL for frontend) | 3d | low |
| 3 | **Honesty pass in `frontend/`**: demo.ts curation only under `VITE_USE_MOCKS`/explicit demo flag; real ages; remove invented patrols/users/claims; Demo/Synthetic chips | 1.5d | medium: changes visible data; keep API calls identical |
| 4 | Login (+MFA step UI in frontend, recovery code, lock-screen recovery in pwa), errors, role-based home | 1.5d | medium: auth UI; no backend/auth-code change; tests for flows |
| 5 | Shell/nav: rail, bottom tab bar, route titles, error boundary, connection indicator | 1.5d | low |
| 6 | Dashboard/queue: priority order, new-alert chip without focus steal, no layout jump, skeletons/empty/error, remove preload overlay (lazy per-clip) | 2d | medium: SSE logic |
| 7 | Case file + EvidencePlayer + ConfirmDialog, sticky mobile actions, redaction chips, no unblur when no original | 2.5d | medium: decision flow, tests per role |
| 8 | Archive search (read `?q=`, interpretation chips, states) | 1d | low |
| 9 | secure-pwa screens: alerts, approvals, audit, sessions, invite, MFA enrollment (copy/print codes), push guidance, RO copy | 3d | medium: step-up/reauth flows; keep `security.test.ts` green |
| 10 | Cameras/map (self-hosted, escaped labels), stats (real data only), rules/patrols/settings honest "demo" or hidden | 2d | low–med: CSP |
| 11 | Playwright walk: every route × role, fail on console/uncaught errors/external hosts; axe; fix stale smoke; screenshots to `docs/design/screens/`; `DESIGN_SYSTEM.md`; bundle before/after; route-level `lazy` | 2d | low |
Total ≈ 22 working days equivalent. Revert any step that turns gate red.

## 9. Open questions (recommended default in bold)
1. **Which UI is the product?** Keep both: `frontend/` for dispatch desktop, `secure-pwa/` for patrol/admin/auditor mobile; shared tokens; no merge. (Alt: converge into one app — much larger.)
2. **Map tiles/live stream vs "no external runtime resources":** drop OSM tiles → self-hosted GeoJSON map; disable webcamromania HLS by default, behind explicit `VITE_LIVE_STREAM=1`, labeled "Flux public extern (demo)" and needing gateway CSP change that I will not make.
3. **Mock-only screens (Rules, Patrols, Settings users):** **show only with an "Demonstrativ" banner in mock mode; hide in real mode.**
4. **Demo curation (hidden ids, reclassification):** **move behind explicit `VITE_DEMO_CURATION=1` (off by default)** — affects the pitch demo look; confirm.
5. **MFA UI in `frontend/`:** **build the OTP/recovery step now (inactive while backend bypasses MFA).**
6. **Dark default or system?** **System preference, dark for dispatch rooms via toggle persisted in localStorage.**

## Verification (for Phase 2)
Per step: `tsc -b`, `eslint`, vitest, `vite build` in both apps; backend tests untouched (`pytest backend` only if an API field changes — none planned). Final: Playwright walk (all routes×roles, console/external-host failures), axe, `check-tokens`, bundle size before/after, screenshots light/dark × desktop/mobile.
