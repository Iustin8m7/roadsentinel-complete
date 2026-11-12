import type { Alert, AlertMetrics, AlertType, ArchiveClip, KeyFrame, VehicleClass, VlmVerdict } from '@/types'
import { ALERT_TYPE } from '@/lib/constants'
import { RULES } from './rules'

// Small seeded PRNG so the seed data is identical on every reset.
export function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

type Rand = () => number
const pick = <T,>(r: Rand, xs: readonly T[]): T => xs[Math.floor(r() * xs.length)]
const between = (r: Rand, a: number, b: number) => Math.round(a + r() * (b - a))

interface Template {
  vehicle: VehicleClass[]
  descriptions: string[]
  metrics: (r: Rand) => AlertMetrics
  frames: string[]
}

type DemoAlertType = Exclude<AlertType, 'pedestrian_on_road' | 'very_high_speed' | 'stopped_emergency_lane' | 'stopped_on_road' | 'object_on_roadway'>
const TEMPLATES: Record<DemoAlertType, Template> = {
  wrong_way: {
    vehicle: ['autoturism', 'autoturism', 'camion'],
    descriptions: [
      'Autoturism de culoare închisă circulă pe contrasens pe banda 1, faruri aprinse.',
      'Vehicul intră pe sensul opus după bretea, alte vehicule se feresc spre banda 2.',
      'Autoutilitară albă pe sens interzis, viteză redusă, avarii stinse.',
    ],
    metrics: (r) => ({ speedKmh: between(r, 40, 110) }),
    frames: ['Intrare pe contrasens', 'Vehicule care evită', 'Ieșire din cadru'],
  },
  pedestrian_highway: {
    vehicle: ['pieton'],
    descriptions: [
      'O persoană merge pe acostament, apoi traversează banda 2. Trafic intens.',
      'Pieton lângă parapetul median, pare să încerce traversarea autostrăzii.',
      'Două persoane pe banda de urgență lângă un autoturism oprit.',
    ],
    metrics: (r) => ({ dwellSec: between(r, 5, 90), vehicleClass: 'pieton' }),
    frames: ['Pieton detectat', 'Pieton pe carosabil', 'Ultima poziție'],
  },
  probable_crash: {
    vehicle: ['autoturism', 'camion', 'autobuz'],
    descriptions: [
      'Două autoturisme oprite brusc pe banda 2, unul cu partea din spate deformată. Fum ușor.',
      'Camion și autoturism imobilizate oblic pe carosabil, resturi pe bandă.',
      'Vehicul lovește parapetul și se oprește pe banda 1. Șoferul coboară.',
    ],
    metrics: (r) => ({ decelMs2: between(r, 9, 14), speedKmh: between(r, 60, 120) }),
    frames: ['Înainte de impact', 'Impact probabil', 'Vehicule imobilizate', 'Persoane în jurul vehiculelor'],
  },
  road_object: {
    vehicle: ['obiect'],
    descriptions: [
      'Obiect de mari dimensiuni (anvelopă de camion) pe banda 1.',
      'Încărcătură căzută (paleți) pe banda 2, vehiculele încetinesc.',
      'Bucăți de caroserie pe carosabil după o coliziune anterioară.',
    ],
    metrics: (r) => ({ dwellSec: between(r, 25, 400), vehicleClass: 'obiect' }),
    frames: ['Obiect detectat', 'Vehicule care ocolesc'],
  },
  high_speed: {
    vehicle: ['autoturism', 'autoturism', 'motocicleta'],
    descriptions: [
      'Autoturism sport depășește pe banda 3 cu viteză mult peste limită.',
      'Motocicletă circulă printre benzi cu viteză foarte mare.',
      'Autoturism negru depășește mai multe vehicule pe banda 1.',
    ],
    metrics: (r) => ({ speedKmh: between(r, 150, 235), speedLimitKmh: 130 }),
    frames: ['Intrare în zonă', 'Măsurare viteză', 'Ieșire din zonă'],
  },
  emergency_lane_stop: {
    vehicle: ['camion', 'autoturism', 'autobuz'],
    descriptions: [
      'Camion oprit pe banda de urgență, avarii pornite, două persoane lângă el.',
      'Autoturism oprit pe banda de urgență fără avarii, nicio persoană vizibilă.',
      'Autocar oprit pe banda de urgență, pasageri coborâți pe acostament.',
    ],
    metrics: (r) => ({ dwellSec: between(r, 60, 900) }),
    frames: ['Vehicul încetinește', 'Vehicul oprit', 'Persoane lângă vehicul'],
  },
  near_miss: {
    vehicle: ['autoturism', 'pieton'],
    descriptions: [
      'Autoturism trece prin trecerea de pietoni la sub 1 m de un pieton.',
      'Două vehicule evită coliziunea la limită în intersecție.',
      'Scuter frânează brusc lângă un pieton pe trecere.',
    ],
    metrics: (r) => ({ distanceM: Number((0.4 + r() * 1.1).toFixed(1)), speedKmh: between(r, 35, 70) }),
    frames: ['Apropiere', 'Distanță minimă', 'După eveniment'],
  },
  hard_braking: {
    vehicle: ['autoturism', 'camion'],
    descriptions: [
      'Autoturism frânează brusc, vehiculul din spate schimbă banda.',
      'Camion frânează puternic la intrarea în aglomerare.',
    ],
    metrics: (r) => ({ decelMs2: between(r, 6, 9), speedKmh: between(r, 70, 110) }),
    frames: ['Înainte de frânare', 'Decelerare maximă'],
  },
  tailgating: {
    vehicle: ['autoturism', 'camion'],
    descriptions: [
      'Autoturism la aproximativ 6 m în spatele altui vehicul, la peste 110 km/h.',
      'Camion urmărește îndeaproape un autoturism pe banda 1.',
    ],
    metrics: (r) => ({ distanceM: between(r, 4, 9), speedKmh: between(r, 100, 140) }),
    frames: ['Distanță măsurată', 'Menținere distanță redusă'],
  },
  dangerous_lane_change: {
    vehicle: ['autoturism', 'motocicleta'],
    descriptions: [
      'Autoturism schimbă trei benzi consecutiv fără semnalizare.',
      'Vehicul intră între două autoturisme la mai puțin de 4 m.',
    ],
    metrics: (r) => ({ distanceM: between(r, 2, 5), speedKmh: between(r, 80, 130) }),
    frames: ['Prima schimbare', 'A doua schimbare', 'Poziție finală'],
  },
  congestion: {
    vehicle: ['autoturism'],
    descriptions: [
      'Coloană de vehicule pe toate benzile, viteză medie sub 15 km/h.',
      'Aglomerare în creștere spre ieșire, banda 3 blocată parțial.',
    ],
    metrics: (r) => ({ speedKmh: between(r, 3, 15), dwellSec: between(r, 300, 1500) }),
    frames: ['Densitate trafic'],
  },
  road_conditions: {
    vehicle: ['autoturism'],
    descriptions: [
      'Vizibilitate redusă din cauza ceței, sub 100 m estimat.',
      'Carosabil umed cu posibil polei, vehiculele circulă lent.',
    ],
    metrics: () => ({}),
    frames: ['Condiții vizibilitate'],
  },
}

const ALERT_TYPES = Object.keys(TEMPLATES) as DemoAlertType[]
// Weighted so the dashboard has a realistic mix (fewer criticals than info/medium).
const WEIGHTS: Record<DemoAlertType, number> = {
  wrong_way: 1, pedestrian_highway: 1, probable_crash: 1, road_object: 1.5,
  high_speed: 3, emergency_lane_stop: 3, near_miss: 2,
  hard_braking: 3, tailgating: 3, dangerous_lane_change: 2,
  congestion: 2.5, road_conditions: 1,
}

function weightedType(r: Rand): DemoAlertType {
  const total = ALERT_TYPES.reduce((s, t) => s + WEIGHTS[t], 0)
  let x = r() * total
  for (const t of ALERT_TYPES) {
    x -= WEIGHTS[t]
    if (x <= 0) return t
  }
  return 'congestion'
}

let counter = 4100
export const nextAlertId = () => `RS-2026-${++counter}`

export function makeAlert(r: Rand, createdAt: Date, forcedType?: AlertType): Alert {
  const type = (forcedType ?? weightedType(r)) as DemoAlertType
  const tpl = TEMPLATES[type]
  const rules = RULES.filter((x) => x.alertType === type)
  const rule = pick(r, rules)
  const cameraId = pick(r, rule.cameraIds)
  const vlmRoll = r()
  const verdict: VlmVerdict = vlmRoll < 0.78 ? 'confirmed' : vlmRoll < 0.9 ? 'uncertain' : 'rejected'
  const metrics = { vehicleClass: pick(r, tpl.vehicle), ...tpl.metrics(r) }
  const durationSec = between(r, 8, 40)
  const frames: KeyFrame[] = tpl.frames.map((label, i) => ({
    label,
    offsetSec: Math.round(((i + 1) / (tpl.frames.length + 1)) * durationSec),
  }))
  return {
    id: nextAlertId(),
    type,
    severity: ALERT_TYPE[type].severity,
    cameraId,
    createdAt: createdAt.toISOString(),
    status: 'new',
    ruleId: rule.id,
    ruleSummary: ruleSummary(rule.thresholds, metrics),
    vlm: {
      verdict,
      confidence: Number((verdict === 'confirmed' ? 0.8 + r() * 0.19 : 0.4 + r() * 0.35).toFixed(2)),
      description:
        verdict === 'rejected'
          ? 'Fals pozitiv probabil: umbră/reflexie interpretată ca eveniment. Nicio anomalie vizibilă în clip.'
          : pick(r, tpl.descriptions),
    },
    metrics,
    clip: { durationSec },
    frames,
    actions: [],
    viewedBy: [],
  }
}

function ruleSummary(t: (typeof RULES)[number]['thresholds'], m: AlertMetrics): string {
  const parts: string[] = []
  if (t.speedKmh && m.speedKmh) parts.push(`viteză ${m.speedKmh} km/h (prag ${t.speedKmh})`)
  if (t.dwellSec && m.dwellSec) parts.push(`staționare ${m.dwellSec}s (prag ${t.dwellSec}s)`)
  if (t.distanceM && m.distanceM) parts.push(`distanță ${m.distanceM} m (prag ${t.distanceM} m)`)
  if (t.decelMs2 && m.decelMs2) parts.push(`decelerare ${m.decelMs2} m/s² (prag ${t.decelMs2})`)
  return parts.join(' · ') || 'Detecție în zonă'
}

/** Seed data: ~60 alerts spread over the last 7 days, older ones already decided. */
export function seedAlerts(seed = 9): Alert[] {
  counter = 4100
  const r = mulberry32(seed)
  const now = Date.now()
  const out: Alert[] = []
  for (let i = 0; i < 60; i++) {
    const ageMin = i < 8 ? between(r, 1, 50) : between(r, 60, 7 * 24 * 60)
    // Make sure the demo opens with critical alerts waiting in the queue.
    const a = makeAlert(r, new Date(now - ageMin * 60_000), i === 0 ? 'probable_crash' : i === 3 ? 'wrong_way' : undefined)
    if (i >= 8) {
      const decided = new Date(now - ageMin * 60_000 + between(r, 1, 6) * 60_000).toISOString()
      const confirm = a.vlm.verdict !== 'rejected' && r() < 0.85
      a.status = confirm ? (r() < 0.7 ? 'closed' : 'confirmed') : 'rejected'
      a.decidedBy = pick(r, ['operator', 'admin'])
      a.decidedAt = decided
      a.viewedBy = [a.decidedBy]
      if (confirm && (a.severity === 'critical' || a.severity === 'high')) {
        a.actions.push({ type: 'dispatch_patrol', at: decided, by: a.decidedBy, patrolId: pick(r, ['P-B21', 'P-B14', 'P-B33', 'P-M02']) })
      }
      if (confirm && a.type === 'road_conditions') {
        a.actions.push({ type: 'warning_sign', at: decided, by: a.decidedBy })
      }
    }
    out.push(a)
  }
  return out.sort((x, y) => y.createdAt.localeCompare(x.createdAt))
}

/** Archive of clips for natural-language search (14 days). */
export function seedArchive(): ArchiveClip[] {
  const r = mulberry32(42)
  const now = Date.now()
  const out: ArchiveClip[] = []
  for (let i = 0; i < 160; i++) {
    const type = weightedType(r)
    const tpl = TEMPLATES[type]
    const rule = pick(r, RULES.filter((x) => x.alertType === type))
    const vehicleClass = pick(r, tpl.vehicle)
    const desc = pick(r, tpl.descriptions)
    out.push({
      id: `CLIP-${String(i + 1).padStart(4, '0')}`,
      cameraId: pick(r, rule.cameraIds),
      startedAt: new Date(now - between(r, 10, 14 * 24 * 60) * 60_000).toISOString(),
      durationSec: between(r, 10, 60),
      vehicleClass,
      eventType: type,
      tags: [vehicleClass, ALERT_TYPE[type].label.toLowerCase(), rule.zone.name.toLowerCase()],
      description: desc,
    })
  }
  out.push(...showcaseClips(new Date(now)))
  return out.sort((x, y) => y.startedAt.localeCompare(x.startedAt))
}

/** Hand-made clips so every example query on the Archive page returns something. */
function showcaseClips(now: Date): ArchiveClip[] {
  const at = (daysAgo: number, hour: number, min = 0) => {
    const d = new Date(now)
    d.setDate(d.getDate() - daysAgo)
    d.setHours(hour, min, 0, 0)
    return d.toISOString()
  }
  const lastTuesday = (now.getDay() - 2 + 7) % 7 || 7
  const clip = (id: string, cameraId: string, startedAt: string, vehicleClass: VehicleClass, eventType: AlertType, description: string): ArchiveClip => ({
    id,
    cameraId,
    startedAt,
    durationSec: 30,
    vehicleClass,
    eventType,
    description,
    tags: [vehicleClass, ALERT_TYPE[eventType].label.toLowerCase()],
  })
  return [
    clip('CLIP-S001', 'CAM-A1-023', at(1, 14, 22), 'camion', 'emergency_lane_stop', 'Camion oprit pe banda de urgență, avarii pornite, două persoane lângă el.'),
    clip('CLIP-S002', 'CAM-A2-012', at(1, 16, 5), 'camion', 'emergency_lane_stop', 'Autocamion cu prelată oprit pe acostament, fără avarii.'),
    clip('CLIP-S003', 'CAM-CB-CHJ', at(1, 17, 41), 'camion', 'emergency_lane_stop', 'TIR oprit pe banda de urgență, șoferul verifică o anvelopă.'),
    clip('CLIP-S004', 'CAM-BUN-02', at(lastTuesday, 8, 17), 'autoturism', 'probable_crash', 'Două autoturisme imobilizate pe banda 2 după o tamponare, trafic blocat parțial.'),
    clip('CLIP-S005', 'CAM-A2-012', at(0, 3, 12), 'autoturism', 'road_conditions', 'Ceață densă, vizibilitate sub 80 m, vehiculele circulă cu avariile pornite.'),
    clip('CLIP-S006', 'CAM-A3-004', new Date(now.getTime() - 40 * 60_000).toISOString(), 'pieton', 'pedestrian_highway', 'Pieton pe acostamentul autostrăzii, traversează spre parapetul median.'),
  ]
}
