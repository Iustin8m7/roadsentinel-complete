// Quick visual check: mock build, admin session, screenshots of selected routes (desktop 1440 / mobile 390, dark / light).
// Usage: node e2e/shots.mjs [--nobuild] [--out dir] [--only login,queue,...] [--themes dark,light] [--motion]
import { spawnSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'
import { preview } from 'vite'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > -1 ? process.argv[i + 1] : d }
const out = path.resolve(arg('--out', path.join(root, '../docs/design/screens-wow')))
const only = arg('--only', '')?.split(',').filter(Boolean)
const themes = arg('--themes', 'dark,light').split(',')
const vps = arg('--vps', 'desktop,mobile').split(',')
mkdirSync(out, { recursive: true })
process.env.PLAYWRIGHT_BROWSERS_PATH ??= path.join(root, 'node_modules/.pw-browsers')
if (!process.argv.includes('--nobuild')) {
  const r = spawnSync('npx', ['vite', 'build', '--outDir', 'dist-mock', '--emptyOutDir'], { cwd: root, env: { ...process.env, VITE_USE_MOCKS: '1' }, stdio: 'pipe' })
  if (r.status !== 0) { console.error(String(r.stderr) + String(r.stdout)); process.exit(1) }
}
const ROUTES = [
  { name: 'login', path: '/login', guest: true }, { name: 'queue', path: '/app' }, { name: 'case', path: '/app/alerte/RS-2026-4101', wait: 900 },
  { name: 'cameras', path: '/app/camere', wait: 700 }, { name: 'archive', path: '/app/arhiva?q=viteza' }, { name: 'archive-empty', path: '/app/arhiva' },
  { name: 'stats', path: '/app/statistici', wait: 1000 }, { name: 'audit', path: '/app/audit' }, { name: 'settings', path: '/app/setari' },
]
const VP = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } }
const srv = await preview({ root, preview: { port: 0, host: '127.0.0.1' }, build: { outDir: 'dist-mock' } })
const origin = srv.resolvedUrls.local[0].replace(/\/$/, '')
const browser = await chromium.launch()
try {
  for (const vpName of vps) for (const theme of themes) {
    const ctx = await browser.newContext({ viewport: VP[vpName], colorScheme: theme, reducedMotion: process.argv.includes('--motion') ? 'no-preference' : 'reduce' })
    const page = await ctx.newPage()
    page.on('pageerror', (e) => console.error('pageerror', e.message))
    page.on('console', (m) => { if (m.type() === 'error') console.error('console', m.text()) })
    await page.goto(`${origin}/login`)
    for (const r of ROUTES.filter((r) => !only?.length || only.includes(r.name))) {
      if (r.guest) { await page.goto(origin + r.path); await page.waitForTimeout(600) }
      else {
        if (page.url().includes('/login')) {
          await page.getByLabel('Utilizator').fill('admin'); await page.getByLabel('Parolă').fill('mock-only-demo')
          await page.getByRole('button', { name: 'Intră' }).click(); await page.waitForURL('**/app')
        }
        await page.goto(origin + r.path, { waitUntil: 'networkidle' }).catch(() => {})
        await page.waitForTimeout(r.wait ?? 500)
      }
      await page.screenshot({ path: path.join(out, `${r.name}-${vpName}-${theme}.png`) })
    }
    await ctx.close()
  }
} finally { await browser.close(); await srv.close() }
console.log('shots written to', out)
