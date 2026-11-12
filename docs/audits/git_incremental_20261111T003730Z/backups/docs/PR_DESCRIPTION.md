# PR draft: release/ready → main (NOT opened; local only)

## Summary
Brings `main` to an honest, security-correct state and adds the missing product pieces, on top of the `design/wow` redesign. Read `docs/FINAL_STATUS.md` for the gates that were run and, just as important, what was **not** run (GitHub CI, Docker, Railway, any model/torch code path).

**Security / honesty (P0)**
* Mandatory MFA restored (the password-only demo login had replaced it for every account); demo exemption exists but is off by default, refused in production.
* No default credentials (`parola` removed); `demo-accounts` refuses production and prints a one-time password.
* Pipeline evidence is stored once: `has_original=false`, unblur/export-original refused (`409`), redaction labelled truthfully (`full|heads_only|off|unknown`), redaction **on** by default, off needs explicit confirmation.
* Deploy workflow is manual and requires green CI for the commit; evidence-storage warning at start-up.
* Strict CSP on the Railway gateway; idle (30 min) and absolute (12 h) session limits enforced (they were configured but unused).

**Pipeline / ML**
* Low-fps rule mode and capabilities computed from the measured frame rate; new rules (near-miss, object on roadway, stationary-after-impact crash); alert gate; idempotent ingestion; live reader/supervisor with backoff and stall detection; consent gate for public streams.
* Model integration kit (registry, install/activate/rollback, held-out evaluation with leakage refusal, manifests, dataset checker), calibration tool, labelling guide, data card.

**Product**
* Four-eyes account recovery, password change, session revocation, break-glass CLI · retention with legal hold and audited purge · patrol workflow · camera edit/disable · measured response times · UI for these.

**Operations**
* Readiness, token-guarded metrics, per-tenant ops status, verified backup/restore scripts, latency measurement, one-command synthetic demo, OPERATIONS/LIMITS/SETUP/PRESENTATION docs; README/HANDOFF/API/SECURITY corrected.

## Migrations
0007 evidence.has_original · 0008 rules/idempotency/camera status · 0009 account recovery · 0010 retention · 0011 patrol + first-view · 0012 readiness grant. Take a backup first (docs/OPERATIONS.md).

## Test plan (as run locally)
Backend 392 passed (PostgreSQL 18.6) · root 128 passed / 2 skipped · frontend 11/11 · secure-pwa 9/9 · both Playwright walks 0 failures under the strict CSP. See docs/FINAL_STATUS.md.

## Risks / reviewer attention
* Large diff (design/wow ≈ 230 files of it). Review order: backend migrations and auth → pipeline modules → UI.
* `roadsentinel/pipeline.py` was refactored and **not executed** (no torch here): run it once on a sample clip before relying on it.
* CI on PostgreSQL 16 and the Docker stack have never run on this branch.
* Nothing here changes who may use a public webcam: the Iași camera stays off until written permission is recorded.

## Commits
```
140552a docs: final status, PR description draft, progress
2878747 style: prettier for offline page
83c4c44 fix(pwa): Romanian offline page, manifest colours match the new theme
be48d48 test: real route discovery for the authorization matrix (the first version silently saw 3 routes), hostile-input test over every state-changing route
3f07828 docs: README, HANDOFF and SETUP match the code; old Romanian handoff archived
4fd3ffe docs: operations, limits, presentation notes
3bf7442 docs: API.md and SECURITY.md match the implemented behaviour
e422f59 fix(auth): enforce idle timeout (30 min) and absolute session lifetime (12 h) on the server
2faaf03 feat(demo): one-command local demo (strict or demo profile), seeded data marked synthetic end to end
2a81a4a ops: backup/restore scripts (verified on a local Postgres), latency measurement tool
8be10b9 feat(ops): readiness probe, token-guarded Prometheus metrics, per-tenant ops status; authorization matrix and cross-tenant probes over the whole API
7418c3e feat(ui): measured response times on the statistics page (n and window shown), relabel the client-side estimate
a7caa87 feat(ui): account recovery page, admin (retention, recovery requests, own password), patrol panel in the secure PWA
221c02e style: black/ruff clean for camera and patrol changes
a182166 feat(cameras): audited camera edit/disable (slug immutable)
7c2d7ca feat(patrol,stats): patrol status workflow (assignee only, forward only), real patrol list, first-view tracking, response-time statistics from timestamps
d4144f9 feat(retention): per-kind policy, legal hold, dry-run, audited purge job (CLI + API), purged evidence returns 410
413d513 docs: progress after phase 2 and account recovery
d363aa3 feat(auth): four-eyes account recovery (request, approve, single-use token), own password change, session revocation, break-glass CLI
258f21f feat(live): public streams stay OFF until the owner's permission is documented; Iasi camera uses low-fps mode and reports what it cannot do
2113de5 feat(calibration,data): homography from measured points, validation against known speeds (speeds stay 'orientativ' until validated); dataset checker, labelling guide, data card template
44c5518 feat(eval): held-out evaluation harness with leakage check, per-class/camera/condition metrics, baseline comparison, alerts-per-hour with human review; manifest builder; runbooks
1a2fd71 feat(models): registry, install/activate/rollback kit with sha256, class-map check, smoke test, hash-chained change log; model identity in every alert; no silent stock fallback
03729c0 feat(ui): new alert types, low-confidence and approximate-speed markers, per-camera measured fps and rules that cannot run
d228c0d feat(live): reconnect with backoff, stall watchdog, bounded retrying uploads, alert gate (dedupe/cooldown/rate limit), measured-fps capabilities in the heartbeat, python supervisor
b390c46 feat(rules,api): low-fps sampling mode, rule capabilities, near_miss and object_on_roadway, stationary-after-impact crash check; idempotent ingestion and heartbeat rate status
a2ac418 docs: progress after phase 1
94576af docs: dependency plan; mark web/ and roadsentinel/server.py deprecated
75e7456 security(gateway): strictest CSP on the Railway gateway (no unsafe-inline, tiles or webcam host), non-root + healthcheck; walks run under the strict CSP
c87799d ci: police UI, pipeline, repo-check jobs; docs link and secret scanners; archive AI prompt files
2cfeb7a feat(ui): honest redaction/no-original states, MFA step comment, no demo password literal
72c3283 Merge design/wow: Night Watch redesign into release/ready
04e0895 ci(deploy): manual only and gated on green CI for the commit; warn when evidence storage is ephemeral
fa034ad fix(pipeline): redaction on by default, off needs explicit confirmation and is reported as 'off'
6c4296e fix(evidence): record has_original, refuse unblur/export when no distinct original exists
2f0ccf5 chore(security): local secret scanner (file:line only), narrow gitleaks allowlist, pre-commit helper
7e6d7ea fix(security): no default credentials; demo-accounts refuses production, generates a one-time password
9a4da96 docs: implementation progress and Linux local-dev notes
dc2e7dc fix(auth): restore mandatory MFA; demo exemption is off by default and refused in production
266552f docs(design): WOW polish pass, screens-wow, DESIGN_SYSTEM v2, PROGRESS with gate numbers; remove recharts
ef27851 feat(design): dashboard command center + map, cinematic evidence viewer, SVG stats, cameras/archive/audit polish, secure-pwa Night Watch skin
6678def feat(design): Night Watch direction, tokens v2, core components v2, cinematic login hero, command palette, calm mode
724ab16 docs(design): PROGRESS with final gate numbers and open items
15ae318 docs(design): DESIGN_SYSTEM, PROGRESS, walk screenshots; player copy/filmstrip fix
a139a7a feat(secure-pwa): Romanian UI on shared tokens, confirm dialogs for decisions/approvals/revocations, honest evidence copy, MFA enrollment codes, audit filters
c9630ef test(frontend): Playwright walk (routes x roles x themes x viewports, axe, external-request guard) and a11y fixes
c20462e feat(frontend): self-hosted schematic map, honest cameras/stats/audit, demo banners
55f6bea feat(frontend): archive search with deep link, states, redaction chips
e13d4dc feat(frontend): queue/dashboard and case file rewrite, ConfirmDialog flow, accessible EvidencePlayer
bfc3350 feat(frontend): dialogs, form fields, login + inactive MFA step (OTP/recovery)
54c5726 feat(frontend): responsive shell, connection indicator, route titles, lazy routes (main bundle 1269 -> 399 kB)
26e3bd6 feat(frontend): honesty pass — curation behind VITE_DEMO_CURATION, no invented patrols/users/claims
3ecf92e feat(design): shared tokens, light/dark themes, core badges/chips/states in frontend
12199eb fix(frontend): clear the 8 existing lint errors, no behavior change
07c13a6 docs(design): DESIGN_PLAN and baseline checks
```

## Diff stat (excluding design screenshots)
```
 223 files changed, 14073 insertions(+), 4749 deletions(-)
```
