// secure-pwa walk with the API stubbed in the browser: every route, light/dark, desktop/mobile,
// axe, console/uncaught errors, external requests, and the safety-critical flows (confirm dialogs, MFA enrollment).
// Usage: (cd ../secure-pwa && npm run build) && PLAYWRIGHT_BROWSERS_PATH=node_modules/.pw-browsers node e2e/pwa-walk.mjs [--shots]
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { preview } from 'vite'
import { CSP } from './csp.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
const pwaRoot = path.resolve(here, '../../secure-pwa')
const shotsDir = path.resolve(here, process.env.SHOTS_DIR ?? '../../docs/design/screens')
const SHOTS = process.argv.includes('--shots')
if (SHOTS) mkdirSync(shotsDir, { recursive: true })
process.env.PLAYWRIGHT_BROWSERS_PATH ??= path.join(here, '../node_modules/.pw-browsers')

const failures = []
const fail = (where, what) => { failures.push(`${where}: ${what}`); console.error('FAIL', where, what) }
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')
const ago = (m) => new Date(Date.now() - m * 60000).toISOString()
const ME = (role = 'tenant_admin') => ({ id: 'u1', email: 'admin@example.test', display_name: 'Admin Test', role, tenant_id: 't', tenant_name: 'Tenant', permissions: ['alerts:read', 'alerts:decide', 'alerts:assign', 'retention:manage', 'users:manage', 'approvals:request', 'approvals:decide', 'audit:read', 'sessions:manage_all', 'alerts:plate_search'], session_id: 's', mfa_fresh_until: ago(-5) })
const ALERT = (id, priority, status = 'new') => ({ id, camera_id: 'c', camera_name: 'Camera A', priority, status, event_type: 'wrong_way', description: `Sens interzis ${id}`, detected_at: ago(id * 7), plate_masked: 'IS 12 ***', assigned_to: null, decided_by: null, decided_at: null, evidence_ids: ['e1'] })

async function stub(page, state) {
  const json = (route, body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  await page.route('**/api/**', (route) => {
    const u = new URL(route.request().url()); const p = u.pathname; const m = route.request().method()
    state.calls.push(`${m} ${p}`)
    if (p === '/api/auth/csrf') return json(route, { csrf_token: 'tok' })
    if (p === '/api/auth/me') return state.authed ? json(route, ME()) : json(route, { detail: 'no' }, 401)
    if (p === '/api/auth/refresh') return route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"no"}' })
    if (p === '/api/auth/login') return json(route, { enrollment_required: state.enroll })
    if (p === '/api/auth/mfa/verify') { state.authed = true; return route.fulfill({ status: 204 }) }
    if (p === '/api/auth/mfa/enroll/start') return json(route, { otpauth_uri: 'otpauth://x', qr_svg_data_uri: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4=', secret: 'ABCDEFGH' })
    if (p === '/api/auth/mfa/enroll/confirm') return json(route, { recovery_codes: ['aaaa-1111', 'bbbb-2222', 'cccc-3333', 'dddd-4444'] })
    if (p === '/api/alerts') return json(route, [ALERT(1, 'critical'), ALERT(2, 'high'), ALERT(3, 'medium', 'confirmed'), ALERT(4, 'info')])
    if (/^\/api\/alerts\/\d+$/.test(p)) return json(route, ALERT(1, 'critical'))
    if (/^\/api\/alerts\/\d+\/(confirm|reject)$/.test(p)) return json(route, ALERT(1, 'critical', 'rejected'))
    if (p === '/api/evidence') return json(route, [{ id: 'e1', alert_id: '1', kind: 'keyframe', content_type: 'image/png', size_bytes: 10, sha256: 'a'.repeat(64), created_at: ago(5), redaction: 'full', has_original: true, unblur_grant_expires_at: null, plate: null }])
    if (p === '/api/evidence/e1/access') return json(route, { url: '/media/e1.png', expires_at: ago(-1) })
    if (p === '/api/approvals') return json(route, [
      { id: 'a1', kind: 'unblur', resource_type: 'evidence', resource_id: 'e1', requester_id: 'u2', justification: 'Verificare caz 123 pentru identificarea vehiculului', case_reference: 'C-123', status: 'pending', decided_by: null, decided_at: null, decision_note: null, grant_expires_at: null, grant_active: false, created_at: ago(9) },
      { id: 'a2', kind: 'export', resource_type: 'evidence', resource_id: 'e1', requester_id: 'u1', justification: 'Cerere proprie în așteptare, motiv suficient', case_reference: 'C-124', status: 'pending', decided_by: null, decided_at: null, decision_note: null, grant_expires_at: null, grant_active: false, created_at: ago(8) },
      { id: 'a3', kind: 'unblur', resource_type: 'evidence', resource_id: 'e1', requester_id: 'u2', justification: 'Caz închis, cerere refuzată anterior', case_reference: 'C-100', status: 'denied', decided_by: 'u1', decided_at: ago(60), decision_note: null, grant_expires_at: null, grant_active: false, created_at: ago(120) },
    ])
    if (/^\/api\/approvals\/\w+\/(approve|deny|revoke)$/.test(p)) return json(route, {})
    if (p === '/api/audit/chain') return json(route, Array.from({ length: 5 }, (_, i) => ({ seq: i + 1, ts: ago(50 - i), actor_id: 'u1abcdef12', action: i % 2 ? 'alert.confirm' : 'auth.login', resource_type: 'alert', resource_id: 'abcdef1234', ip: '10.0.0.1', details: { ok: true }, prev_hash: 'p', entry_hash: 'h'.repeat(64) })))
    if (p === '/api/audit/verify') return json(route, { ok: true, checked: 5, first_broken_seq: null, reason: null, head_hash: 'f'.repeat(64) })
    if (p === '/api/retention' && m === 'GET') return json(route, { days: { keyframe: 30, clip: 30, camera_video: 7, confirmed_case: 365 }, defaults: { keyframe: 30, clip: 30, camera_video: 7, confirmed_case: 365 }, due_now: 3, held_skipped: 1 })
    if (p === '/api/users' && m === 'GET') return json(route, [{ id: 'u1', email: 'admin@example.test', display_name: 'Admin Test', role: 'tenant_admin', is_active: true }, { id: 'u2', email: 'op@example.test', display_name: 'Operator Test', role: 'operator', is_active: true }])
    if (p === '/api/patrols') return json(route, [{ id: 'p1', display_name: 'Patrulă 1', open_assignments: 2 }])
    if (p === '/api/auth/reset/inspect') return json(route, { email: 'op@example.test', reset_mfa: true, expires_at: ago(-30) })
    if (p === '/api/sessions') return json(route, [{ id: 's1', user_id: 'u1', created_at: ago(30), last_seen_at: ago(1), expires_at: ago(-60), ip: '10.0.0.1', user_agent: 'Chrome test', revoked_at: null, revoked_reason: null, current: true }, { id: 's2', user_id: 'u1', created_at: ago(300), last_seen_at: ago(100), expires_at: ago(-60), ip: '10.0.0.2', user_agent: 'Phone test', revoked_at: null, revoked_reason: null, current: false }])
    if (p === '/api/users') return json(route, [{ id: 'u1', email: 'admin@example.test', display_name: 'Admin', role: 'tenant_admin', is_active: true, mfa_enabled: true }])
    if (p === '/api/push/subscriptions') return route.fulfill({ status: 204 })
    return json(route, { detail: `unstubbed ${p}` }, 404)
  })
  await page.route('**/media/**', (route) => route.fulfill({ status: 200, contentType: 'image/png', body: PNG }))
}

function watch(page, tag, origin) {
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    const t = m.text()
    if (/status of 40[14]|Failed to load resource.*(401|404)/.test(t)) return // deliberate stub answers (anonymous probe, refresh)
    fail(tag, `console.error: ${t}`)
  })
  page.on('pageerror', (e) => fail(tag, `uncaught: ${e.message}`))
  page.on('request', (r) => { const u = r.url(); if (!u.startsWith('data:') && !u.startsWith('blob:') && new URL(u).origin !== origin) fail(tag, `external request ${u}`) })
}
const axe = async (page, tag) => { for (const v of (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()).violations) fail(tag, `axe ${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0].target.join(' ')}`) }
const shot = async (page, name) => { if (SHOTS) await page.screenshot({ path: path.join(shotsDir, `${name}.png`) }) }

const srv = await preview({ root: pwaRoot, preview: { port: 0, host: '127.0.0.1', headers: { 'Content-Security-Policy': CSP } }, build: { outDir: 'dist' } })
const origin = srv.resolvedUrls.local[0].replace(/\/$/, '')
const browser = await chromium.launch()
const VPS = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844 } }
try {
  for (const [vp, size] of Object.entries(VPS)) for (const theme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: size, colorScheme: theme, reducedMotion: 'reduce', serviceWorkers: 'block' })
    const page = await ctx.newPage(); const state = { authed: true, enroll: false, calls: [] }
    const tag0 = `pwa/${vp}/${theme}`
    watch(page, tag0, origin); await stub(page, state)
    for (const r of [['/alerts', 'alerts'], ['/alerts/1', 'case'], ['/approvals', 'approvals'], ['/audit', 'audit'], ['/sessions', 'sessions'], ['/admin', 'admin']]) {
      const tag = `${tag0}${r[0]}`
      await page.goto(origin + r[0], { waitUntil: 'networkidle' }); await page.waitForTimeout(300)
      if ((await page.locator('h1').count()) !== 1) fail(tag, `expected 1 h1, found ${await page.locator('h1').count()}`)
      if ((await page.locator('main').count()) !== 1) fail(tag, 'expected exactly 1 main')
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) fail(tag, 'horizontal overflow')
      await axe(page, tag); await shot(page, `pwa-${r[1]}-${vp}-${theme}`)
    }
    await ctx.close()
  }

  // Safety-critical flows (desktop, dark)
  {
    const ctx = await browser.newContext({ viewport: VPS.desktop, serviceWorkers: 'block' })
    const page = await ctx.newPage(); const state = { authed: true, enroll: false, calls: [] }
    watch(page, 'pwa/flows', origin); await stub(page, state)
    await page.goto(`${origin}/alerts/1`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Respinge', exact: true }).click()
    if (!(await page.getByRole('dialog').isVisible())) fail('pwa/reject', 'no confirm dialog')
    if (state.calls.some((c) => c.endsWith('/reject'))) fail('pwa/reject', 'reject sent before confirmation')
    await page.keyboard.press('Escape')
    if (await page.getByRole('dialog').isVisible()) fail('pwa/reject', 'Esc did not close dialog')
    if (state.calls.some((c) => c.endsWith('/reject'))) fail('pwa/reject', 'reject sent by cancelling')
    await page.getByRole('button', { name: 'Respinge', exact: true }).click()
    await page.getByRole('button', { name: 'Respinge alerta' }).click()
    await page.waitForTimeout(300)
    if (!state.calls.includes('POST /api/alerts/1/reject')) fail('pwa/reject', 'confirmed reject was not sent')

    await page.goto(`${origin}/approvals`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Refuză' }).first().click()
    if (!(await page.getByRole('dialog').isVisible())) fail('pwa/deny', 'no confirm dialog for deny')
    await page.getByRole('button', { name: 'Anulează' }).click()
    if (state.calls.some((c) => c.endsWith('/deny'))) fail('pwa/deny', 'deny sent by cancelling')
    if (!(await page.getByText('Necesită un alt administrator').isVisible())) fail('pwa/approvals', 'own request shows approve/deny instead of "needs another admin"')
    await page.getByRole('button', { name: /Istoric/ }).click()
    if (!(await page.getByText('Refuzată').first().isVisible())) fail('pwa/approvals', 'history tab missing denied request')
    await ctx.close()
  }

  // Login with MFA enrollment: recovery codes must be acknowledged before continuing
  {
    const ctx = await browser.newContext({ viewport: VPS.desktop, serviceWorkers: 'block' })
    const page = await ctx.newPage(); const state = { authed: false, enroll: true, calls: [] }
    watch(page, 'pwa/enroll', origin); await stub(page, state)
    await page.goto(`${origin}/login`, { waitUntil: 'networkidle' })
    await page.getByLabel('E-mail').fill('admin@example.test'); await page.getByLabel('Parolă').fill('x')
    await page.getByRole('button', { name: 'Continuă' }).click()
    await page.getByLabel('Cod din aplicație').fill('123456')
    await axe(page, 'pwa/enroll-step'); await shot(page, 'pwa-enroll-desktop')
    await page.getByRole('button', { name: 'Activează' }).click()
    const cont = page.getByRole('button', { name: 'Continuă' })
    await cont.waitFor()
    if (!(await cont.isDisabled())) fail('pwa/enroll', 'continue enabled before recovery codes were acknowledged')
    await axe(page, 'pwa/recovery-codes'); await shot(page, 'pwa-recovery-codes-desktop')
    await page.getByLabel(/Am păstrat codurile/).check()
    state.authed = true
    await cont.click(); await page.waitForURL('**/alerts')
    await ctx.close()
  }
} finally { await browser.close(); await srv.close() }
console.log(`pwa walk: ${failures.length} failure(s)`)
if (failures.length) { console.log([...new Set(failures)].slice(0, 60).join('\n')); process.exit(1) }
