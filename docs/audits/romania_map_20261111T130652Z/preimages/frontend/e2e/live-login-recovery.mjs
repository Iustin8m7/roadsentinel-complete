// Actual integration runtime only. Secrets stay in mode-0600 local artifacts, never logs/traces.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'
import { chromium, expect } from '@playwright/test'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const origin = 'http://127.0.0.1:5175'
const credentials = JSON.parse(fs.readFileSync(path.join(root, 'backend/.integration-test-credentials.json'), 'utf8'))
if (credentials.database !== 'rsint_20261110b') throw new Error('Wrong credential database')
const privateDir = path.join(root, 'backend/.integration-authenticators')
fs.mkdirSync(privateDir, { recursive: true, mode: 0o700 })
fs.chmodSync(privateDir, 0o700)
const secretFile = path.join(privateDir, 'authenticators.json')
const secrets = fs.existsSync(secretFile) ? JSON.parse(fs.readFileSync(secretFile, 'utf8')) : {}
const output = process.env.RS_LIVE_EVIDENCE_DIR ? path.resolve(process.env.RS_LIVE_EVIDENCE_DIR) : path.join(root, 'docs/audits/runtime_verification')
if (!output.startsWith(root + path.sep)) throw new Error('Evidence must stay inside integration workspace')
fs.mkdirSync(path.join(output, 'screenshots'), { recursive: true })
const report = { runtime: 'A: existing 5175 -> 8003 -> rsint_20261110b:55446', accounts: [], requests: [], errors: [] }
const python = path.join(root, '.venv.integration/bin/python')
function totp(secret) {
  return execFileSync(python, ['-c', 'import sys,pyotp; print(pyotp.TOTP(sys.stdin.read()).now())'], { input: secret, encoding: 'utf8' }).trim()
}
function save() {
  fs.writeFileSync(secretFile, JSON.stringify(secrets, null, 2), { mode: 0o600 })
  fs.chmodSync(secretFile, 0o600)
}
async function codeFor(email) {
  const value = secrets[email]
  if (!value?.secret) throw new Error('No local authenticator; physical MFA input required')
  while (Math.floor(Date.now()/30000) <= (value.lastUsedStep ?? -1)) await new Promise(r => setTimeout(r, 1000))
  const code = totp(value.secret)
  value.lastUsedStep = Math.floor(Date.now()/30000)
  save()
  return code
}
function redact(message) {
  let text = String(message).replaceAll(credentials.password, '<redacted>')
  for (const value of Object.values(secrets)) {
    text = text.replaceAll(value.secret, '<redacted>')
    for (const code of value.recovery_codes ?? []) text = text.replaceAll(code, '<redacted>')
  }
  return text
}
const browser = await chromium.launch({ headless: true })
async function login(role, expectedRole, invalid = false) {
  const email = credentials.accounts[role]
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  page.on('pageerror', error => report.errors.push(redact(error.message)))
  page.on('response', response => {
    const url = new URL(response.url())
    if (url.pathname.startsWith('/api/')) report.requests.push({ role, method: response.request().method(), path: url.pathname, status: response.status() })
  })
  await page.goto(origin + '/login')
  await page.screenshot({path:path.join(output,'screenshots',`login-${expectedRole}.png`)})
  await page.locator('input[name="username"]').fill(email)
  if (invalid) {
    await page.locator('input[name="password"]').fill(credentials.password + '!invalid')
    const rejected = page.waitForResponse(r => new URL(r.url()).pathname === '/api/login')
    await page.getByRole('button', { name: 'Intră', exact: true }).click()
    expect((await rejected).status()).toBe(401)
    await expect(page.getByRole('alert')).toContainText('Invalid credentials')
  }
  await page.locator('input[name="password"]').fill(credentials.password)
  const passwordStep = page.waitForResponse(r => new URL(r.url()).pathname === '/api/login')
  const enrollmentStart = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/mfa/enroll/start')).catch(() => null)
  await page.getByRole('button', { name: 'Intră', exact: true }).click()
  const passwordResponse = await passwordStep
  expect(passwordResponse.status()).toBe(200)
  const result = await passwordResponse.json()
  expect(result.mfa_required).toBe(true)
  expect((await page.request.get(origin+'/api/auth/me')).status()).toBe(401)
  if (!result.mfa_enrollment) {
    await page.screenshot({path:path.join(output,'screenshots',`mfa-${expectedRole}.png`),mask:[page.locator('input[name="code"]')]})
    if (invalid) {
      const actual = totp(secrets[email].secret)
      const wrong = String((Number(actual)+1)%1000000).padStart(6,'0')
      await page.locator('input[name="code"]').fill(wrong)
      const denied=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/mfa/verify'))
      await page.getByRole('button',{name:'Verifică',exact:true}).click()
      expect((await denied).status()).toBe(401)
      expect((await page.request.get(origin+'/api/auth/me')).status()).toBe(401)
    }
  }
  if (result.mfa_enrollment) {
    const started = await enrollmentStart
    if (!started) throw new Error('Enrollment did not start')
    const setup = await started.json()
    if (!/^[A-Z2-7]+$/.test(setup.secret) || !setup.qr_svg_data_uri.startsWith('data:image/svg+xml;base64,')) throw new Error('Invalid enrollment response')
    await expect(page.getByAltText('Cod QR pentru configurarea aplicației de autentificare')).toBeVisible()
    await page.locator('input[name="enrollment_code"]').fill(totp(setup.secret))
    const confirmation = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/mfa/enroll/confirm'))
    await page.getByRole('button', { name: 'Activează și continuă', exact: true }).click()
    const confirmed = await confirmation
    expect(confirmed.status()).toBe(200)
    const recovery = await confirmed.json()
    expect(recovery.recovery_codes.length).toBe(8)
    await expect(page.getByRole('heading', { name: 'Salvează codurile de recuperare' })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/login')
    secrets[email] = { secret: setup.secret, otpauth_uri: setup.otpauth_uri, recovery_codes: recovery.recovery_codes, lastUsedStep: Math.floor(Date.now()/30000) }
    save()
    fs.writeFileSync(path.join(privateDir, email.split('@')[0] + '.html'), `<!doctype html><meta charset="utf-8"><title>RoadSentinel development authenticator</title><h1>${email}</h1><p>Private development MFA setup. Scan this QR with your authenticator. Do not share this file.</p><img width="280" src="${setup.qr_svg_data_uri}"><p>Manual setup key: <code>${setup.secret}</code></p>`, { mode: 0o600 })
    await page.getByRole('button', { name: 'Am salvat codurile, continuă', exact: true }).click()
  } else {
    await page.locator('input[name="code"]').fill(await codeFor(email))
    await page.getByRole('button', { name: 'Verifică', exact: true }).click()
  }
  const landing = expectedRole === 'auditor' ? '/app/audit' : '/app'
  await page.waitForURL(origin + landing)
  const me = await page.request.get(origin + '/api/auth/me')
  expect(me.status()).toBe(200)
  expect((await me.json()).role).toBe(expectedRole)
  await page.reload()
  await page.waitForURL(origin + landing)
  await expect(page.getByRole('button', { name: 'Meniu utilizator' })).toContainText(email)
  const alerts = await page.request.get(origin + '/api/events')
  expect(alerts.status()).toBe(expectedRole === 'auditor' ? 403 : 200)
  const users = await page.request.get(origin + '/api/users')
  expect(users.status()).toBe(expectedRole === 'tenant_admin' ? 200 : 403)
  const audit = await page.request.get(origin + '/api/audit/verify')
  expect(audit.status()).toBe(['tenant_admin', 'auditor'].includes(expectedRole) ? 200 : 403)
  if (expectedRole === 'auditor') {
    await expect(page.getByRole('table').locator('tbody tr').first()).toBeVisible()
  } else {
    await expect(page.getByLabel('Se încarcă alertele')).toHaveCount(0)
    await expect(page.getByRole('heading',{name:'Coada de alerte',exact:true})).toBeVisible()
  }
  await page.screenshot({ path: path.join(output, 'screenshots', `live-${expectedRole}.png`), fullPage: true })
  const tab=await context.newPage()
  await tab.goto(origin+landing)
  await expect(tab.getByRole('button',{name:'Meniu utilizator'})).toContainText(email)
  expect((await tab.request.get(origin+'/api/auth/me')).status()).toBe(200)
  await tab.close()
  if (expectedRole !== 'tenant_admin') {
    await page.goto(origin+'/app/setari')
    await expect(page.getByRole('heading',{name:'Acces restricționat',exact:true})).toBeVisible()
    await page.goto(origin+landing)
  }
  await page.getByRole('button', { name: 'Meniu utilizator' }).click()
  await page.getByRole('menuitem', { name: 'Deconectare' }).click()
  await page.waitForURL(origin + '/login')
  expect((await page.request.get(origin + '/api/auth/me')).status()).toBe(401)
  await expect(page.getByRole('heading',{name:'Autentificare',exact:true})).toBeVisible()
  const attempted=page.waitForRequest(r=>r.isNavigationRequest() && new URL(r.url()).pathname===landing)
  const guestBoot=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/me' && r.request().resourceType()==='fetch')
  await page.evaluate(target=>{window.location.href=target},origin+landing)
  await attempted
  expect((await (await guestBoot).json()).operator).toBeNull()
  await page.waitForURL(origin+'/login')
  await expect(page.getByRole('heading',{name:'Autentificare',exact:true})).toBeVisible()
  await page.screenshot({path:path.join(output,'screenshots',`logout-${expectedRole}.png`)})
  report.accounts.push({ email, role: expectedRole, passwordAccepted: true, enrolledInThisRun: result.mfa_enrollment, refreshPreservedSession: true, dashboardDataLoaded: true, logoutRevokedSession: true, destination: landing })
  fs.writeFileSync(path.join(output, 'live-browser-result.json'), JSON.stringify(report, null, 2))
  await context.close()
  console.log(`PASS existing integration: ${expectedRole}, MFA, dashboard/role destination, refresh, RBAC and logout`)
}
try {
  await login('Operator', 'operator', true)
  await login('Administrator', 'tenant_admin')
  await login('Patrol', 'patrol')
  await login('Auditor', 'auditor')
  await login('Operator', 'operator') // enrolled challenge as well as first-login QR flow
  expect(report.errors).toEqual([])
} catch (error) {
  fs.writeFileSync(path.join(output, 'live-browser-result.json'), JSON.stringify({ ...report, failure: redact(error.message) }, null, 2))
  console.error(redact(error.message))
  process.exitCode = 1
} finally {
  await browser.close()
}
