import assert from 'node:assert/strict'
import { chromium } from '@playwright/test'

const origin = process.env.RS_UI_ORIGIN ?? 'http://127.0.0.1:5173'
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage()
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
try {
  await page.goto(`${origin}/app/camere`)
  await page.getByLabel('Utilizator').fill(process.env.RS_UI_USER ?? '')
  await page.getByLabel('Parolă').fill(process.env.RS_UI_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Intră' }).click()
  await page.getByRole('heading', { name: 'Verificare în doi pași' }).waitFor()
  await page.getByLabel('Cod din aplicația de autentificare').fill(process.env.RS_UI_TOTP ?? '')
  await page.getByRole('button', { name: 'Verifică' }).click()
  await page.waitForURL('**/app/camere')
  await page.goto(`${origin}/app/camere`)
  await page.getByRole('heading', { name: 'Autostradă demo' }).waitFor()
  const cameraCard = page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: 'Autostradă demo' }) })
  await cameraCard.getByRole('button', { name: 'Detalii live' }).click()
  await page.getByRole('heading', { name: /Stare și analize/ }).waitFor()
  await page.getByRole('region', { name: 'Previzualizare video cu detecții' }).getByText('RECORDED REPLAY').waitFor()
  await page.getByText('YOLOX-S ONNX / Supervision ByteTrack').waitFor()
  await page.getByText('P95 inferență').waitFor()
  const preview = page.getByTestId('camera-live-preview')
  await preview.waitFor()
  await page.waitForFunction(() => {
    const frame = document.querySelector('[data-testid="camera-live-preview"]')
    return frame instanceof HTMLImageElement && frame.complete && frame.naturalWidth > 0 && frame.dataset.capturedAt
  }, null, { timeout: 20000 })
  const firstFrameAt = await preview.getAttribute('data-captured-at')
  await page.waitForFunction(
    (first) => document.querySelector('[data-testid="camera-live-preview"]')?.getAttribute('data-captured-at') !== first,
    firstFrameAt,
    { timeout: 20000 },
  )
  const freshFrameAt = await preview.getAttribute('data-captured-at')
  assert.notEqual(freshFrameAt, firstFrameAt, 'expected a changing annotated frame from the worker')
  const screenshotPath = process.env.RS_E2E_SCREENSHOT
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  const telemetry = page.getByTestId('camera-reported-at')
  await telemetry.waitFor()
  const firstHeartbeat = await telemetry.textContent()
  const waitStarted = Date.now()
  await page.waitForFunction(
    (first) => document.querySelector('[data-testid="camera-reported-at"]')?.textContent !== first,
    firstHeartbeat,
    { timeout: 20000 },
  )
  const heartbeatRefreshMs = Date.now() - waitStarted
  const detections = Number(await page.getByTestId('camera-detections').textContent())
  assert.ok(detections > 0, `expected real detection count, got ${detections}`)
  await page.waitForFunction(
    () => Number.parseInt(document.querySelector('[data-testid="camera-crossings"]')?.textContent ?? '0', 10) > 0,
    null,
    { timeout: 50000 },
  )
  const crossings = Number.parseInt(await page.getByTestId('camera-crossings').textContent(), 10)
  const syntheticAlertId = process.env.RS_SYNTHETIC_ALERT_ID
  assert.ok(syntheticAlertId, 'expected explicit synthetic review alert id')
  await page.goto(`${origin}/app/alerte/${syntheticAlertId}`)
  await page.getByText('SYNTHETIC TEST: deterministic wrong-way scenario', { exact: true }).waitFor()
  await page.waitForFunction(() => {
    const video = document.querySelector('video')
    return video instanceof HTMLVideoElement && video.readyState >= 2 && video.videoWidth > 0
  }, null, { timeout: 15000 })
  await page.getByRole('button', { name: 'Respinge', exact: true }).click()
  await page.getByLabel('Motiv (obligatoriu)').fill('SYNTHETIC TEST: browser review verification')
  await page.getByRole('button', { name: 'Continuă: respinge alerta' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Respinge alerta' }).click()
  await page.getByText('Alertă respinsă').waitFor()
  const reviewScreenshot = process.env.RS_E2E_ALERT_SCREENSHOT
  if (reviewScreenshot) await page.screenshot({ path: reviewScreenshot, fullPage: true })
  await page.goto(`${origin}/app/camere`)
  await page.getByRole('heading', { name: 'Camere din România' }).waitFor()
  await page.getByRole('heading', { name: 'Calea București / Toamnei / 15 Noiembrie' }).waitFor()
  await page.getByText('35 intrări · 0 analize active').waitFor()
  assert.deepEqual(errors, [], `browser errors: ${errors.join('; ')}`)
  console.log(`REAL_API_CAMERA_DETAIL_OK detections=${detections} crossings=${crossings} heartbeat_refresh_ms=${heartbeatRefreshMs}`)
  console.log(`REAL_API_ANNOTATED_PREVIEW_OK frame_at=${freshFrameAt} screenshot=${screenshotPath ?? 'not-saved'}`)
  console.log(`REAL_API_SYNTHETIC_ALERT_REVIEW_OK id=${syntheticAlertId} status=rejected`)
  console.log('REAL_ROMANIAN_CATALOG_OK entries=35 enabled=0')
} finally {
  await browser.close()
}
