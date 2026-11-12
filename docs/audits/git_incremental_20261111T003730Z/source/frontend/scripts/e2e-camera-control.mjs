// A18 browser check for the camera control plane, against a REAL local API (no route stubs).
// Run by scripts/e2e/run_camera_control_e2e.sh after the API harness activated a config and a
// worker acknowledged it. Headless Chromium only.
//
// env: E2E_BASE (vite preview origin proxied to the API), E2E_PASSWORD, E2E_SLUG, E2E_CAMERA_ID,
//      E2E_ARTIFACTS (optional directory for screenshots)
import assert from 'node:assert/strict'
import path from 'node:path'
import { chromium } from '@playwright/test'

const base = process.env.E2E_BASE ?? 'http://localhost:5441'
const password = process.env.E2E_PASSWORD
const slug = process.env.E2E_SLUG ?? 'e2e-replay'
const cameraId = process.env.E2E_CAMERA_ID
const artifacts = process.env.E2E_ARTIFACTS
assert(password && cameraId, 'E2E_PASSWORD and E2E_CAMERA_ID are required')

const browser = await chromium.launch({ headless: true })
const log = (text) => console.log(`[browser] ${text}`)

async function login(user) {
  const context = await browser.newContext()
  const page = await context.newPage()
  page.setDefaultTimeout(20000)
  const runtimeErrors = []
  const consoleErrors = []
  page.on('pageerror', (error) => runtimeErrors.push(String(error)))
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  await page.goto(`${base}/login`)
  await page.fill('#username', user)
  await page.fill('#password', password)
  await page.click('button[type=submit]')
  await page.waitForURL(/\/app/)
  return { context, page, runtimeErrors, consoleErrors }
}

async function openCamera(page) {
  await page.goto(`${base}/app/camere`)
  const row = page.locator(`[data-testid="control-${slug}"]`)
  await row.waitFor()
  // AppLayout's "preparing video files" splash covers the page until clips are cached.
  await page.getByRole('button', { name: /Continuă oricum/ }).click({ timeout: 4000 }).catch(() => {})
  const card = page.locator('div.group', { has: row })
  const badge = card.locator('[data-testid="runtime-state"]')
  await assertState(badge)
  await row.locator('button').click()
  const panel = page.getByRole('dialog', { name: 'Control cameră' })
  await panel.locator('[data-testid="applied-revision"]').filter({ hasText: /^\d+$/ }).waitFor()
  return { card, panel }
}

async function assertState(badge) {
  const state = await badge.getAttribute('data-state')
  const text = (await badge.innerText()).trim()
  assert.equal(state, 'replay', `expected replay state, got ${state} (${text})`)
  assert.match(text, /^REDARE/)
  assert.doesNotMatch(text, /\bLIVE\b/, 'a replay must never be labelled LIVE')
}

let failures = 0
try {
  // ---- administrator
  const admin = await login('admin')
  const { panel } = await openCamera(admin.page)
  assert.equal(await panel.locator('[data-testid="applied-revision"]').innerText(), '1')
  assert.equal(await panel.locator('[data-testid="desired-revision"]').innerText(), '1')
  assert.equal(await panel.locator('[data-testid="source-kind"]').innerText(), 'Înregistrare redată (replay)')
  await assertState(panel.locator('[data-testid="runtime-state"]'))
  assert.equal(await panel.locator('[data-testid="version-1"] [data-testid="version-status"]').innerText(), 'Activă')
  // This harness sends no source fingerprint and no detector metrics: the UI must say so, not invent them.
  assert.equal(await panel.locator('[data-testid="source-attestation"]').innerText(), 'neraportată de niciun worker activ')
  assert.ok(await panel.getByRole('group', { name: 'Metrici worker' }).isVisible(), 'worker metrics section is shown')
  assert.equal(await panel.locator('[data-testid="metric-latency"]').innerText(), '— / —')
  assert.match(await panel.locator('[data-testid="metrics-freshness"]').innerText(), /ultimul semnal/)
  assert.ok(await panel.getByRole('button', { name: 'Dezactivează' }).isVisible(), 'admin sees mutation controls')
  const restart = panel.getByRole('button', { name: /Repornire indisponibilă/ })
  assert.ok(await restart.isDisabled(), 'unsupported restart is shown disabled')
  if (artifacts) await admin.page.screenshot({ path: path.join(artifacts, 'admin-camera-control.png'), fullPage: true })
  assert.deepEqual(admin.runtimeErrors, [], `admin runtime errors: ${admin.runtimeErrors}`)
  log(`admin: replay badge (not LIVE), applied r1 = desired r1, controls visible; console errors: ${admin.consoleErrors.length}`)

  // ---- operator: read-only UI and server-side 403
  const operator = await login('operator')
  const op = await openCamera(operator.page)
  assert.equal(await op.panel.locator('[data-testid="applied-revision"]').innerText(), '1')
  assert.ok(await op.panel.getByText('Doar citire').isVisible())
  for (const name of ['Dezactivează', 'Pauză', 'Activează', 'Validează', 'Ciornă ca JSON', /Editor vizual/]) {
    assert.equal(await op.panel.getByRole('button', { name }).count(), 0, `operator must not see "${name}"`)
  }
  const csrf = (await operator.context.cookies()).find((c) => c.name.endsWith('rs_csrf'))?.value ?? ''
  const denied = await operator.page.request.post(`${base}/api/camera-control/cameras/${cameraId}/pause`, {
    headers: { 'X-CSRF-Token': decodeURIComponent(csrf), Origin: base },
    data: { expected_revision: 0, reason: 'operator tries to pause' },
  })
  assert.equal(denied.status(), 403, `operator mutation must be 403, got ${denied.status()}`)
  if (artifacts) await operator.page.screenshot({ path: path.join(artifacts, 'operator-camera-control.png'), fullPage: true })
  assert.deepEqual(operator.runtimeErrors, [], `operator runtime errors: ${operator.runtimeErrors}`)
  log(`operator: read-only panel, no mutation controls, POST pause -> ${denied.status()}; console errors: ${operator.consoleErrors.length}`)
  for (const message of [...admin.consoleErrors, ...operator.consoleErrors]) log(`console error (reported, not fatal): ${message}`)
} catch (error) {
  failures++
  console.error(error)
} finally {
  await browser.close()
}
console.log(failures ? 'E2E CAMERA CONTROL: FAIL' : 'E2E CAMERA CONTROL: PASS')
process.exit(failures ? 1 : 0)
