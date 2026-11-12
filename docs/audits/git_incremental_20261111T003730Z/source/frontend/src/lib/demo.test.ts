import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Alert } from '@/types'
import { PRELOAD_FIRST, preloadClips, preloadReady } from './demo'

describe('preloadReady (post-login overlay)', () => {
  const waiting = { loaded: true, failed: false, timedOut: false, total: 42, done: 0 }

  it('stays open while the first clips are still loading', () => {
    expect(preloadReady(waiting)).toBe(false)
    expect(preloadReady({ ...waiting, done: PRELOAD_FIRST - 1 })).toBe(false)
  })
  it('closes once the first few clips are ready, not all of them', () => {
    expect(preloadReady({ ...waiting, done: PRELOAD_FIRST })).toBe(true)
  })
  it('needs only as many clips as exist', () => {
    expect(preloadReady({ ...waiting, total: 2, done: 2 })).toBe(true)
    expect(preloadReady({ ...waiting, total: 2, done: 1 })).toBe(false)
  })
  it('closes at once when there is nothing to preload', () => {
    expect(preloadReady({ ...waiting, total: 0 })).toBe(true)
  })
  it('stays open until the alert list has arrived', () => {
    expect(preloadReady({ ...waiting, loaded: false, total: 0 })).toBe(false)
  })
  it('closes when loading failed or the wait ran out, whatever the progress', () => {
    expect(preloadReady({ ...waiting, loaded: false, failed: true })).toBe(true)
    expect(preloadReady({ ...waiting, loaded: false, timedOut: true })).toBe(true)
  })
})

describe('preloadClips', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('downloads two clips at a time, with a timeout signal, and skips failures', async () => {
    let inFlight = 0
    let peak = 0
    const signals: unknown[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      signals.push(init?.signal)
      peak = Math.max(peak, ++inFlight)
      await new Promise((r) => setTimeout(r, 5))
      inFlight--
      return url.includes('broken') ? new Response('', { status: 500 }) : new Response('clip')
    }))
    const progress: [number, number][] = []
    const srcs = ['/m/a.mp4', '/m/broken.mp4', '/m/c.mp4', undefined, '/m/d.mp4', '/m/e.mp4', '/m/a.mp4']

    await preloadClips(srcs, (done, total) => progress.push([done, total]))

    expect(peak).toBe(2)
    expect(signals).toHaveLength(5)
    expect(signals.every((s) => s instanceof AbortSignal)).toBe(true)
    expect(progress[0]).toEqual([0, 5])
    expect(progress.at(-1)).toEqual([5, 5])
  })
})

describe('pitch staging and rejected alerts', () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })
  const alert = (id: string, status: Alert['status'], type: Alert['type'], createdAt: string) =>
    ({ id, status, type, createdAt, severity: 'critical', ruleSummary: '' }) as Alert
  const staged = async () => {
    vi.stubEnv('VITE_DEMO_CURATION', '1')
    vi.resetModules()
    return import('./demo')
  }

  it('puts rejected alerts after every other alert, with or without staging', async () => {
    const list = [
      alert('200', 'rejected', 'probable_crash', '2026-11-09T10:00:00Z'),
      alert('201', 'new', 'congestion', '2026-11-01T10:00:00Z'),
      alert('202', 'confirmed', 'tailgating', '2026-11-02T10:00:00Z'),
    ]
    const plain = await import('./demo')
    expect([...list].sort(plain.demoSort).map((a) => a.id)).toEqual(['202', '201', '200'])
    const demo = await staged()
    expect([...list].sort(demo.demoSort).map((a) => a.id)).toEqual(['202', '201', '200'])
  })
  it('replays a confirmed alert as new, but never a rejected one', async () => {
    const demo = await staged()
    expect(demo.curate(alert('210', 'confirmed', 'very_high_speed', '2026-11-01T10:00:00Z')).status).toBe('new')
    expect(demo.curate(alert('195', 'rejected', 'very_high_speed', '2026-11-01T10:00:00Z')).status).toBe('rejected')
    const decision = { id: '5', at: '', username: 'op', role: 'operator', action: 'rejected' } as const
    expect(demo.keepAudit({ ...decision, target: '195' })).toBe(true)
    expect(demo.keepAudit({ ...decision, target: '210' })).toBe(false)
  })
  it('shows the real age of an alert, never a staged one', async () => {
    const demo = await staged()
    expect(demo.demoAgo(alert('301', 'new', 'congestion', '2020-01-01T10:00:00Z'))).not.toMatch(/ s$/)
  })
})
