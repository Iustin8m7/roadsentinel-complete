import { describe, expect, it } from 'vitest'
import { adaptEvent, type ApiEvent } from './adapters'

const event: ApiEvent = {
  id: 1, camera_id: 'fixture', camera_name: 'Licensed replay', location: null,
  type: 'pedestrian_on_road', priority: 'critical', occurred_at: '2026-11-10T00:00:00Z',
  video_t: 1, track_id: 2, object_class: 'person', speed_kmh: null,
  rule: 'Person detected in a configured test zone', details: {}, keyframe_url: null,
  clip_url: null, vlm_status: 'skipped', vlm_text: null, status: 'new', action: null,
  redaction: 'full',
}
describe('source disclosure for synthetic scenarios with real licensed pixels', () => {
  it.each([
    ['recorded_upload', '[RECORDED]'],
    ['local_replay', '[LOCAL RECORDED REPLAY]'],
    ['live_camera', '[LIVE]'],
    ['unknown', '[SOURCE UNVERIFIED]'],
  ])('keeps both the synthetic marker and %s origin', (origin, label) => {
    const adapted = adaptEvent({...event, details: {synthetic: true, origin}})
    expect(adapted.ruleSummary).toContain('[SYNTHETIC TEST]')
    expect(adapted.ruleSummary).toContain(label)
    expect(adapted.redaction).toBe('full')
  })
  it('does not label ordinary recorded evidence synthetic', () => {
    expect(adaptEvent({...event, details:{origin:'recorded_upload'}}).ruleSummary).toBe('[RECORDED] '+event.rule)
  })
})
