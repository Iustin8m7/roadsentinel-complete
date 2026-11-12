import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api'
import { adaptCamera } from './adapters'
import { activate, ageLabel, ATTESTATION_LABEL, cameraAction, configStage, frozenLabel, metric, STATE_LABEL, stateTone, type Runtime, type Worker } from './cameraControl'

afterEach(() => vi.unstubAllGlobals())

describe('camera control client', () => {
  it('sends the expected revision and reason with CSRF on activation', async () => {
    vi.stubGlobal('document', { cookie: '__Secure-rs_csrf=tok' })
    const fetcher = vi.fn().mockResolvedValue(new Response('{"changed":true}', { status: 200 }))
    vi.stubGlobal('fetch', fetcher)
    await activate('cam-1', 'ver-1', 4, 'go live')
    const [url, request] = fetcher.mock.calls[0]
    expect(url).toBe('/api/camera-control/cameras/cam-1/activate')
    expect(request.headers.get('X-CSRF-Token')).toBe('tok')
    expect(JSON.parse(request.body)).toEqual({ version_id: 'ver-1', expected_revision: 4, reason: 'go live' })
  })

  it('exposes the structured 409 conflict code and message', async () => {
    vi.stubGlobal('document', { cookie: '' })
    vi.stubGlobal('location', { pathname: '/app/camere', assign: vi.fn() })
    const body = { detail: { code: 'revision_conflict', message: 'The camera changed', current_revision: 5 } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 409 })))
    const error = await cameraAction('cam-1', 'pause', 4, 'x y z').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('revision_conflict')
    expect((error as ApiError).message).toBe('The camera changed')
  })

  it('never marks a heartbeating replay as live on the camera model', () => {
    const base = { id: 'x', name: 'x', location: null, video_url: null, last_seen_at: new Date().toISOString() }
    expect(adaptCamera({ ...base, source_kind: 'recorded_replay' }).live).toBe(false)
    expect(adaptCamera({ ...base, source_kind: 'authorized_network_live' }).live).toBe(true)
  })

  it('never marks an undeclared source as live, but keeps its heartbeat for the player', () => {
    const base = { id: 'x', name: 'x', location: null, video_url: null, last_seen_at: new Date().toISOString() }
    for (const source_kind of [null, undefined]) {
      expect(adaptCamera({ ...base, source_kind })).toMatchObject({ live: false, heartbeat: true, status: 'online' })
    }
    expect(adaptCamera({ ...base, source_kind: 'owned_optical_live' }).live).toBe(true)
    expect(adaptCamera({ ...base, source_kind: 'recorded_replay' }).heartbeat).toBe(false)
  })

  it('only a fresh live source is labelled LIVE', () => {
    expect(STATE_LABEL.live).toBe('LIVE')
    for (const state of ['replay', 'stale', 'never_seen', 'processing', 'paused']) {
      expect(STATE_LABEL[state]).not.toMatch(/^LIVE/)
      expect(stateTone(state)).not.toBe('live')
    }
    expect(ageLabel(null)).toBe('niciodată')
    expect(ageLabel(30)).toBe('acum 30 s')
  })

  it('runtime failure states are never LIVE and are shown as problems', () => {
    for (const state of ['frozen_image', 'source_mismatch']) {
      expect(STATE_LABEL[state]).toBeTruthy()
      expect(stateTone(state)).toBe('bad')
    }
    expect(ATTESTATION_LABEL.mismatch).toMatch(/^NU/)
  })

  it('formats metrics with units and an em dash when not measured', () => {
    expect(metric(null, 'ms')).toBe('—')
    expect(metric(41.46, 'ms')).toBe('41 ms')
    expect(metric(11.84, 'cadre/s', 1)).toBe('11,8 cadre/s')
    expect(metric(3, '')).toBe('3')
  })

  it('reports the frozen-image check conservatively', () => {
    const none = { frozen_signal: null, frozen_confidence: null, unchanged_s: null }
    expect(frozenLabel('healthy', none)).toBe('nemăsurat')
    expect(frozenLabel('healthy', { frozen_signal: 3.2, frozen_confidence: 0, unchanged_s: 0.1 })).toMatch(/^nu /)
    expect(frozenLabel('healthy', { frozen_signal: 0, frozen_confidence: 0.4, unchanged_s: 30 })).toMatch(/^suspect/)
    expect(frozenLabel('frozen_image', { frozen_signal: 0, frozen_confidence: 0.95, unchanged_s: 30 })).toMatch(/^DA/)
  })
})

describe('where a configuration revision stands', () => {
  const rt = (patch: Partial<Runtime>): Runtime => ({
    state: 'replay', is_live: false, freshness: 'fresh', heartbeat_age_s: 4, stale_after_s: 90, offline_after_s: 600, runnable: true,
    blocked_reason: null, unmet: [], desired_revision: 2, desired_fingerprint: 'a', applied_revision: 2, applied_fingerprint: 'a',
    revision_in_sync: true, reference_frame_mismatch: null, duplicate_worker: false, server_time: '', source_attestation: 'match', ...patch,
  })
  const worker = (patch: Partial<Worker>) => ({ health: 'healthy', last_ack_status: 'accepted', last_ack_revision: 2, last_ack_reason: null, ...patch }) as Worker

  it('says nothing is activated when no revision was requested', () => {
    expect(configStage(rt({ desired_revision: null, applied_revision: null, revision_in_sync: false }), null).stage).toBe('none')
  })
  it('keeps an activated revision apart from an applied one', () => {
    const waiting = configStage(rt({ applied_revision: 1, revision_in_sync: false }), worker({ last_ack_revision: 1 }))
    expect(waiting).toMatchObject({ stage: 'requested', label: 'Cerută, neaplicată încă' })
    expect(waiting.detail).toMatch(/revizia 1/)
    expect(configStage(rt({ applied_revision: null, revision_in_sync: false }), null).detail).toMatch(/niciun worker/)
  })
  it('reports a revision the worker refused, with its reason', () => {
    const refused = configStage(rt({ applied_revision: 1, revision_in_sync: false }), worker({ last_ack_status: 'rejected', last_ack_reason: 'frame_size_mismatch' }))
    expect(refused).toMatchObject({ stage: 'rejected', label: 'Respinsă de worker' })
    expect(refused.detail).toMatch(/frame_size_mismatch/)
  })
  it('calls a revision in effect only while a worker with a fresh signal runs it', () => {
    expect(configStage(rt({}), worker({})).stage).toBe('effective')
    expect(configStage(rt({ freshness: 'stale', state: 'stale' }), worker({}))).toMatchObject({ stage: 'applied', label: 'Aplicată de worker' })
    expect(configStage(rt({ state: 'stopped' }), worker({ health: 'stopped' })).stage).toBe('applied')
    expect(configStage(rt({ state: 'paused' }), worker({})).stage).toBe('applied')
  })
})
