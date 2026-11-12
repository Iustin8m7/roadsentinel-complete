import { afterEach, describe, expect, it, vi } from 'vitest'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const event = (status: 'new' | 'confirmed') => ({
  id: 195, camera_id: 'demo-highway', camera_name: null, location: null, type: 'very_high_speed', priority: 'high',
  occurred_at: '2026-10-18T13:05:58', video_t: 1, track_id: 3, object_class: 'car', speed_kmh: 133.1, rule: '', details: {},
  keyframe_url: null, clip_url: null, vlm_status: 'unavailable', vlm_text: null, status, action: null,
  audit: status === 'confirmed' ? [{ id: 9, at: '2026-11-10T12:00:00Z', actor: 'admin', action: 'confirmed', note: null }] : [],
})

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('deciding a replayed alert', () => {
  it('shows the decision when the backend accepts it, as it does when the backend already holds one', async () => {
    vi.stubEnv('VITE_DEMO_CURATION', '1')
    vi.resetModules()
    vi.stubGlobal('document', { cookie: '__Secure-rs_csrf=t' })
    vi.stubGlobal('location', { pathname: '/app', assign: vi.fn() })
    vi.stubGlobal('fetch', vi.fn(async () => json(event('confirmed'))))
    const { decide, upsertAlert, useDataStore } = await import('./data')
    const { adaptEvent } = await import('@/lib/adapters')
    upsertAlert(adaptEvent(event('new') as never))
    await decide('195', 'confirm')
    expect(useDataStore.getState().alerts.find((a) => a.id === '195')?.status).toBe('confirmed')
  })
})
