import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, initCsrf, post } from './api'
import { adaptEvent, adaptCamera, adaptAudit, adaptStats, type ApiEvent } from './adapters'
import { hasBackendPermission, ROLE_PERMISSIONS } from './permissions'
import { isDemoCurationEnabled } from './demo'

afterEach(() => vi.unstubAllGlobals())
it('keeps mock operator archive access aligned with the secure backend role', () => {
  expect(ROLE_PERMISSIONS.operator).toContain('archive.search')
})
it('checks camera management against the backend permission set', () => {
  expect(hasBackendPermission(['alerts:read', 'cameras:manage'], 'cameras:manage')).toBe(true)
  expect(hasBackendPermission(['cameras:read'], 'cameras:manage')).toBe(false)
})
it('never enables demo curation for real-backend records', () => {
  expect(isDemoCurationEnabled(false, '1')).toBe(false)
  expect(isDemoCurationEnabled(true, '1')).toBe(true)
  expect(isDemoCurationEnabled(true, undefined)).toBe(false)
})

describe('cookie API contract', () => {
  it('sends credentials and the secure CSRF cookie on decisions', async () => {
    vi.stubGlobal('document', { cookie: 'unrelated=x; __Secure-rs_csrf=token%2D123' })
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetcher)
    await post('/api/events/17/decision', { decision: 'confirm', action: 'monitor' })
    const [, request] = fetcher.mock.calls[0]
    expect(request.credentials).toBe('include')
    expect(request.headers.get('X-CSRF-Token')).toBe('token-123')
    expect(JSON.parse(request.body)).toEqual({ decision: 'confirm', action: 'monitor' })
  })
  it('redirects expired sessions but keeps failed logins on the form', async () => {
    vi.stubGlobal('document', { cookie: '' })
    const assign = vi.fn()
    vi.stubGlobal('location', { pathname: '/alerte', assign })
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve(new Response('{"detail":"Expired"}', { status: 401 }))))
    await expect(api('/api/events')).rejects.toThrow('Expired')
    expect(assign).toHaveBeenCalledWith('/login')
    assign.mockClear()
    vi.stubGlobal('location', { pathname: '/login', assign })
    await expect(post('/api/login', {})).rejects.toThrow('Expired')
    expect(assign).not.toHaveBeenCalled()
  })
  it('tolerates only a missing demo CSRF endpoint', async () => {
    vi.stubGlobal('document', { cookie: '' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 404 })))
    await expect(initCsrf()).resolves.toBeUndefined()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 503 })))
    await expect(initCsrf()).rejects.toThrow('503')
  })
})
const event: ApiEvent = {
  id: 17, camera_id: 'demo', camera_name: 'Demo', location: null, type: 'stopped_on_road',
  priority: 'high', occurred_at: '2026-10-17T10:00:00', video_t: 5, track_id: null, object_class: 'car',
  speed_kmh: null, rule: 'Stopped', details: {}, keyframe_url: '/media/key.jpg', clip_url: '/media/clip.mp4',
  vlm_status: 'skipped', vlm_text: null, status: 'new', action: null,
}
it('preserves contract event types, missing verdict confidence, and media links', () => {
  for (const type of ['wrong_way', 'pedestrian_on_road', 'very_high_speed', 'stopped_emergency_lane', 'stopped_on_road', 'hard_braking', 'tailgating', 'dangerous_lane_change', 'congestion'] as const) {
    const alert = adaptEvent({ ...event, type })
    expect(alert).toMatchObject({ id: '17', type, severity: 'high', status: 'new', keyframeUrl: '/media/key.jpg', vlm: { verdict: 'skipped' } })
    expect(alert.vlm.confidence).toBeUndefined()
  }
})
it('flags low-confidence and uncalibrated speeds and the rules a camera cannot run', () => {
  const alert = adaptEvent({ ...event, speed_kmh: 90, details: { confidence: 'low', speed_calibration: 'unvalidated' } })
  expect(alert.metrics).toMatchObject({ lowConfidence: true, speedApprox: true })
  expect(adaptEvent({ ...event, speed_kmh: 90, details: { speed_calibration: 'validated' } }).metrics).toMatchObject({ lowConfidence: false, speedApprox: false })
  const cam = adaptCamera({ id: 'c', name: 'C', location: null, video_url: null, status_info: { fps: 0.5, rules: { very_high_speed: { supported: false, min_fps: 5, reason: 'necesită ≥ 5.0 cadre/s' }, pedestrian_on_road: { supported: true, min_fps: 0 } } } })
  expect(cam.fps).toBe(0.5)
  expect(cam.unsupportedRules).toEqual([{ rule: 'very_high_speed', reason: 'necesită ≥ 5.0 cadre/s' }])
})
it('adapts camera coordinates, nullable audit event IDs, and server counts', () => {
  expect(adaptCamera({ id: 'a', uuid: 'camera-uuid', timezone: 'Europe/Bucharest', name: 'A', location: null, video_url: null, latitude: 44, longitude: 26, is_active: false })).toMatchObject({ lat: 44, lng: 26, status: 'offline', backendUuid: 'camera-uuid', timezone: 'Europe/Bucharest', isActive: false })
  expect(adaptAudit({ id: 2, event_id: null, actor: 'Operator', action: 'login', note: null, at: 'now' }).target).toBeUndefined()
  expect(adaptStats({ total: 3, by_priority: { critical: 0, high: 3, medium: 0, info: 0 }, by_status: { new: 2, rejected: 1 }, by_type: {}, vlm_available: false })).toMatchObject({ total: 3, open: 2, rejected: 1 })
})

it('adapts persisted live YOLO telemetry and identifies file replay', () => {
  const camera = adaptCamera({
    id: 'local-replay', name: 'Replay', location: 'test', video_url: null,
    last_seen_at: new Date().toISOString(),
    status_info: {
      fps: 2.9, processing_fps: 1.84, detections: 1085, unique_tracks: 67,
      tracks_by_class: { car: 32, bus: 13, truck: 16 },
      inference_latency_ms_p50: 84.57, inference_latency_ms_p95: 93.07, inference_latency_ms_p99: 106.22, process_peak_rss_mb: 447.2,
      model: 'YOLOX-S ONNX / Supervision ByteTrack', model_sha256: 'c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063',
      source: { kind: 'network', state: 'healthy', replay: true, width: 1920, height: 1080 },
      traffic: { total_crossings: 9, rolling_flow_per_minute: { total: 2.5, window_seconds: 60 }, counts_by_line_lane_class: [] },
    },
  })
  expect(camera).toMatchObject({ processingFps: 1.84, detections: 1085, uniqueTracks: 67, inferenceLatencyP95Ms: 93.07 })
  expect(camera.sourceHealth?.replay).toBe(true)
  expect(camera.traffic?.total_crossings).toBe(9)
  expect(camera.inferenceLatencyP99Ms).toBe(106.22)
  expect(camera.processPeakRssMb).toBe(447.2)
})
it('requires declared live provenance in addition to a heartbeat; external playback stays opt-in', () => {
  const recent = new Date(Date.now() - 20_000).toISOString()
  const stale = new Date(Date.now() - 10 * 60_000).toISOString()
  const base = { name: 'P', location: null, video_url: null, is_active: true }
  expect(adaptCamera({ ...base, id: 'iasi-piata-unirii', last_seen_at: recent })).toMatchObject({ status: 'online', live: false, liveUrl: undefined })
  expect(adaptCamera({ ...base, id: 'iasi-piata-unirii', last_seen_at: stale })).toMatchObject({ status: 'degraded', live: false })
  expect(adaptCamera({ ...base, id: 'x', source_kind: 'authorized_network_live', last_seen_at: recent })).toMatchObject({status:'online',live:true})
  expect(adaptCamera({ ...base, id: 'x', last_seen_at: null })).toMatchObject({ live: false, liveUrl: undefined })
  expect(adaptCamera({ ...base, id: 'stalled', last_seen_at: recent, status_info: { source: { kind: 'network', state: 'stale' } } })).toMatchObject({ status: 'degraded', live: false })
})
it('labels seeded demo data as synthetic instead of claiming redaction', () => {
  expect(adaptEvent({ ...event, redaction: 'full', details: { synthetic: true, source: 'app.services.seed' } }).redaction).toBe('synthetic')
  expect(adaptEvent({ ...event, redaction: 'full', details: { synthetic: true } }).redaction).toBe('full')
  expect(adaptEvent({ ...event, redaction: 'full', details: {} }).redaction).toBe('full')
})
