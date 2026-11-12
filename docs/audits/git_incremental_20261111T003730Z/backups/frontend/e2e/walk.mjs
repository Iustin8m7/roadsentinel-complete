// Route x role walk. Fails on console errors, uncaught page errors, requests to foreign hosts and axe violations.
// Mock mode (VITE_USE_MOCKS=1 build): admin + operator across every route.
// Real mode (normal build, /api stubbed in the browser): operator list/detail/archive/cameras/stats/audit + MFA step.
// Usage: PLAYWRIGHT_BROWSERS_PATH=node_modules/.pw-browsers node e2e/walk.mjs [--shots]
import { spawnSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { preview } from 'vite'
import { CSP } from './csp.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const romanianRegistry = JSON.parse(readFileSync(path.resolve(root, '../cameras/romanian-source-registry.json'), 'utf8'))
const camelize = (value) => value.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
const discoveryFixture = romanianRegistry.sources.map((row) => Object.fromEntries(Object.entries(row).map(([key, value]) => [camelize(key), value])))
const shotsDir = path.resolve(root, process.env.SHOTS_DIR ?? '../docs/design/screens')
const SHOTS = process.argv.includes('--shots')
if (SHOTS) mkdirSync(shotsDir, { recursive: true })
process.env.PLAYWRIGHT_BROWSERS_PATH ??= path.join(root, 'node_modules/.pw-browsers')

function build(outDir, env) {
  const r = spawnSync('npx', ['vite', 'build', '--outDir', outDir, '--emptyOutDir'], { cwd: root, env: { ...process.env, ...env }, stdio: 'pipe' })
  if (r.status !== 0) throw new Error(`build failed: ${r.stderr}`)
}

const failures = []
const fail = (where, what) => { failures.push(`${where}: ${what}`); console.error('FAIL', where, what) }
const archiveOnly = process.argv.includes('--archive-only')
const camerasOnly = process.argv.includes('--cameras-only')
const ilisestiPlayer = process.argv.includes('--ilisesti-player')

// 1x1 PNG
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')
const NOW = Date.now()
const ev = (id, type, priority, cam, ageMin, extra = {}) => ({
  id, camera_id: cam, camera_name: cam, location: 'Iași', type, priority, occurred_at: new Date(NOW - ageMin * 60000).toISOString(), video_t: 3,
  track_id: id, object_class: 'car', speed_kmh: type === 'very_high_speed' ? 132 : null, rule: `Regulă ${type}`, details: {},
  keyframe_url: `/media/k${id}.png`, clip_url: null, vlm_status: 'unavailable', vlm_text: null, status: 'new', action: null, redaction: 'full', ...extra,
})
const EVENTS = [
  ev(1, 'wrong_way', 'critical', 'cam-a', 2),
  ev(2, 'very_high_speed', 'high', 'cam-a', 9),
  ev(3, 'hard_braking', 'medium', 'cam-b', 30, { redaction: 'heads_only' }),
  ev(4, 'congestion', 'info', 'cam-b', 90, { status: 'confirmed', redaction: undefined }),
]

async function stubApi(page, { mfa = false, role = 'operator' } = {}) {
  const json = (route, body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  let loggedIn = false
  let workerState = 'STOPPED'
  const savedSearches = []
  const cameras = [
    { id: 'cam-a', uuid: 'uuid-cam-a', name: 'Camera A', location: 'Str. A', timezone: 'Europe/Bucharest', video_url: null, latitude: 47.16, longitude: 27.58, is_active: true, last_seen_at: new Date().toISOString() },
    { id: 'cam-b', uuid: 'uuid-cam-b', name: 'Camera B', location: null, timezone: 'Europe/Bucharest', video_url: null, latitude: null, longitude: null, is_active: true, last_seen_at: null },
  ]
  await page.route('**/api/**', (route) => {
    const u = new URL(route.request().url())
    const p = u.pathname
    const m = route.request().method()
    if (p === '/api/auth/csrf') return route.fulfill({ status: 204 })
    if (p === '/api/me') return loggedIn ? json(route, { operator: 'operator', auth_required: true }) : json(route, { operator: null, auth_required: true }, 200)
    if (p === '/api/login') { if (!mfa) loggedIn = true; return json(route, { operator: mfa ? null : 'operator', auth_required: true, mfa_required: mfa }) }
    if (p === '/api/auth/mfa/verify') { loggedIn = true; return route.fulfill({ status: 204 }) }
    if (p === '/api/auth/me') return json(route, {
      role: role === 'admin' ? 'tenant_admin' : 'operator',
      permissions: role === 'admin' ? ['cameras:manage'] : ['alerts:read'],
    })
    if (p === '/api/auth/refresh') return route.fulfill({ status: 204 })
    if (p === '/api/logout') { loggedIn = false; return route.fulfill({ status: 204 }) }
    if (p === '/api/stats/response') return json(route, { alerts: 4, never_viewed: 1, rejection_rate: 0, rejection_rate_n: 1, time_to_first_view: { n: 3, median_s: 22, p90_s: 61 }, time_to_decision: { n: 1, median_s: 140, p90_s: 140 } })
    if (p === '/api/events' && m === 'GET') return json(route, EVENTS)
    const one = p.match(/^\/api\/events\/(\d+)$/)
    if (one) return json(route, { ...EVENTS.find((e) => String(e.id) === one[1]), audit: [] })
    if (p.endsWith('/view')) return json(route, {})
    if (p.endsWith('/decision')) return json(route, { ...EVENTS[0], status: 'confirmed', audit: [{ id: 9, event_id: 1, actor: 'operator', action: 'confirmed', note: null, at: new Date().toISOString() }] })
    if (p === '/api/cameras' && m === 'GET') return json(route, cameras)
    if (p === '/api/cameras' && m === 'POST') {
      const body = route.request().postDataJSON()
      if (cameras.some((camera) => camera.id === body.slug)) return json(route, { detail: 'duplicate slug' }, 409)
      const camera = { id: body.slug, uuid: `uuid-${body.slug}`, slug: body.slug, name: body.name, location: body.location, timezone: body.timezone, video_url: null, latitude: null, longitude: null, is_active: true, last_seen_at: null }
      cameras.push(camera)
      return json(route, camera, 201)
    }
    if (p === '/api/cameras/discovery' && m === 'GET') return json(route, discoveryFixture)
    const workerControl = p.match(/^\/api\/cameras\/([^/]+)\/worker(?:\/(start|stop|restart))?$/)
    if (workerControl) {
      const action = workerControl[2]
      if (m === 'POST' && action) workerState = action === 'stop' ? 'STOPPED' : action === 'restart' ? 'RUNNING' : 'STARTING'
      return json(route, { state: workerState, desired_state: workerState === 'STOPPED' ? 'STOPPED' : 'RUNNING', pid: workerState === 'STOPPED' ? null : 9001, config_version: 'fixture-config' })
    }
    const cameraEdit = p.match(/^\/api\/cameras\/([^/]+)$/)
    if (cameraEdit && m === 'PATCH') {
      const camera = cameras.find((c) => c.uuid === cameraEdit[1])
      if (!camera) return json(route, { detail: 'Not found' }, 404)
      Object.assign(camera, route.request().postDataJSON())
      return json(route, { id: camera.uuid, ...camera })
    }
    if (p === '/api/stats') return json(route, { total: 4, by_priority: { critical: 1, high: 1, medium: 1, info: 1 }, by_status: { new: 3, confirmed: 1 }, by_type: { wrong_way: 1 }, vlm_available: false })
    if (p === '/api/meta') return json(route, { event_types: { wrong_way: { label: 'Sens interzis', priority: 'critical' }, very_high_speed: { label: 'Viteză foarte mare', priority: 'high' }, hard_braking: { label: 'Frânare bruscă', priority: 'medium' }, congestion: { label: 'Aglomerare', priority: 'info' } }, actions: { monitor: 'Monitorizare', dispatch_patrol: 'Trimitere patrulă' } })
    if (p === '/api/audit') return json(route, [{ id: 1, event_id: 1, actor: 'operator', action: 'viewed', note: null, at: new Date().toISOString() }])
    if (p === '/api/saved-searches' && m === 'GET') return json(route, savedSearches)
    if (p === '/api/saved-searches' && m === 'POST') {
      const body = route.request().postDataJSON()
      const item = { id: 'saved-1', name: body.name, created_at: new Date().toISOString() }
      savedSearches.push(item)
      return json(route, item, 201)
    }
    const savedRun = p.match(/^\/api\/saved-searches\/([^/]+)\/run$/)
    if (savedRun && m === 'POST') {
      const body = route.request().postDataJSON() ?? {}
      return json(route, {
        filter: { explanation: 'tip=viteză' },
        results: [body.cursor ? EVENTS[0] : EVENTS[1]],
        next_cursor: body.cursor ? null : 'cursor.saved.page2',
      })
    }
    const savedDelete = p.match(/^\/api\/saved-searches\/([^/]+)$/)
    if (savedDelete && m === 'DELETE') {
      const index = savedSearches.findIndex((item) => item.id === savedDelete[1])
      if (index >= 0) savedSearches.splice(index, 1)
      return route.fulfill({ status: 204 })
    }
    if (p === '/api/search') {
      const body = route.request().postDataJSON() ?? {}
      return json(route, {
        filter: { explanation: 'tip=sens interzis' },
        results: [body.cursor ? EVENTS[1] : EVENTS[0]],
        next_cursor: body.cursor ? null : 'cursor.query.page2',
      })
    }
    if (p === '/api/stream') return route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': ok\n\n' })
    return json(route, { detail: `unstubbed ${p}` }, 404)
  })
  await page.route('**/media/**', (route) => route.fulfill({ status: 200, contentType: 'image/png', body: PNG }))
}

function watch(page, tag, origin) {
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    const t = m.text()
    // EventSource reconnect noise of the stubbed stream and the intentional 404 of unstubbed probes are not app errors
    if (/EventSource|\/api\/stream|net::ERR_ABORTED/.test(t)) return
    fail(tag, `console.error: ${t}`)
  })
  page.on('pageerror', (e) => fail(tag, `uncaught: ${e.message}`))
  page.on('request', (r) => {
    const u = r.url()
    if (u.startsWith('data:') || u.startsWith('blob:')) return
    if (new URL(u).origin !== origin && !(ilisestiPlayer && new URL(u).origin === 'https://webcamromania.ro')) fail(tag, `external request ${u}`)
  })
}

async function axe(page, tag) {
  const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
  for (const v of res.violations) fail(tag, `axe ${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0].target.join(' ')}`)
}

async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: path.join(shotsDir, `${name}.png`), fullPage: name.includes('cameras') })
}

const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } }
const THEMES = ['light', 'dark']

async function walkRoutes(browser, origin, mode, routes, loginFn, role) {
  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    for (const theme of THEMES) {
      const ctx = await browser.newContext({ viewport: vp, colorScheme: theme, reducedMotion: 'reduce' })
      const page = await ctx.newPage()
      const tag0 = `${mode}/${role}/${vpName}/${theme}`
      watch(page, tag0, origin)
      if (mode === 'real') await stubApi(page)
      await page.goto(`${origin}/login`)
      await loginFn(page)
      const selectedRoutes = archiveOnly ? routes.filter((r) => r.search) : routes
      for (const r of selectedRoutes) {
        const tag = `${tag0}${r.path}`
        await page.goto(origin + r.path, { waitUntil: 'networkidle' }).catch(() => {})
        if (r.search) {
          const searchInput = page.getByLabel('Ce căutați?')
          if (!(await searchInput.count())) {
            fail(tag, `archive search input missing at ${page.url()}: ${(await page.locator('body').innerText()).slice(0, 300)}`)
          } else {
            await searchInput.fill(r.search)
          }
          if (!(await searchInput.count())) continue
          await page.getByRole('button', { name: 'Caută' }).click()
          await page.waitForTimeout(100)
          if (mode === 'real') {
            await page.getByRole('button', { name: 'Încarcă rezultatele următoare' }).click()
            const queryCount = page.locator('p[role="status"]')
            await queryCount.filter({ hasText: '2 rezultate' }).waitFor({ timeout: 3000 }).catch(async () => fail(tag, `query cursor did not append the next page (${await queryCount.innerText()})`))
            await page.getByLabel('Numele căutării').fill('Saved browser search')
            await page.getByRole('button', { name: 'Salvează filtrele curente' }).click()
            const saved = page.getByRole('button', { name: 'Saved browser search', exact: true })
            await saved.waitFor()
            await saved.click()
            await page.getByRole('button', { name: 'Încarcă rezultatele următoare' }).click()
            const savedCount = page.locator('p[role="status"]')
            await savedCount.filter({ hasText: '2 rezultate' }).waitFor({ timeout: 3000 }).catch(async () => fail(tag, `saved-search cursor did not append the next page (${await savedCount.innerText()})`))
            page.once('dialog', (dialog) => dialog.accept())
            await page.getByRole('button', { name: 'Șterge căutarea: Saved browser search' }).click()
          }
        }
        await page.waitForTimeout(r.wait ?? 400)
        if (r.path === '/app/camere' && mode === 'real') {
          const catalog = page.getByRole('heading', { name: 'Camere din România' })
          await catalog.waitFor({ timeout: 5000 }).catch(() => fail(tag, 'Romanian camera experience did not load'))
          await page.getByText('35 intrări', { exact: false }).waitFor({ timeout: 5000 }).catch(() => fail(tag, 'authenticated discovery fixture did not show all 35 entries'))
          if (!(await page.getByRole('link', { name: 'Pagina operatorului' }).count())) fail(tag, 'official provider launch action missing')
          const cameraSearch = page.getByLabel('Caută camere românești')
          if (!(await cameraSearch.count())) fail(tag, 'camera search control missing')
          await cameraSearch.fill('Cluj')
          await page.getByLabel('Lista camerelor').getByRole('button', { name: /Piața Unirii/ }).first().click()
          if (!page.url().includes('camera=RO-CJ-MUNI-001')) fail(tag, 'camera selection did not write its detail deep link')
          await cameraSearch.fill('')
        }
        const h1 = await page.locator('h1').count()
        if (h1 !== 1) fail(tag, `expected exactly 1 <h1>, found ${h1}`)
        const mains = await page.locator('main').count()
        if (mains !== 1) fail(tag, `expected exactly 1 <main>, found ${mains}`)
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
        if (overflow) fail(tag, 'horizontal page overflow')
        if (!(await page.title()).includes('RoadSentinel')) fail(tag, `bad title "${await page.title()}"`)
        await axe(page, tag)
        if (r.path === '/app/camere' && mode === 'real') await page.locator('#main').evaluate((el) => el.scrollTo({ top: 380 }))
        if (r.shot) await shot(page, `${mode}-${role}-${r.shot}-${vpName}-${theme}`)
      }
      await ctx.close()
    }
  }
}

const mockLogin = (user) => async (page) => {
  await page.getByLabel('Utilizator').fill(user)
  await page.getByLabel('Parolă').fill('mock-only-demo')
  await page.getByRole('button', { name: 'Intră' }).click()
  await page.waitForURL('**/app')
}
const realLogin = async (page) => {
  await page.getByLabel('Utilizator').fill('operator')
  await page.getByLabel('Parolă').fill('x')
  await page.getByRole('button', { name: 'Intră' }).click()
  await page.waitForURL('**/app')
}

const MOCK_ROUTES = [
  { path: '/app', shot: 'queue' }, { path: '/app/alerte/RS-2026-4101', shot: 'case', wait: 800 }, { path: '/app/camere', shot: 'cameras' },
  { path: '/app/arhiva', search: 'viteză', shot: 'archive' }, { path: '/app/statistici', shot: 'stats', wait: 800 }, { path: '/app/audit', shot: 'audit' },
  { path: '/app/patrule' }, { path: '/app/reguli' }, { path: '/app/setari' },
]
const REAL_ROUTES = [
  { path: '/app', shot: 'queue' }, { path: '/app/alerte/1', shot: 'case', wait: 800 }, { path: '/app/camere', shot: 'cameras' },
  { path: '/app/arhiva', search: 'sens', shot: 'archive' }, { path: '/app/statistici', shot: 'stats', wait: 800 }, { path: '/app/audit' },
]

const t0 = Date.now()
build('dist-mock', { VITE_USE_MOCKS: '1' })
// Deliberately set the demo curation flag in real mode: fixture-only filtering must remain off.
build('dist-real', { VITE_DEMO_CURATION: '1' })
const browser = await chromium.launch()
const servers = []
async function serve(dir) {
  const s = await preview({ root, preview: { port: 0, host: '127.0.0.1', strictPort: false, headers: { 'Content-Security-Policy': CSP } }, build: { outDir: dir } })
  servers.push(s)
  return s.resolvedUrls.local[0].replace(/\/$/, '')
}
try {
  if (camerasOnly) {
    const realOrigin = await serve('dist-real')
    await walkRoutes(browser, realOrigin, 'real', REAL_ROUTES.filter((r) => r.path === '/app/camere'), realLogin, 'operator')
    const context = await browser.newContext({ viewport: VIEWPORTS.desktop })
    const page = await context.newPage()
    watch(page, 'real/admin/worker-controls-fixture', realOrigin)
    await stubApi(page, { role: 'admin' })
    await page.goto(`${realOrigin}/login`)
    await realLogin(page)
    await page.goto(`${realOrigin}/app/camere`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Adaugă cameră' }).click()
    const createDialog = page.getByRole('dialog')
    await createDialog.getByLabel('Nume cameră').fill('Owned local camera')
    await createDialog.getByLabel('ID cameră (slug)').fill('local-uvc-camera')
    await createDialog.getByLabel('Locație / drum').fill('Laborator')
    await createDialog.getByRole('button', { name: 'Adaugă camera' }).click()
    await page.getByRole('heading', { name: 'Owned local camera' }).waitFor()
    const config = page.getByLabel('Config local cameras/*.yaml').first()
    await config.fill('local-uvc.yaml')
    await page.getByRole('button', { name: 'Start' }).first().click()
    await page.getByText('STARTING', { exact: true }).first().waitFor()
    await page.getByRole('button', { name: 'Stop' }).first().click()
    await page.getByText('STOPPED', { exact: true }).first().waitFor()
    await page.getByRole('button', { name: 'Restart' }).first().click()
    await page.getByText('RUNNING', { exact: true }).first().waitFor()
    await page.getByLabel('Control analytics worker').first().scrollIntoViewIfNeeded()
    await shot(page, 'real-admin-camera-worker-controls-fixture')
    await context.close()
    if (ilisestiPlayer) {
      const page = await browser.newPage({ viewport: VIEWPORTS.desktop })
      watch(page, 'real/ilisesti/provider-fallback', realOrigin)
      await stubApi(page, { role: 'operator' })
      await page.goto(`${realOrigin}/login`)
      await realLogin(page)
      await page.goto(`${realOrigin}/app/camere?camera=RO-DN17-WCR-001`, { waitUntil: 'domcontentloaded' })
      await page.getByText('Playerul individual nu este documentat pentru afișare aici').waitFor({ timeout: 8000 }).catch(() => fail('real/ilisesti/provider-fallback', 'camera card did not show the external-provider fallback'))
      const providerLink = page.getByRole('link', { name: 'Pagina operatorului' })
      const providerHref = await providerLink.getAttribute('href')
      if (providerHref !== 'https://webcamromania.ro/webcam-orase/webcam-ilisesti-dn17/') fail('real/ilisesti/provider-fallback', `unexpected provider URL: ${providerHref}`)
      if (await page.locator('iframe[title*="Ilișești DN17"]').count()) fail('real/ilisesti/provider-fallback', 'branding-only provider embed was presented as a live camera player')
      console.log('ILISESTI_PROVIDER_FALLBACK official source page link rendered; branding-only embed excluded; no camera image retained')
      await page.close()
    }
  } else {
  const mockOrigin = await serve('dist-mock')
  for (const role of ['admin', 'operator']) await walkRoutes(browser, mockOrigin, 'mock', MOCK_ROUTES, mockLogin(role), role)

  const realOrigin = await serve('dist-real')
  await walkRoutes(browser, realOrigin, 'real', REAL_ROUTES, realLogin, 'operator')

  // Camera metadata is writable only for the real backend's tenant-admin role.
  {
    const ctx = await browser.newContext({ viewport: VIEWPORTS.desktop })
    const page = await ctx.newPage()
    watch(page, 'real/admin/camera-edit', realOrigin)
    await stubApi(page, { role: 'admin' })
    await page.goto(`${realOrigin}/login`)
    await realLogin(page)
    await page.goto(`${realOrigin}/app/camere`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Editează metadatele' }).first().click()
    await page.getByLabel('Nume cameră').fill('Camera Alpha')
    await page.getByRole('button', { name: 'Salvează metadatele' }).click()
    await page.getByRole('heading', { name: 'Camera Alpha' }).waitFor()
    await axe(page, 'real/admin/camera-edit')
    await ctx.close()
  }

  // Real mode honesty checks + MFA step
  {
    const ctx = await browser.newContext({ viewport: VIEWPORTS.desktop })
    const page = await ctx.newPage()
    watch(page, 'real/honesty', realOrigin)
    await stubApi(page)
    await page.goto(`${realOrigin}/login`)
    if (await page.getByText('Conturi demonstrative').count()) fail('real/login', 'demo accounts visible in real mode')
    await page.waitForTimeout(500)
    await axe(page, 'real/login')
    if ((await page.locator('h1').count()) !== 1) fail('real/login', 'expected exactly 1 <h1>')
    await realLogin(page)
    for (const txt of ['Patrule disponibile', 'Patrule pe teren', 'Demonstrativ']) if (await page.getByText(txt).count()) fail('real/dashboard', `"${txt}" visible in real mode`)
    if (await page.getByRole('link', { name: 'Patrule' }).count()) fail('real/nav', 'Patrule link visible in real mode')
    await page.goto(`${realOrigin}/app/alerte/1`)
    await page.getByRole('button', { name: 'Respinge' }).click()
    await page.getByRole('button', { name: /Continuă/ }).isDisabled().then((d) => { if (!d) fail('real/case', 'reject allowed without a reason') })
    await page.getByLabel(/Motiv/).fill('fals pozitiv')
    await page.getByRole('button', { name: /Continuă/ }).click()
    if (!(await page.getByRole('dialog').isVisible())) fail('real/case', 'no confirm dialog before rejecting')
    await page.keyboard.press('Escape')
    if (await page.getByRole('dialog').isVisible()) fail('real/case', 'Esc did not close the confirm dialog')
    await ctx.close()

    const ctx2 = await browser.newContext({ viewport: VIEWPORTS.desktop })
    const p2 = await ctx2.newPage()
    watch(p2, 'real/mfa', realOrigin)
    await stubApi(p2, { mfa: true })
    await p2.goto(`${realOrigin}/login`)
    await p2.getByLabel('Utilizator').fill('operator')
    await p2.getByLabel('Parolă').fill('x')
    await p2.getByRole('button', { name: 'Intră' }).click()
    await p2.getByLabel(/Cod din aplicația/).waitFor()
    await axe(p2, 'real/mfa')
    await shot(p2, 'real-login-mfa-desktop')
    await p2.getByLabel(/Cod din aplicația/).fill('123456')
    await p2.getByRole('button', { name: 'Verifică' }).click()
    await p2.waitForURL('**/app')
    await ctx2.close()
  }
  }
} finally {
  await browser.close()
  await Promise.all(servers.map((s) => s.close()))
}
console.log(`walk finished in ${Math.round((Date.now() - t0) / 1000)}s: ${failures.length} failure(s)`)
if (failures.length) { console.log([...new Set(failures)].slice(0, 80).join('\n')); process.exit(1) }
