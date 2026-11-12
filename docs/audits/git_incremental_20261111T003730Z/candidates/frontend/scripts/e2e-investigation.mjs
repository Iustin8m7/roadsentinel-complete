// Investigation workflow E2E against the REAL API (no stubbed routes), headless Chromium only.
//
// Prerequisites (see scripts/e2e-investigation-setup.sh): disposable Postgres, API with the
// generated env on :8442, one SYNTHETIC incident ingested, and `vite preview` on :5442 with
// RS_API_PROXY=http://127.0.0.1:8442. Then:
//
//   E2E_BASE=http://localhost:5442 E2E_WORKDIR=/scratch/dir node scripts/e2e-investigation.mjs
//
// Covers: login -> archive search (interpretation chips) -> open case -> evidence + honest
// labels -> bookmark at the current clip time -> note -> reload (both persisted) -> export
// request -> second admin approves (four-eyes) -> generate -> download -> offline digest
// verification with `python -m app.cli verify-package` -> decision + concurrent-decision
// conflict feedback -> no console errors.
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const BASE = process.env.E2E_BASE ?? 'http://localhost:5442'
const WORK = process.env.E2E_WORKDIR ?? '.'
const PASSWORD = process.env.E2E_PASSWORD ?? 'E2e-Investigation-2026'
const PY = process.env.E2E_PYTHON ?? path.join(process.env.HOME, 'token/backend/.venv/bin/python')
const BACKEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../backend')
const steps = []
const step = (name) => { steps.push(name); console.log(`✓ ${name}`) }

const browser = await chromium.launch({ headless: true })
const problems = []
async function session(user) {
  const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1600, height: 1000 } })
  const page = await context.newPage()
  page.setDefaultTimeout(20000)
  page.on('pageerror', (e) => problems.push(`[${user}] pageerror: ${e.message}`))
  page.on('console', (m) => { if (m.type() === 'error') problems.push(`[${user}] console: ${m.text()}`) })
  await page.goto(`${BASE}/login`)
  await page.locator('input[autocomplete=username]').fill(user)
  await page.locator('input[autocomplete=current-password]').fill(PASSWORD)
  await page.locator('form button[type=submit]').click()
  await page.waitForURL(`${BASE}/app`)
  await ready(page)
  return page
}
// The app shell always mounts a full-screen clip-preload overlay; its own "continue" button
// moves on (it also never closes by itself when the visible queue is empty, as here: incident
// #1 is one of the ids the dashboard's demo curation hides, which this test opens on purpose).
async function ready(page) {
  await page.locator('aside').first().waitFor()
  // The clip preload overlay closes by itself once clips are cached; skip it only if still open.
  const skip = page.getByRole('button', { name: /Continuă oricum/ })
  await skip.click({ timeout: 3000 }).catch(() => {})
  await skip.waitFor({ state: 'detached', timeout: 60000 })
}

try {
  const op = await session('operator')
  step('operator logged in through the UI (real API, MFA-exempt demo account)')

  await op.goto(`${BASE}/app/arhiva`)
  await ready(op)
  await op.getByTestId('archive-card').first().waitFor()
  await op.getByLabel('Căutare în arhivă după cuvinte cheie').fill('viteză peste 130 km/h xyzzy')
  await op.getByRole('button', { name: 'Caută' }).click()
  await op.getByTestId('token-unsupported').first().waitFor()
  assert.equal(await op.getByTestId('token-unsupported').count(), 1)
  assert.match(await op.getByTestId('token-unsupported').first().innerText(), /xyzzy/)
  assert.ok(await op.getByTestId('token-recognized').count() >= 2)
  assert.match(await op.getByTestId('archive-total').innerText(), /^1 rezultate/)
  step('archive search with recognized/unsupported token interpretation and exact total')

  await op.getByTestId('open-case').first().click()
  await op.waitForURL(/\/app\/alerte\/\d+$/)
  const caseUrl = op.url()
  await op.getByTestId('case-workspace').waitFor()
  assert.equal(await op.getByTestId('evidence-clip').getByTestId('storage-state').innerText(), 'Disponibilă')
  assert.match(await op.getByTestId('source-kind').innerText(), /Necunoscută/)
  assert.match(await op.getByTestId('model-status').innerText(), /nu a fost măsurată/)
  assert.match(await op.getByTestId('speed').innerText(), /necalibrată/)
  step('case opened from the archive: evidence available, source/model/speed shown honestly')

  const addBookmark = op.getByRole('button', { name: 'Adaugă marcaj la momentul curent' })
  await op.waitForFunction(() => {
    const v = document.querySelector('video')
    return v && v.readyState >= 1 && v.duration > 0
  })
  await op.evaluate(() => { const v = document.querySelector('video'); v.pause(); v.currentTime = 2.5 })
  await addBookmark.click()
  await op.getByLabel('Etichetă marcaj').fill('Vehicul intră în cadru (E2E)')
  await op.getByRole('button', { name: 'Salvează' }).click()
  await op.getByTestId('bookmark-item').filter({ hasText: 'Vehicul intră în cadru (E2E)' }).waitFor()
  step('bookmark added at the current clip time')

  await op.getByLabel('Textul notei').fill('Observație E2E: obiectul se deplasează de la stânga la dreapta.')
  await op.getByLabel('Vehicul clar vizibil').check()
  await op.getByRole('button', { name: 'Adaugă nota' }).click()
  await op.getByTestId('note-item').filter({ hasText: 'Observație E2E' }).waitFor()
  step('investigator note added')

  await op.reload()
  await ready(op)
  await op.getByTestId('case-workspace').waitFor()
  const bm = op.getByTestId('bookmark-item').filter({ hasText: 'Vehicul intră în cadru (E2E)' })
  await bm.waitFor()
  assert.match(await bm.innerText(), /0:02\.5/)
  await op.getByTestId('note-item').filter({ hasText: 'Observație E2E' }).waitFor()
  await op.getByTestId('bookmark-marker').first().waitFor()
  step('after reload: bookmark (with its real timestamp) and note persisted; marker on the timeline')

  await op.getByLabel('Justificare export').fill('Dosar E2E: verificare pachet de probe sintetic')
  await op.getByLabel('Referință dosar').fill('E2E-2026-1')
  await op.getByRole('button', { name: 'Solicită export' }).click()
  await op.locator('[data-testid=export-item][data-state=pending_approval]').waitFor()
  assert.ok(await op.getByText('Nu vă puteți aproba propria cerere.').isVisible())
  step('export requested; requester cannot approve it')

  const admin = await session('admin')
  await admin.goto(caseUrl)
  await ready(admin)
  await admin.getByTestId('case-workspace').waitFor()
  await admin.getByRole('button', { name: 'Aprobă exportul' }).click()
  await admin.locator('[data-testid=export-item][data-state=queued]').waitFor()
  step('second administrator approved the export (four-eyes)')

  await op.reload()
  await ready(op)
  await op.getByRole('button', { name: 'Generează pachetul' }).click()
  await op.locator('[data-testid=export-item][data-state=completed]').waitFor()
  const manifestSha = (await op.getByTestId('manifest-sha256').innerText()).trim()
  assert.match(manifestSha, /^[0-9a-f]{64}$/)
  const [download] = await Promise.all([
    op.waitForEvent('download'),
    op.getByRole('button', { name: 'Descarcă pachetul' }).click(),
  ])
  const zipPath = path.join(WORK, 'e2e-package.zip')
  await download.saveAs(zipPath)
  const verify = spawnSync(PY, ['-m', 'app.cli', 'verify-package', zipPath, '--manifest-sha256', manifestSha], {
    cwd: BACKEND, env: { PATH: process.env.PATH }, encoding: 'utf8',
  })
  assert.equal(verify.status, 0, verify.stdout + verify.stderr)
  const report = JSON.parse(verify.stdout)
  assert.equal(report.ok, true)
  assert.equal(report.files_checked, 2)
  const jobs = await op.evaluate(async (url) => (await fetch(url, { credentials: 'include' })).json(),
    `/api/events/${caseUrl.split('/').pop()}/exports`)
  const zipSha = createHash('sha256').update(readFileSync(zipPath)).digest('hex')
  assert.equal(jobs[0].package_sha256, zipSha)
  step(`package downloaded and verified offline: ${report.files_checked} files, manifest ${manifestSha.slice(0, 12)}…`)

  await admin.reload()
  await ready(admin)
  await admin.getByTestId('case-workspace').waitFor()
  await op.getByRole('button', { name: 'Confirmă', exact: true }).click()
  await op.getByText('Alertă confirmată').waitFor()
  await admin.getByRole('button', { name: 'Respinge', exact: true }).click()
  await admin.getByPlaceholder(/fals pozitiv/).fill('Test E2E: decizie concurentă')
  await admin.getByRole('button', { name: 'Confirmă respingerea' }).click()
  await admin.getByTestId('decision-conflict').waitFor()
  assert.match(await admin.getByTestId('decision-conflict').innerText(), /deja confirmat de Operator/)
  step('operator confirmed; a stale second tab got explicit 409 conflict feedback')

  const unexpected = problems.filter((p) => !/Failed to load resource: the server responded with a status of 409/.test(p))
  assert.deepEqual(unexpected, [], unexpected.join('\n'))
  step(`no console/page errors (the one expected 409 resource message ignored: ${problems.length - unexpected.length})`)
  console.log(`\nE2E PASSED (${steps.length} steps)`)
} finally {
  await browser.close()
}
