import { describe, expect, it } from 'vitest'
import {
  clientToFrame, defaultConfig, errorTarget, History, localProblems, polygonArea, ruleGates, selfIntersects,
  unitDirection, zoneId, type CameraConfig, type Catalog, type Pt,
} from './cameraConfig'

const CATALOG: Catalog = {
  schema_version: 1, coordinate_convention: 'pixels_top_left', zone_kinds: ['carriageway', 'emergency_lane'],
  vehicle_classes: ['car', 'truck', 'bus', 'motorcycle'],
  rules: [
    { id: 'very_high_speed', needs_calibration: true, min_fps: 5, zone_kinds: [], needs_direction: false },
    { id: 'wrong_way', needs_calibration: true, min_fps: 10, zone_kinds: ['carriageway', 'emergency_lane'], needs_direction: true },
    { id: 'stopped_emergency_lane', needs_calibration: true, min_fps: 5, zone_kinds: ['emergency_lane'], needs_direction: false },
    { id: 'pedestrian_on_road', needs_calibration: false, min_fps: 1, zone_kinds: ['carriageway', 'emergency_lane'], needs_direction: false },
  ],
  thresholds: [
    { id: 'speed_limit_kmh', min: 5, max: 200, integer: false, required: true, default: 50 },
    { id: 'very_high_speed_kmh', min: 5, max: 300, integer: false, required: true, default: 80 },
    { id: 'min_track_age_s', min: 0.2, max: 10, integer: false, required: false, default: null },
  ],
  acquisition: [{ id: 'target_fps', min: 0.5, max: 60, integer: false, required: true, default: 10 }],
  limits: { zones: 32, polygon_points: 64, frame_min: 64, frame_max: 8192 },
}
const FRAME = { width: 1920, height: 1080 }
const square = (x: number, y: number, s: number): Pt[] => [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]
function config(patch: Partial<CameraConfig> = {}): CameraConfig {
  return {
    ...defaultConfig(FRAME, CATALOG, 'yolo11s.pt'),
    zones: [{ id: 'road', name: 'Carosabil', kind: 'carriageway', direction: [0, 1], polygon: square(100, 100, 400) }],
    calibration: { source: [[100, 100], [500, 100], [500, 500], [100, 500]], target_width_m: 7, target_length_m: 30 },
    rules: ['very_high_speed'],
    ...patch,
  }
}

describe('pointer position to reference-frame pixels', () => {
  const rect = { left: 40, top: 20, width: 960, height: 540 } // the 1920x1080 frame shown at half size
  it('scales by the displayed size, whatever the zoom or pixel density', () => {
    expect(clientToFrame(rect, FRAME, 40, 20)).toEqual([0, 0])
    expect(clientToFrame(rect, FRAME, 520, 290)).toEqual([960, 540])
    expect(clientToFrame(rect, FRAME, 1000, 560)).toEqual([1920, 1080])
  })
  it('clamps a pointer outside the picture to the frame edge and returns whole pixels', () => {
    expect(clientToFrame(rect, FRAME, -500, 9000)).toEqual([0, 1080])
    expect(clientToFrame(rect, FRAME, 40.4, 20.4)).toEqual([1, 1])
  })
  it('gives the same frame point for the same spot at two display sizes', () => {
    const big = { left: 0, top: 0, width: 1920, height: 1080 }
    expect(clientToFrame(rect, FRAME, 40 + 240, 20 + 135)).toEqual(clientToFrame(big, FRAME, 480, 270))
  })
})

describe('geometry checks that mirror the server', () => {
  it('measures area and finds crossing edges', () => {
    expect(polygonArea(square(0, 0, 10))).toBe(100)
    expect(selfIntersects(square(0, 0, 10))).toBe(false)
    expect(selfIntersects([[0, 0], [10, 10], [10, 0], [0, 10]])).toBe(true)
  })
  it('accepts a valid config', () => {
    expect(localProblems(config(), CATALOG)).toEqual([])
  })
  it('names the zone and the point that is wrong', () => {
    const bad = config({ zones: [
      { id: 'road', name: 'A', kind: 'carriageway', direction: [0, 1], polygon: [[0, 0], [10, 10], [10, 0], [0, 10]] },
      { id: 'road', name: '', kind: 'carriageway', direction: [0, 0], polygon: [[0, 0], [5000, 0], [0, 50]] },
      { id: 'Bad Id', name: 'C', kind: 'emergency_lane', polygon: [[0, 0], [10, 0]] },
    ] })
    const found = localProblems(bad, CATALOG).map((e) => `${e.path} ${e.code}`)
    expect(found).toEqual(expect.arrayContaining([
      'zones[0].polygon self_intersecting', 'zones[1].id duplicate_id', 'zones[1].name invalid_name',
      'zones[1].direction invalid_direction', 'zones[1].polygon[1] outside_reference_frame',
      'zones[2].id invalid_id', 'zones[2].polygon invalid_polygon',
    ]))
  })
  it('refuses a calibration with three points on one line', () => {
    const bad = config({ calibration: { source: [[0, 0], [10, 0], [20, 0], [0, 10]], target_width_m: 7, target_length_m: 30 } })
    expect(localProblems(bad, CATALOG).map((e) => e.code)).toContain('degenerate_calibration')
  })
  it('requires a direction on a carriageway and at least one zone and one rule', () => {
    const bad = config({ zones: [{ id: 'road', name: 'A', kind: 'carriageway', polygon: square(0, 0, 50) }] })
    expect(localProblems(bad, CATALOG).map((e) => `${e.path} ${e.code}`)).toContain('zones[0].direction required')
    expect(localProblems(config({ zones: [], rules: [] }), CATALOG).map((e) => e.code)).toEqual(expect.arrayContaining(['invalid_zones', 'invalid_rules']))
  })
  it('checks thresholds against the catalogue bounds', () => {
    const bad = config({ thresholds: { speed_limit_kmh: 90, very_high_speed_kmh: 60 } })
    expect(localProblems(bad, CATALOG).map((e) => `${e.path} ${e.code}`)).toContain('thresholds.very_high_speed_kmh inconsistent')
    const low = config({ thresholds: { speed_limit_kmh: 1, very_high_speed_kmh: 80 } })
    expect(localProblems(low, CATALOG).map((e) => `${e.path} ${e.code}`)).toContain('thresholds.speed_limit_kmh out_of_range')
  })
})

describe('why a rule cannot be switched on', () => {
  it('lists every missing prerequisite', () => {
    const c = config({ calibration: null, zones: [{ id: 'road', name: 'A', kind: 'carriageway', polygon: square(0, 0, 50) }], acquisition: { target_fps: 6 } })
    const gates = ruleGates(c, CATALOG)
    expect(gates.very_high_speed).toEqual(['calibration_required'])
    expect(gates.wrong_way).toEqual(['calibration_required', 'unsupported_at_fps', 'direction_required'])
    expect(gates.stopped_emergency_lane).toEqual(['calibration_required', 'zone_required'])
    expect(gates.pedestrian_on_road).toEqual([])
  })
  it('opens the rule once the prerequisites exist', () => {
    expect(ruleGates(config({ acquisition: { target_fps: 12 } }), CATALOG).wrong_way).toEqual([])
  })
})

describe('helpers', () => {
  it('builds a starting config from the catalogue defaults', () => {
    const c = defaultConfig(FRAME, CATALOG, 'yolo11s.pt')
    expect(c.reference_frame).toEqual({ width: 1920, height: 1080, coordinate_convention: 'pixels_top_left' })
    expect(c.thresholds).toEqual({ speed_limit_kmh: 50, very_high_speed_kmh: 80 })
    expect(c.acquisition).toEqual({ target_fps: 10 })
    expect(c.zones).toEqual([])
  })
  it('makes a valid, unused zone id from a name', () => {
    expect(zoneId('Carosabil sens Nord', [])).toBe('carosabil_sens_nord')
    expect(zoneId('Bandă de urgență', ['banda_de_urgenta'])).toBe('banda_de_urgenta_2')
    expect(zoneId('###', [])).toBe('zona')
  })
  it('stores a direction as a unit vector with two decimals', () => {
    expect(unitDirection([0, -37])).toEqual([0, -1])
    expect(unitDirection([10, 10])).toEqual([0.71, 0.71])
    expect(unitDirection([0, 0])).toBeNull()
  })
  it('maps a server error path to the shape or field it is about', () => {
    expect(errorTarget('zones[2].polygon[5]')).toEqual({ kind: 'zone', index: 2, vertex: 5 })
    expect(errorTarget('zones[0].direction')).toEqual({ kind: 'zone', index: 0 })
    expect(errorTarget('calibration.source[1]')).toEqual({ kind: 'calibration', vertex: 1 })
    expect(errorTarget('rules[3]')).toEqual({ kind: 'rule', index: 3 })
    expect(errorTarget('thresholds.speed_limit_kmh')).toEqual({ kind: 'threshold', id: 'speed_limit_kmh' })
    expect(errorTarget('acquisition.target_fps')).toEqual({ kind: 'acquisition', id: 'target_fps' })
    expect(errorTarget('min_y')).toEqual({ kind: 'limit' })
    expect(errorTarget('model.id')).toEqual({ kind: 'model' })
  })
  it('undoes and redoes edits, and drops the redo branch after a new edit', () => {
    const h = new History<number>(1)
    h.push(2); h.push(3)
    expect(h.undo()).toBe(2)
    expect(h.undo()).toBe(1)
    expect(h.undo()).toBeNull()
    expect(h.redo()).toBe(2)
    h.push(9)
    expect(h.redo()).toBeNull()
    expect(h.current).toBe(9)
    expect(h.canUndo && !h.canRedo).toBe(true)
  })
})
