import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { createServer as createNetServer } from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { createServer, loadConfigFromFile } from 'vite'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repo = path.dirname(root)
const runtime = await mkdtemp(path.join(root, 'node_modules/.smoke-'))
const socket = createNetServer()
await new Promise((resolve) => socket.listen(0, '127.0.0.1', resolve))
const port = socket.address().port
await new Promise((resolve) => socket.close(resolve))
const backend = `http://127.0.0.1:${port}`
const python = process.env.SMOKE_PYTHON ?? path.join(repo, '.venv/bin/python')
const server = spawn(python, ['-m', 'uvicorn', 'roadsentinel.server:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: runtime, env: { ...process.env, PYTHONPATH: repo, DATABASE_URL: `sqlite:///${runtime}/smoke.db`, DASHBOARD_PASSWORD: 'smoke-password', COOKIE_SECURE: '0', INGEST_TOKEN: 'smoke-ingest', SECRET_KEY: 'smoke-session-only' }, stdio: ['ignore', 'pipe', 'pipe'],
})
let serverLog = ''
server.stdout.on('data', (data) => { serverLog += data })
server.stderr.on('data', (data) => { serverLog += data })
let vite, browser
try {
  let ready = false
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(`${backend}/api/me`)).ok) { ready = true; break } } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  assert(ready, serverLog)
  const config = await loadConfigFromFile({ command: 'serve', mode: 'development' }, path.join(root, 'vite.config.ts'))
  vite = await createServer({ ...config.config, root, configFile: false, server: { host: '127.0.0.1', port: 0, proxy: { '/api': backend, '/media': backend } } })
  await vite.listen()
  const origin = `http://127.0.0.1:${vite.httpServer.address().port}`
  browser = await chromium.launch({ headless: true, ...(process.env.SMOKE_CHROME ? { executablePath: process.env.SMOKE_CHROME } : {}) })
  const page = await browser.newPage()
  page.setDefaultTimeout(15000)
  page.setDefaultNavigationTimeout(15000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  async function ingest(type) {
    const body = new FormData()
    body.set('event', JSON.stringify({ camera_id: 'demo-highway', type, object_class: type === 'pedestrian_on_road' ? 'person' : 'car', occurred_at: '2026-10-17T10:00:00', video_t: 1, rule: `Smoke ${type}`, vlm_status: 'skipped' }))
    body.set('keyframe', new Blob(['demo'], { type: 'image/jpeg' }), 'keyframe.jpg')
    body.set('clip', new Blob(['demo'], { type: 'video/mp4' }), 'clip.mp4')
    const response = await fetch(`${backend}/api/ingest/events`, { method: 'POST', headers: { Authorization: 'Bearer smoke-ingest' }, body })
    assert.equal(response.status, 200, await response.text())
  }
  await ingest('stopped_on_road')
  console.log('Demo server ready; opening UI')
  await page.goto(origin)
  await page.waitForURL('**/login')
  await page.locator('input[autocomplete=username]').fill('smoke@example.test')
  await page.locator('input[autocomplete=current-password]').fill('smoke-password')
  await page.getByRole('button', { name: 'INTRĂ ÎN SISTEM' }).click()
  await page.waitForURL(origin + '/')
  console.log('Logged in')
  await page.goto(origin + '/alerte')
  await page.getByText('Vehicul oprit pe carosabil', { exact: true }).first().waitFor()
  await page.goto(origin + '/alerte/1')
  console.log('Opened event detail')
  await page.getByLabel('Acțiune').selectOption('monitor')
  await page.getByRole('button', { name: 'CONFIRMĂ', exact: true }).click()
  await page.getByText('CONFIRMATĂ', { exact: true }).waitFor()
  const decision = await page.request.get(origin + '/api/events/1')
  assert.equal((await decision.json()).action, 'monitor')
  await page.goto(origin + '/alerte')
  await ingest('pedestrian_on_road')
  await page.getByText('Pieton pe carosabil', { exact: true }).first().waitFor()
  await page.goto(origin + '/arhiva')
  await page.locator('input').fill('pieton')
  await page.getByRole('button', { name: 'CAUTĂ ÎN ARHIVĂ' }).click()
  await page.getByText('Pieton pe carosabil', { exact: true }).first().waitFor()
  assert.deepEqual(errors, [])
  console.log('PASS real demo: login, event detail, confirmed monitor decision, SSE arrival, search, no browser exceptions')

  const mfaPage = await browser.newPage()
  let verified = false
  let aliasAttempted = false
  await mfaPage.route('**/api/auth/csrf', (route) => route.fulfill({ json: { csrf_token: 'smoke-csrf' }, headers: { 'set-cookie': 'rs_csrf=smoke-csrf; Path=/' } }))
  await mfaPage.route('**/api/me', (route) => route.fulfill({ json: { operator: verified ? 'MFA operator' : null, auth_required: true } }))
  await mfaPage.route('**/api/login', (route) => route.fulfill({ json: { operator: null, auth_required: true, mfa_required: true } }))
  await mfaPage.route('**/api/login/mfa', (route) => { aliasAttempted = true; return route.fulfill({ status: 404, json: { detail: 'Not found' } }) })
  await mfaPage.route('**/api/auth/mfa/verify', (route) => {
    assert.equal(route.request().headers()['x-csrf-token'], 'smoke-csrf')
    assert.deepEqual(route.request().postDataJSON(), { code: '123456' })
    verified = true
    return route.fulfill({ status: 204 })
  })
  await mfaPage.goto(origin + '/login')
  await mfaPage.locator('input[autocomplete=username]').fill('mfa@example.test')
  await mfaPage.locator('input[autocomplete=current-password]').fill('password')
  await mfaPage.getByRole('button', { name: 'INTRĂ ÎN SISTEM' }).click()
  await mfaPage.locator('input[autocomplete=one-time-code]').fill('123456')
  await mfaPage.getByRole('button', { name: 'INTRĂ ÎN SISTEM' }).click()
  await mfaPage.waitForURL(origin + '/')
  assert(verified && aliasAttempted)
  console.log('PASS simulated secure contract: MFA alias 404 fallback, CSRF header, verification code, session restoration')
} finally {
  await browser?.close()
  await vite?.close()
  server.kill('SIGTERM')
  await new Promise((resolve) => server.once('exit', resolve))
  await rm(runtime, { recursive: true, force: true })
}
