// Browser check for the visual camera configuration editor, against a REAL local API (no route
// stubs) with two administrators. Run by scripts/e2e/run_config_editor_e2e.sh after the camera
// control harness created a replay camera whose revision 1 a worker acknowledged. Headless Chromium.
//
// What it proves: a zone drawn with the mouse is stored in reference-frame pixels at two display
// sizes; keyboard and numeric editing, undo and redo; rules gated by what they need; problems
// shown before saving; submit; self-approval refused by the server; approval by a second
// administrator; activation shown as requested until a worker applies it; rollback.
//
// env: E2E_BASE, E2E_PASSWORD, E2E_WORKER (shell command that runs one worker pass and prints
//      {"applied_revision": n}; it inherits this environment), E2E_SLUG, E2E_ARTIFACTS (optional)
import assert from 'node:assert/strict'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const base = process.env.E2E_BASE ?? 'http://localhost:5441'
const password = process.env.E2E_PASSWORD
const worker = process.env.E2E_WORKER
const slug = process.env.E2E_SLUG ?? 'e2e-replay'
const artifacts = process.env.E2E_ARTIFACTS
assert(password && worker, 'E2E_PASSWORD and E2E_WORKER are required')

const FRAME = { width: 1920, height: 1080 }
const browser = await chromium.launch({ headless: true })
const log = (text) => console.log(`[editor] ${text}`)
const shot = async (page, name) => { if (artifacts) await page.screenshot({ path: path.join(artifacts, `${name}.png`) }) }
const near = (actual, expected, what, tolerance = 2) => assert.ok(Math.abs(actual - expected) <= tolerance, `${what}: got ${actual}, expected ${expected} ±${tolerance}`)

async function login(user, viewport = { width: 1440, height: 900 }) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  page.setDefaultTimeout(20000)
  const errors = []
  page.on('pageerror', (error) => errors.push(String(error)))
  await page.goto(`${base}/login`)
  await page.fill('#username', user)
  await page.fill('#password', password)
  await page.click('button[type=submit]')
  await page.waitForURL(/\/app/)
  return { context, page, errors }
}
async function openPanel(page, camera = slug, hasWorker = true) {
  await page.goto(`${base}/app/camere`)
  const row = page.locator(`[data-testid="control-${camera}"]`)
  await row.waitFor()
  await page.getByRole('button', { name: /Continuă oricum/ }).click({ timeout: 3000 }).catch(() => {})
  await row.locator('button').click()
  const panel = page.getByRole('dialog', { name: 'Control cameră' })
  await panel.locator('[data-testid="applied-revision"]').filter({ hasText: hasWorker ? /^\d+$/ : /./ }).waitFor()
  return panel
}
/** Client position of a reference-frame point on the editor stage as it is displayed now. */
async function at(page, x, y) {
  const box = await page.locator('[data-testid="editor-stage"]').boundingBox()
  return [box.x + (x / FRAME.width) * box.width, box.y + (y / FRAME.height) * box.height]
}
const pointValue = async (editor, n, axis) => Number(await editor.getByLabel(`Punctul ${n}, ${axis}`, { exact: true }).inputValue())
const text = (locator) => locator.innerText()

let failures = 0
try {
  const admin = await login('admin')
  let panel = await openPanel(admin.page)
  assert.equal(await text(panel.locator('[data-testid="desired-revision"]')), '1')
  await panel.locator('[data-testid="open-editor"]').click()
  const editor = admin.page.locator('[data-testid="config-editor"]')
  await editor.locator('[data-testid="editor-stage"]').waitFor()
  assert.equal(await editor.locator('[data-testid^="zone-row-"]').count(), 2, 'the editor starts from the active version (2 zones)')
  assert.match(await text(editor.locator('[data-testid="backdrop-note"]')), /Fără imagine de fundal|Fundal:/)

  // ---- draw a zone with the mouse: stored in reference-frame pixels
  const corners = [[200, 120], [600, 120], [600, 320], [200, 320]]
  await editor.locator('[data-testid="draw-zone"]').click()
  for (const [x, y] of corners) await admin.page.mouse.click(...(await at(admin.page, x, y)))
  await editor.getByRole('button', { name: 'Închide zona' }).click()
  assert.equal(await editor.locator('[data-testid^="zone-row-"]').count(), 3)
  for (const [i, [x, y]] of corners.entries()) {
    near(await pointValue(editor, i + 1, 'x'), x, `drawn point ${i + 1} x`)
    near(await pointValue(editor, i + 1, 'y'), y, `drawn point ${i + 1} y`)
  }
  log('zone drawn with 4 clicks; its points are the clicked reference-frame pixels (±2)')

  // ---- the same mapping at another display size: drag a corner after shrinking the window
  await admin.page.setViewportSize({ width: 1100, height: 720 })
  await admin.page.waitForTimeout(300)
  const from = await at(admin.page, await pointValue(editor, 3, 'x'), await pointValue(editor, 3, 'y'))
  const to = await at(admin.page, 900, 400)
  await admin.page.mouse.move(...from)
  await admin.page.mouse.down()
  await admin.page.mouse.move((from[0] + to[0]) / 2, (from[1] + to[1]) / 2, { steps: 4 })
  await admin.page.mouse.move(...to, { steps: 4 })
  await admin.page.mouse.up()
  near(await pointValue(editor, 3, 'x'), 900, 'dragged corner x at 1100 px wide', 3)
  near(await pointValue(editor, 3, 'y'), 400, 'dragged corner y at 1100 px wide', 3)
  await admin.page.setViewportSize({ width: 1440, height: 900 })
  await admin.page.waitForTimeout(300)
  near(await pointValue(editor, 3, 'x'), 900, 'corner x unchanged after resizing back', 3)
  log('corner dragged at a smaller display size lands on the intended frame pixel; resizing does not move it')

  // ---- keyboard and numeric editing, undo and redo
  const x1 = await pointValue(editor, 1, 'x'), y1 = await pointValue(editor, 1, 'y')
  await editor.locator('[data-testid="zone-2-vertex-0"]').focus()
  await admin.page.keyboard.press('ArrowRight')
  await admin.page.keyboard.press('Shift+ArrowDown')
  assert.equal(await pointValue(editor, 1, 'x'), x1 + 1)
  assert.equal(await pointValue(editor, 1, 'y'), y1 + 10)
  await editor.getByRole('button', { name: 'Anulează ultima modificare' }).click()
  await editor.getByRole('button', { name: 'Anulează ultima modificare' }).click()
  await editor.locator('[data-testid="zone-row-2"]').click()
  assert.equal(await pointValue(editor, 1, 'x'), x1)
  assert.equal(await pointValue(editor, 1, 'y'), y1)
  await editor.getByRole('button', { name: 'Refă modificarea' }).click()
  await editor.locator('[data-testid="zone-row-2"]').click()
  assert.equal(await pointValue(editor, 1, 'x'), x1 + 1)
  await editor.getByLabel('Punctul 1, x', { exact: true }).fill('210')
  assert.equal(await pointValue(editor, 1, 'x'), 210)
  log('arrow keys move a corner by 1 px (Shift: 10 px); undo, redo and typed coordinates work')

  // ---- a problem is shown on the shape and blocks saving
  await editor.getByLabel('Punctul 2, x', { exact: true }).fill('5000')
  const problems = editor.locator('[data-testid="editor-problems"]')
  assert.match(await text(problems), /zones\[2\]\.polygon\[1\]/)
  await editor.locator('[data-testid="editor-reason"]').fill('Zonă nouă pentru banda de urgență')
  assert.ok(await editor.locator('[data-testid="editor-submit"]').isDisabled(), 'a config with problems cannot be saved')
  await editor.getByLabel('Punctul 2, x', { exact: true }).fill('600')
  await problems.waitFor({ state: 'detached' })

  // ---- rules are gated by what they need
  await editor.locator('[data-testid="tab-rules"]').click()
  const lane = editor.locator('[data-testid="rule-stopped_emergency_lane"]')
  assert.match(await text(lane.locator('[data-testid="rule-stopped_emergency_lane-blocked"]')), /lipsește zona/)
  assert.ok(await lane.getByRole('checkbox').isDisabled(), 'a rule without its zone cannot be switched on')
  await editor.locator('[data-testid="tab-zones"]').click()
  await editor.locator('[data-testid="zone-row-2"]').click()
  await editor.locator('[data-testid="zone-form"]').getByLabel('Nume').fill('Bandă de urgență')
  await editor.locator('[data-testid="zone-form"]').getByLabel('Identificator').fill('banda_urgenta')
  await editor.locator('[data-testid="zone-form"]').getByLabel('Tip').selectOption('emergency_lane')
  await editor.locator('[data-testid="tab-rules"]').click()
  assert.equal(await lane.locator('[data-testid="rule-stopped_emergency_lane-blocked"]').count(), 0)
  await lane.getByRole('checkbox').check()
  log('"stopped in the emergency lane" is unavailable until an emergency-lane zone exists, then can be enabled')

  // ---- thresholds: bounds and consistency
  await editor.locator('[data-testid="tab-thresholds"]').click()
  const veryHigh = editor.locator('[data-testid="threshold-very_high_speed_kmh"]')
  const before = await veryHigh.inputValue()
  await veryHigh.fill('10')
  assert.match(await text(problems), /thresholds\.very_high_speed_kmh/)
  await veryHigh.fill(before)
  await problems.waitFor({ state: 'detached' })
  await editor.locator('[data-testid="threshold-stopped_seconds"]').fill('45')
  await shot(admin.page, 'editor-before-submit')

  // ---- server check, save and submit
  await editor.locator('[data-testid="editor-check"]').click()
  await editor.locator('[data-testid="editor-notice"]').filter({ hasText: 'Serverul acceptă configurația' }).waitFor()
  await editor.locator('[data-testid="editor-submit"]').click()
  await editor.waitFor({ state: 'detached' })
  assert.match(await text(panel.locator('[data-testid="control-notice"]')), /Versiunea 2 a fost trimisă spre aprobare/)
  const v2 = panel.locator('[data-testid="version-2"]')
  assert.equal(await text(v2.locator('[data-testid="version-status"]')), 'Așteaptă aprobare')
  log('server accepted the config; revision 2 saved and submitted from the editor')

  // ---- four eyes: the author cannot approve
  await panel.locator('[data-testid="control-reason"]').fill('încerc să aprob singur')
  await v2.getByRole('button', { name: /Aprobă/ }).click()
  await panel.locator('[data-testid="control-notice"]').filter({ hasText: /Refuzat de server/ }).waitFor()
  assert.equal(await text(v2.locator('[data-testid="version-status"]')), 'Așteaptă aprobare', 'self-approval must not change the status')
  const refusal = await text(panel.locator('[data-testid="control-notice"]'))
  assert.match(refusal, /different administrator/)
  log(`author's approval refused by the server: "${refusal.slice(0, 110)}"`)

  // ---- a second administrator reviews the diff and approves
  const second = await login('admin2@roadsentinel.local')
  const panel2 = await openPanel(second.page)
  const v2b = panel2.locator('[data-testid="version-2"]')
  await v2b.getByRole('button', { name: 'Diferențe față de activă' }).click()
  const diffText = await text(panel2.locator('[data-testid="version-diff"]'))
  assert.match(diffText, /banda_urgenta/, 'the diff names the new zone')
  assert.match(diffText, /stopped_seconds/, 'the diff shows the changed threshold')
  await shot(second.page, 'reviewer-diff')
  await panel2.locator('[data-testid="control-reason"]').fill('Am verificat zona și pragurile')
  await v2b.getByRole('button', { name: /Aprobă/ }).click()
  await v2b.locator('[data-testid="version-status"]').filter({ hasText: 'Aprobată' }).waitFor()
  log('second administrator saw the diff (new zone, changed threshold) and approved revision 2')

  // ---- activation is a request until a worker applies it
  panel = await openPanel(admin.page)
  await panel.locator('[data-testid="control-reason"]').fill('Activez configurația aprobată')
  await panel.locator('[data-testid="version-2"]').getByRole('button', { name: 'Activează' }).click()
  await panel.locator('[data-testid="desired-revision"]').filter({ hasText: /^2$/ }).waitFor()
  assert.equal(await text(panel.locator('[data-testid="applied-revision"]')), '1', 'no worker has applied revision 2 yet')
  assert.equal(await text(panel.locator('[data-testid="config-stage"]')), 'Cerută, neaplicată încă')
  await shot(admin.page, 'activated-not-applied')
  log('after activation the panel shows requested r2, applied r1: not yet in effect')

  const applied = JSON.parse(execSync(worker, { encoding: 'utf8' }).trim().split('\n').pop()).applied_revision
  assert.equal(applied, 2, 'the worker applied the activated revision')
  panel = await openPanel(admin.page)
  assert.equal(await text(panel.locator('[data-testid="applied-revision"]')), '2')
  assert.equal(await text(panel.locator('[data-testid="config-stage"]')), 'Aplicată de worker')
  await shot(admin.page, 'applied-by-worker')
  log('a worker pass fetched, verified and acknowledged r2; the panel now shows it applied')

  // ---- the saved geometry is exactly what was drawn (read back through the editor after reload)
  await panel.locator('[data-testid="open-editor"]').click()
  await editor.locator('[data-testid="zone-row-2"]').click()
  assert.equal(await editor.locator('[data-testid="zone-form"]').getByLabel('Identificator').inputValue(), 'banda_urgenta')
  assert.equal(await pointValue(editor, 1, 'x'), 210)
  near(await pointValue(editor, 3, 'x'), 900, 'saved corner x', 3)
  await editor.getByRole('button', { name: 'Închide editorul' }).click()

  // ---- rollback to revision 1 is again only a request until applied
  await panel.locator('[data-testid="control-reason"]').fill('Revin la configurația anterioară')
  await panel.locator('[data-testid="version-1"]').getByRole('button', { name: 'Revino la această versiune' }).click()
  await panel.locator('[data-testid="desired-revision"]').filter({ hasText: /^1$/ }).waitFor()
  assert.equal(await text(panel.locator('[data-testid="applied-revision"]')), '2')
  assert.equal(JSON.parse(execSync(worker, { encoding: 'utf8' }).trim().split('\n').pop()).applied_revision, 1)
  log('rollback requested r1 while the worker still ran r2; the next worker pass applied r1')

  // ---- a new camera, onboarded entirely from the UI: nothing runs until every step is done
  await admin.page.goto(`${base}/app/camere`)
  await admin.page.locator('[data-testid="add-camera-open"]').click()
  await admin.page.locator('[data-testid="add-camera-name"]').fill('Cameră nouă E2E')
  await admin.page.locator('[data-testid="add-camera-location"]').fill('Stradă de test, fără cameră reală')
  await admin.page.locator('[data-testid="add-camera-slug"]').fill('e2e-noua')
  await admin.page.locator('[data-testid="add-camera-save"]').click()
  const fresh = admin.page.getByRole('dialog', { name: 'Control cameră' })
  await fresh.locator('[data-testid="lifecycle"]').filter({ hasText: 'În configurare' }).waitFor()
  assert.equal(await text(fresh.locator('[data-testid="source-kind"]')), 'Sursă nedeclarată')
  assert.equal(await text(fresh.locator('[data-testid="config-stage"]')), 'Nicio configurație activată')
  assert.ok((await text(fresh.locator('[data-testid="unmet"]'))).length > 10, 'a new camera lists what is missing')
  await fresh.locator('[data-testid="control-reason"]').fill('Înregistrez sursa camerei noi')
  await fresh.locator('[data-testid="open-source-form"]').click()
  await fresh.locator('[data-testid="source-url-input"]').fill('rtsp://camera.invalid/stream') // wrong scheme for a recording
  await fresh.locator('[data-testid="source-save"]').click()
  await fresh.locator('[data-testid="control-notice"]').filter({ hasText: /Sursă înregistrată:/ }).waitFor()
  assert.equal(await text(fresh.locator('[data-testid="source-kind"]')), 'Sursă nedeclarată', 'a refused source is not stored')
  await fresh.locator('[data-testid="source-url-input"]').fill('replay://data/videos/vehicles-2.mp4')
  await fresh.locator('[data-testid="source-save"]').click()
  await fresh.locator('[data-testid="source-kind"]').filter({ hasText: 'Înregistrare redată (replay)' }).waitFor()
  assert.equal(await fresh.locator('[data-testid="source-form"]').count(), 0, 'the form closes once the source is stored')
  await fresh.locator('[data-testid="open-grant-form"]').click()
  await fresh.locator('[data-testid="grant-party"]').fill('Fixture local de test (E2E)')
  await fresh.locator('[data-testid="grant-reference"]').fill('E2E-TEST-ONLY: nu este o autorizare reală')
  await fresh.locator('[data-testid="grant-purpose"]').fill('Verificare automată locală pe un clip demonstrativ licențiat')
  await fresh.locator('[data-testid="grant-scope"]').selectOption('events_and_recordings')
  await fresh.locator('[data-testid="grant-save"]').click()
  await fresh.getByText('alerte și înregistrări').waitFor()
  log('new camera added from the UI; a wrong source address was refused, a replay source and a test-only permission recorded')

  await fresh.locator('[data-testid="open-editor"]').click()
  await editor.locator('[data-testid="frame-width"]').fill('1920')
  await editor.locator('[data-testid="frame-height"]').fill('1080')
  await editor.locator('[data-testid="frame-start"]').click()
  await editor.locator('[data-testid="add-rectangle"]').click()
  assert.equal(await pointValue(editor, 1, 'x'), 720)
  await editor.locator('[data-testid="tab-rules"]').click()
  const speed = editor.locator('[data-testid="rule-very_high_speed"]')
  assert.match(await text(speed.locator('[data-testid="rule-very_high_speed-blocked"]')), /necalibrat/)
  assert.ok(await speed.getByRole('checkbox').isDisabled(), 'a speed rule cannot be enabled without calibration')
  await editor.locator('[data-testid="rule-pedestrian_on_road"]').getByRole('checkbox').check()
  await editor.locator('[data-testid="editor-reason"]').fill('Prima configurație a camerei noi')
  await editor.locator('[data-testid="editor-submit"]').click()
  await editor.waitFor({ state: 'detached' })
  await fresh.locator('[data-testid="version-1"] [data-testid="version-status"]').filter({ hasText: 'Așteaptă aprobare' }).waitFor()
  const review = await openPanel(second.page, 'e2e-noua', false)
  await review.locator('[data-testid="control-reason"]').fill('Verificat: zonă simplă, fără reguli de viteză')
  await review.locator('[data-testid="version-1"]').getByRole('button', { name: /Aprobă/ }).click()
  await review.locator('[data-testid="version-1"] [data-testid="version-status"]').filter({ hasText: 'Aprobată' }).waitFor()
  const mine = await openPanel(admin.page, 'e2e-noua', false)
  await mine.locator('[data-testid="control-reason"]').fill('Activez prima configurație')
  await mine.locator('[data-testid="version-1"]').getByRole('button', { name: 'Activează' }).click()
  await mine.locator('[data-testid="desired-revision"]').filter({ hasText: /^1$/ }).waitFor()
  assert.equal(await text(mine.locator('[data-testid="config-stage"]')), 'Cerută, neaplicată încă')
  assert.match(await text(mine.locator('[data-testid="config-stage-detail"]')), /niciun worker/)
  await shot(admin.page, 'new-camera-activated')
  log('speed rule unavailable without calibration; first config drawn without a mouse, approved by the second administrator, activated: requested, no worker yet')

  // ---- revoking the permission blocks the camera, whatever was approved
  await mine.locator('[data-testid="control-reason"]').fill('Proprietarul a retras acordul')
  await mine.locator('[data-testid="grant-revoke"]').click()
  await mine.locator('[data-testid="unmet"]').filter({ hasText: /revoked/ }).waitFor()
  assert.match(await text(mine.locator('[data-testid="runtime-state"]')), /Blocată: autorizare lipsă/)
  log('permission revoked from the UI: the approved camera is shown blocked')

  // ---- an operator cannot open the editor
  const operator = await login('operator')
  const opPanel = await openPanel(operator.page)
  assert.equal(await opPanel.locator('[data-testid="open-editor"]').count(), 0)
  assert.deepEqual([...admin.errors, ...second.errors, ...operator.errors], [], 'no page errors')
} catch (error) {
  failures++
  console.error(error)
} finally {
  await browser.close()
}
console.log(failures ? 'E2E CONFIG EDITOR: FAIL' : 'E2E CONFIG EDITOR: PASS')
process.exit(failures ? 1 : 0)
