import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'

const base = process.env.RS_E2E_URL
const screenshotDir = process.env.RS_E2E_SCREENSHOT_DIR
if (!base || !screenshotDir) throw new Error('RS_E2E_URL and RS_E2E_SCREENSHOT_DIR are required')
await fs.mkdir(screenshotDir, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } })
const page = await context.newPage()
const consoleErrors = []
const analyticsResponses = []
page.on('pageerror', (error) => consoleErrors.push(error.message))
page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
page.on('response', async (response) => {
  const url = response.url()
  if (url.includes('/analytics/')) {
    let body = null
    if (response.ok() && !url.endsWith('/frame')) {
      try { body = await response.json() } catch { /* capture status separately */ }
    }
    analyticsResponses.push({ url, status: response.status(), body })
  }
})

try {
  await page.goto(`${base}/app/analiza-video`, { waitUntil: 'networkidle' })
  await page.getByLabel('Utilizator').fill(process.env.RS_E2E_EMAIL)
  await page.getByLabel('Parolă').fill(process.env.RS_E2E_PASSWORD)
  await page.getByRole('button', { name: 'Intră' }).click()
  await page.getByLabel('Cod din aplicația de autentificare').fill(process.env.RS_E2E_TOTP)
  await page.getByRole('button', { name: 'Verifică' }).click()
  await page.getByRole('heading', { name: 'Analiză video înregistrată' }).waitFor()
  await page.getByRole('tab', { name: /Heatmap și analitice/ }).click()

  const frame = page.getByAltText(/Cadru de referință redacted/)
  await frame.waitFor({ state: 'visible' })
  await page.waitForFunction(() => {
    const image = document.querySelector('img[alt^="Cadru de referință"]')
    const canvas = document.querySelector('canvas[aria-label^="Heatmap"]')
    if (!(image instanceof HTMLImageElement) || !(canvas instanceof HTMLCanvasElement)) return false
    if (!image.complete || image.naturalWidth < 64 || canvas.width < 16) return false
    const pixels = canvas.getContext('2d')?.getImageData(0, 0, canvas.width, canvas.height).data
    return Boolean(pixels && pixels.some((value, index) => index % 4 === 3 && value > 0))
  }, { timeout: 30000 })
  await page.getByRole('heading', { name: 'Densitate spațială a observațiilor' }).waitFor()
  await page.getByRole('heading', { name: 'Activitate în timpul sursei' }).waitFor()
  await page.getByText(/Procesare măsurată/).waitFor()
  const initial = analyticsResponses.find((item) => item.url.includes('/heatmap?') && item.status === 200)?.body
  if (!initial || initial.included_observations <= 0) throw new Error('Real authenticated heatmap payload is empty')
  const summaryPayload = analyticsResponses.find((item) => item.url.endsWith('/summary') && item.status === 200)?.body
  if (!Number.isFinite(summaryPayload?.inference_fps) || summaryPayload.inference_fps <= 0) {
    throw new Error('Measured processing FPS is missing or not positive')
  }
  const naturalWidth = await frame.evaluate((image) => image.naturalWidth)
  const initialPixels = await page.locator('canvas[aria-label^="Heatmap"]').evaluate((canvas) => {
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data
    return data.reduce((sum, value, index) => sum + (index % 4 === 3 ? value : 0), 0)
  })
  await page.getByRole('heading', { name: 'Densitate spațială a observațiilor' }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(screenshotDir, 'analytics-all.png'), fullPage: true })

  const carResponsePromise = page.waitForResponse((response) =>
    response.url().includes('/heatmap?') && response.url().includes('classes=car') && response.status() === 200,
  )
  await page.getByRole('button', { name: 'Toate' }).click()
  const car = await carResponsePromise.then((response) => response.json())
  await page.screenshot({ path: path.join(screenshotDir, 'analytics-car.png'), fullPage: true })

  const start = page.getByRole('spinbutton', { name: 'Început interval sursă' })
  const end = page.getByRole('spinbutton', { name: 'Sfârșit interval sursă' })
  await start.fill('0')
  const narrowResponsePromise = page.waitForResponse((response) =>
    response.url().includes('/heatmap?') && response.url().includes('end_s=5') && response.status() === 200,
  )
  await end.fill('5')
  await end.press('Tab')
  const narrow = await narrowResponsePromise.then((response) => response.json())

  const opacity = page.getByRole('slider', { name: /Opacitate heatmap/ })
  await opacity.press('Home')
  await page.waitForTimeout(100)
  const zeroAlpha = await page.locator('canvas[aria-label^="Heatmap"]').evaluate((canvas) => {
    const d = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data
    return d.reduce((n, v, i) => n + (i % 4 === 3 ? v : 0), 0)
  })
  await opacity.press('End')
  await page.waitForTimeout(100)
  const highAlpha = await page.locator('canvas[aria-label^="Heatmap"]').evaluate((canvas) => {
    const d = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data
    return d.reduce((n, v, i) => n + (i % 4 === 3 ? v : 0), 0)
  })
  if (!(zeroAlpha < highAlpha)) throw new Error('Opacity control did not change rendered heatmap alpha')

  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(200)
  const mobileCanvasWidth = await page.locator('canvas[aria-label^="Heatmap"]').evaluate((canvas) => canvas.getBoundingClientRect().width)
  if (mobileCanvasWidth < 300) throw new Error(`Mobile heatmap width is unexpectedly small: ${mobileCanvasWidth}`)
  await page.screenshot({ path: path.join(screenshotDir, 'analytics-mobile.png'), fullPage: true })

  const analyticsPath = new URL(analyticsResponses.find((item) => item.url.includes('/heatmap?')).url).pathname.split('/')
  const recordingId = analyticsPath[3]
  const runId = analyticsPath[5]
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: new RegExp(runId) }).waitFor()
  await page.getByRole('button', { name: new RegExp(runId) }).click()
  await page.getByRole('tab', { name: /Heatmap și analitice/ }).click()
  await page.getByRole('heading', { name: 'Densitate spațială a observațiilor' }).waitFor()
  await page.waitForFunction(() => {
    const image = document.querySelector('img[alt^="Cadru de referință"]')
    return image instanceof HTMLImageElement && image.complete && image.naturalWidth >= 64
  }, { timeout: 30000 })
  const restoredFrameWidth = await page.getByAltText(/Cadru de referință redacted/).evaluate((image) => image.naturalWidth)
  if (restoredFrameWidth < 64) throw new Error('Persisted analytics did not reload a real frame')

  const noAuth = await context.browser().newContext()
  const response = await noAuth.request.get(`${base}/api/recordings`)
  if (response.status() !== 401) throw new Error(`Unauthenticated API expected 401, got ${response.status()}`)
  await noAuth.close()
  if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(' | ')}`)

  console.log(JSON.stringify({
    result: 'REAL_AUTHENTICATED_BROWSER_ANALYTICS_PASS',
    recordingId,
    runId,
    imageNaturalWidth: naturalWidth,
    initialObservations: initial.included_observations,
    measuredProcessingFps: summaryPayload.inference_fps,
    initialHeatmapNonzero: initial.values.filter((value) => value > 0).length,
    initialCanvasAlphaSum: initialPixels,
    carOnlyObservations: car.included_observations,
    narrowWindowObservations: narrow.included_observations,
    opacityAlphaAtZero: zeroAlpha,
    opacityAlphaAtHigh: highAlpha,
    mobileCanvasWidth,
    persistedReloadNaturalWidth: restoredFrameWidth,
    unauthenticatedStatus: response.status(),
    analyticsResponses: analyticsResponses.map(({ url, status }) => ({ path: new URL(url).pathname, status })),
    screenshots: ['analytics-all.png', 'analytics-car.png', 'analytics-mobile.png'].map((name) => path.join(screenshotDir, name)),
    consoleErrors,
  }))
} finally {
  await context.close()
  await browser.close()
}
