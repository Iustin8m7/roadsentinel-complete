// Camera configuration (schema v1) as the visual editor handles it.
//
// Coordinates are whole pixels of the reference frame (x right, y down, origin top-left): the same
// domain the server validator and the worker use. The checks here mirror
// backend/app/services/camera_config.py so a problem shows on the shape while it is drawn; the server
// stays the authority and its answer is shown as well.
import { api } from './api'
import type { ConfigError } from './cameraControl'

export type Pt = [number, number]
export interface Zone { id: string; name: string; kind: string; direction?: Pt | null; polygon: Pt[] }
export interface Calibration { source: Pt[]; target_width_m: number; target_length_m: number }
export interface Frame { width: number; height: number }
export interface CameraConfig {
  schema_version: number
  reference_frame: Frame & { coordinate_convention?: string }
  calibration: Calibration | null
  min_y: number | null
  zones: Zone[]
  counting_lines?: { id: string; points: [Pt, Pt]; lane?: string }[]
  rules: string[]
  thresholds: Record<string, number | string[]>
  acquisition: Record<string, number>
  model: { id: string; sha256?: string }
}
export interface RuleSpec { id: string; needs_calibration: boolean; min_fps: number; zone_kinds: string[]; needs_direction: boolean }
export interface Bound { id: string; min: number; max: number; integer: boolean; required: boolean; default: number | null }
export interface Catalog {
  schema_version: number; coordinate_convention: string; zone_kinds: string[]; vehicle_classes: string[]
  rules: RuleSpec[]; thresholds: Bound[]; acquisition: Bound[]
  limits: { zones: number; polygon_points: number; frame_min: number; frame_max: number }
}
export const getCatalog = () => api<Catalog>('/api/camera-control/catalog')

// --------------------------------------------------------------------------- pointer mapping

/** Pointer position (client pixels) to a reference-frame pixel. `rect` is the on-screen box that
 *  shows the whole frame edge to edge, so the result does not depend on zoom, CSS scaling or the
 *  screen's pixel density. Outside the picture the point is clamped to the frame edge. */
export function clientToFrame(rect: { left: number; top: number; width: number; height: number }, frame: Frame, clientX: number, clientY: number): Pt {
  const x = rect.width > 0 ? ((clientX - rect.left) / rect.width) * frame.width : 0
  const y = rect.height > 0 ? ((clientY - rect.top) / rect.height) * frame.height : 0
  return [clamp(Math.round(x), 0, frame.width), clamp(Math.round(y), 0, frame.height)]
}
export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

// --------------------------------------------------------------------------- geometry

export function polygonArea(points: Pt[]): number {
  let sum = 0
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i], [x2, y2] = points[(i + 1) % points.length]
    sum += x1 * y2 - x2 * y1
  }
  return Math.abs(sum / 2)
}
const cross = (o: Pt, a: Pt, b: Pt) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
function segmentsCross(p1: Pt, p2: Pt, q1: Pt, q2: Pt) {
  const d1 = cross(q1, q2, p1), d2 = cross(q1, q2, p2), d3 = cross(p1, p2, q1), d4 = cross(p1, p2, q2)
  return d1 * d2 < 0 && d3 * d4 < 0
}
export function selfIntersects(points: Pt[]): boolean {
  const n = points.length
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue // neighbours through the closing edge
      if (segmentsCross(points[i], points[(i + 1) % n], points[j], points[(j + 1) % n])) return true
    }
  }
  return false
}
export function centroid(points: Pt[]): Pt {
  const n = Math.max(1, points.length)
  return [points.reduce((s, p) => s + p[0], 0) / n, points.reduce((s, p) => s + p[1], 0) / n]
}
/** A direction as the unit vector the config stores (two decimals); null for no direction. */
export function unitDirection(v: Pt): Pt | null {
  const len = Math.hypot(v[0], v[1])
  if (len < 1e-9) return null
  const r = (n: number) => { const x = Math.round((n / len) * 100) / 100; return x === 0 ? 0 : x }
  return [r(v[0]), r(v[1])]
}

// --------------------------------------------------------------------------- checks

const ZONE_ID = /^[a-z0-9_]{1,40}$/
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const isPt = (v: unknown): v is Pt => Array.isArray(v) && v.length === 2 && isNum(v[0]) && isNum(v[1])

/** Problems the editor can see without asking the server, with the server's paths and codes. */
export function localProblems(config: CameraConfig, catalog: Catalog): ConfigError[] {
  const out: ConfigError[] = []
  const add = (path: string, code: string, message: string) => out.push({ path, code, message })
  const { width, height } = config.reference_frame
  for (const [axis, value] of [['width', width], ['height', height]] as const) {
    if (!Number.isInteger(value) || value < catalog.limits.frame_min || value > catalog.limits.frame_max) add(`reference_frame.${axis}`, 'out_of_range', 'dimensiune de cadru nevalidă')
  }
  const lineIds = new Set<string>()
  if ((config.counting_lines?.length ?? 0) > 16) add('counting_lines', 'too_many', 'cel mult 16 linii')
  config.counting_lines?.forEach((line, i) => {
    const path = `counting_lines[${i}]`
    if (!ZONE_ID.test(line.id) || lineIds.has(line.id)) add(`${path}.id`, 'invalid_id', 'identificator invalid sau repetat')
    lineIds.add(line.id)
    if (line.points.length !== 2 || !line.points.every(isPt)) add(`${path}.points`, 'invalid_point', 'linia are nevoie de două puncte')
    else if (line.points[0][0] === line.points[1][0] && line.points[0][1] === line.points[1][1]) add(`${path}.points`, 'degenerate_line', 'punctele trebuie să fie diferite')
    else if (line.points.some(([x, y]) => x < 0 || y < 0 || x > width || y > height)) add(`${path}.points`, 'outside_reference_frame', 'linia trebuie să fie în cadrul de referință')
  })
  const bound = (path: string, value: unknown, b: Bound) => {
    if (!isNum(value) || (b.integer && !Number.isInteger(value))) { add(path, 'invalid_type', b.integer ? 'trebuie să fie un număr întreg' : 'trebuie să fie un număr'); return null }
    if (value < b.min || value > b.max) { add(path, 'out_of_range', `trebuie să fie între ${b.min} și ${b.max}`); return null }
    return value
  }

  const cal = config.calibration
  if (cal) {
    if (!(Array.isArray(cal.source) && cal.source.length === 4 && cal.source.every(isPt))) add('calibration.source', 'invalid_calibration', 'trebuie exact 4 puncte')
    else {
      const p = cal.source
      const collinear = ([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]] as const).some(([a, b, d]) => Math.abs(cross(p[a], p[b], p[d])) < 1e-6)
      if (collinear || selfIntersects(p)) add('calibration.source', 'degenerate_calibration', 'punctele trebuie să formeze un patrulater simplu (fără trei puncte pe aceeași linie)')
    }
    if (!isNum(cal.target_width_m) || cal.target_width_m < 0.5 || cal.target_width_m > 500) add('calibration.target_width_m', 'out_of_range', 'lățimea trebuie să fie între 0,5 și 500 m')
    if (!isNum(cal.target_length_m) || cal.target_length_m < 0.5 || cal.target_length_m > 5000) add('calibration.target_length_m', 'out_of_range', 'lungimea trebuie să fie între 0,5 și 5000 m')
  }
  if (config.min_y != null && (!Number.isInteger(config.min_y) || config.min_y < 0 || config.min_y > height)) add('min_y', 'out_of_range', `trebuie să fie între 0 și ${height}`)

  if (config.zones.length < 1 || config.zones.length > catalog.limits.zones) add('zones', 'invalid_zones', `trebuie între 1 și ${catalog.limits.zones} zone`)
  const seen = new Set<string>()
  config.zones.forEach((zone, i) => {
    const zp = `zones[${i}]`
    if (!ZONE_ID.test(zone.id)) add(`${zp}.id`, 'invalid_id', 'identificatorul poate avea doar litere mici, cifre și „_” (cel mult 40)')
    else if (seen.has(zone.id)) add(`${zp}.id`, 'duplicate_id', `identificatorul „${zone.id}” este folosit de două ori`)
    else seen.add(zone.id)
    if (!(zone.name.trim().length >= 1 && zone.name.trim().length <= 80)) add(`${zp}.name`, 'invalid_name', 'numele trebuie să aibă între 1 și 80 de caractere')
    if (!catalog.zone_kinds.includes(zone.kind)) add(`${zp}.kind`, 'unsupported_value', 'tip de zonă necunoscut')
    if (zone.direction != null) {
      if (!isPt(zone.direction)) add(`${zp}.direction`, 'invalid_point', 'direcția trebuie să aibă două numere')
      else if (zone.direction[0] === 0 && zone.direction[1] === 0) add(`${zp}.direction`, 'invalid_direction', 'direcția nu poate fi [0, 0]')
    } else if (zone.kind === 'carriageway') add(`${zp}.direction`, 'required', 'o zonă de carosabil are nevoie de sensul de mers')
    if (zone.polygon.length < 3 || zone.polygon.length > catalog.limits.polygon_points) { add(`${zp}.polygon`, 'invalid_polygon', `zona trebuie să aibă între 3 și ${catalog.limits.polygon_points} puncte`); return }
    let allPoints = true
    zone.polygon.forEach((p, j) => {
      if (!isPt(p)) { add(`${zp}.polygon[${j}]`, 'invalid_point', 'punct invalid'); allPoints = false }
      else if (p[0] < 0 || p[0] > width || p[1] < 0 || p[1] > height) add(`${zp}.polygon[${j}]`, 'outside_reference_frame', `punctul trebuie să fie în cadrul de ${width}×${height}`)
    })
    if (!allPoints) return
    if (selfIntersects(zone.polygon)) add(`${zp}.polygon`, 'self_intersecting', 'laturile zonei se intersectează')
    else if (polygonArea(zone.polygon) < 1) add(`${zp}.polygon`, 'degenerate_polygon', 'zona nu are suprafață')
  })

  for (const b of catalog.acquisition) bound(`acquisition.${b.id}`, config.acquisition[b.id], b)
  if (config.rules.length === 0) add('rules', 'invalid_rules', 'alegeți cel puțin o regulă')
  const gates = ruleGates(config, catalog)
  config.rules.forEach((rule, i) => {
    if (!catalog.rules.some((r) => r.id === rule)) add(`rules[${i}]`, 'unknown_rule', 'regulă necunoscută')
    else for (const code of gates[rule] ?? []) add(`rules[${i}]`, code, GATE_TEXT[code] ?? code)
  })
  const values: Record<string, number | null> = {}
  for (const b of catalog.thresholds) {
    const value = config.thresholds[b.id]
    if (value === undefined) { if (b.required) add(`thresholds.${b.id}`, 'required', 'prag obligatoriu'); continue }
    values[b.id] = bound(`thresholds.${b.id}`, value, b)
  }
  const limit = values.speed_limit_kmh, veryHigh = values.very_high_speed_kmh
  if (limit != null && veryHigh != null && veryHigh < limit) add('thresholds.very_high_speed_kmh', 'inconsistent', 'trebuie să fie cel puțin cât limita de viteză')
  if (!/^[A-Za-z0-9._/-]{1,120}$/.test(config.model.id) || config.model.id.startsWith('/') || config.model.id.split('/').includes('..')) add('model.id', 'invalid_id', 'referință de model invalidă')
  return out
}

/** For every rule in the catalogue, what is missing before it can run (empty = can be enabled). */
export function ruleGates(config: CameraConfig, catalog: Catalog): Record<string, string[]> {
  const cal = config.calibration
  const hasCalibration = !!cal && cal.source.length === 4 && isNum(cal.target_width_m) && isNum(cal.target_length_m)
  const kinds = new Map<string, boolean>() // kind -> some zone of that kind has a direction
  for (const z of config.zones) {
    if (catalog.zone_kinds.includes(z.kind)) kinds.set(z.kind, (kinds.get(z.kind) ?? false) || (z.direction != null && !(z.direction[0] === 0 && z.direction[1] === 0)))
  }
  const fps = config.acquisition.target_fps
  const out: Record<string, string[]> = {}
  for (const spec of catalog.rules) {
    const missing: string[] = []
    if (spec.needs_calibration && !hasCalibration) missing.push('calibration_required')
    if (isNum(fps) && fps < spec.min_fps) missing.push('unsupported_at_fps')
    if (spec.zone_kinds.length && !spec.zone_kinds.some((k) => kinds.has(k))) missing.push('zone_required')
    else if (spec.needs_direction && !spec.zone_kinds.some((k) => kinds.get(k))) missing.push('direction_required')
    out[spec.id] = missing
  }
  return out
}
export const GATE_TEXT: Record<string, string> = {
  calibration_required: 'necalibrat: are nevoie de calibrarea pixel–metru',
  unsupported_at_fps: 'prea puține cadre pe secundă pentru această regulă',
  zone_required: 'lipsește zona de care are nevoie',
  direction_required: 'lipsește o zonă cu sens de mers',
}

// --------------------------------------------------------------------------- helpers

export function defaultConfig(frame: Frame, catalog: Catalog, modelId: string): CameraConfig {
  const defaults = (bounds: Bound[]) => Object.fromEntries(bounds.filter((b) => b.required && b.default != null).map((b) => [b.id, b.default as number]))
  return {
    schema_version: catalog.schema_version,
    reference_frame: { width: frame.width, height: frame.height, coordinate_convention: catalog.coordinate_convention },
    calibration: null, min_y: null, zones: [], rules: [],
    thresholds: defaults(catalog.thresholds), acquisition: defaults(catalog.acquisition), model: { id: modelId },
  }
}

/** A valid, unused zone id from a display name ("Bandă de urgență" → "banda_de_urgenta"). */
export function zoneId(name: string, taken: string[]): string {
  const base = name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 36) || 'zona'
  if (!taken.includes(base)) return base
  for (let n = 2; ; n++) if (!taken.includes(`${base}_${n}`)) return `${base}_${n}`
}

export type ErrorTarget =
  | { kind: 'zone'; index: number; vertex?: number } | { kind: 'calibration'; vertex?: number } | { kind: 'rule'; index: number }
  | { kind: 'threshold'; id: string } | { kind: 'acquisition'; id: string } | { kind: 'limit' } | { kind: 'model' } | { kind: 'other' }
/** Which shape or field a validator path ("zones[2].polygon[5]") is about. */
export function errorTarget(path: string): ErrorTarget {
  let m = /^zones\[(\d+)\](?:\.polygon\[(\d+)\])?/.exec(path)
  if (m) return m[2] === undefined ? { kind: 'zone', index: +m[1] } : { kind: 'zone', index: +m[1], vertex: +m[2] }
  m = /^calibration(?:\.source\[(\d+)\])?/.exec(path)
  if (m) return m[1] === undefined ? { kind: 'calibration' } : { kind: 'calibration', vertex: +m[1] }
  m = /^rules\[(\d+)\]/.exec(path)
  if (m) return { kind: 'rule', index: +m[1] }
  m = /^thresholds\.(\w+)/.exec(path)
  if (m) return { kind: 'threshold', id: m[1] }
  m = /^acquisition\.(\w+)/.exec(path)
  if (m) return { kind: 'acquisition', id: m[1] }
  if (path.startsWith('min_y')) return { kind: 'limit' }
  if (path.startsWith('model')) return { kind: 'model' }
  return { kind: 'other' }
}

/** Linear undo / redo over whole values; a new edit drops the redo branch. */
export class History<T> {
  private past: T[] = []
  private future: T[] = []
  current: T
  constructor(initial: T, private limit = 200) { this.current = initial }
  push(value: T) {
    this.past.push(this.current)
    if (this.past.length > this.limit) this.past.shift()
    this.current = value
    this.future = []
  }
  undo(): T | null {
    const previous = this.past.pop()
    if (previous === undefined) return null
    this.future.push(this.current)
    this.current = previous
    return previous
  }
  redo(): T | null {
    const next = this.future.pop()
    if (next === undefined) return null
    this.past.push(this.current)
    this.current = next
    return next
  }
  get canUndo() { return this.past.length > 0 }
  get canRedo() { return this.future.length > 0 }
}

export const RULE_LABEL: Record<string, string> = {
  pedestrian_on_road: 'Pieton pe carosabil', very_high_speed: 'Viteză foarte mare', stopped_on_road: 'Vehicul oprit pe carosabil',
  stopped_emergency_lane: 'Vehicul oprit pe banda de urgență', hard_braking: 'Frânare bruscă', probable_crash: 'Posibilă coliziune – necesită verificare',
  tailgating: 'Distanță prea mică', dangerous_lane_change: 'Schimbare de bandă periculoasă', wrong_way: 'Mers pe contrasens', congestion: 'Aglomerare',
}
export const ZONE_KIND_LABEL: Record<string, string> = { carriageway: 'Carosabil', emergency_lane: 'Bandă de urgență' }
/** Threshold name, unit and plain meaning, in the order the form shows them. */
export const THRESHOLD_INFO: Record<string, { label: string; unit: string }> = {
  speed_limit_kmh: { label: 'Limita de viteză a drumului', unit: 'km/h' },
  very_high_speed_kmh: { label: 'Viteză de la care apare alerta', unit: 'km/h' },
  stopped_speed_kmh: { label: 'Sub această viteză vehiculul e considerat oprit', unit: 'km/h' },
  stopped_seconds: { label: 'Cât stă oprit până la alertă', unit: 's' },
  hard_brake_mps2: { label: 'Decelerare considerată frânare bruscă', unit: 'm/s²' },
  headway_seconds: { label: 'Distanță minimă în timp față de vehiculul din față', unit: 's' },
  headway_min_speed_kmh: { label: 'Distanța se verifică doar peste această viteză', unit: 'km/h' },
  lane_change_m: { label: 'Deplasare laterală considerată schimbare de bandă', unit: 'm' },
  lane_change_window_s: { label: 'Intervalul în care se măsoară deplasarea laterală', unit: 's' },
  wrong_way_min_px: { label: 'Deplasare minimă împotriva sensului', unit: 'px' },
  congestion_vehicles: { label: 'Vehicule în zonă pentru aglomerare', unit: 'vehicule' },
  congestion_avg_speed_kmh: { label: 'Viteză medie sub care e aglomerare', unit: 'km/h' },
  congestion_seconds: { label: 'Cât durează până la alerta de aglomerare', unit: 's' },
  min_track_age_s: { label: 'Vârsta minimă a unei urmăriri înainte de reguli', unit: 's' },
  crash_window_s: { label: 'Fereastra în care se caută oprirea după frânare', unit: 's' },
}
export const ACQUISITION_INFO: Record<string, { label: string; unit: string }> = {
  target_fps: { label: 'Cadre analizate pe secundă (cel mult)', unit: 'cadre/s' },
  reconnect_backoff_s: { label: 'Pauză înainte de reconectare', unit: 's' },
  read_timeout_s: { label: 'Timp de așteptare la citire', unit: 's' },
  max_reconnect_attempts: { label: 'Încercări de reconectare', unit: '' },
}
