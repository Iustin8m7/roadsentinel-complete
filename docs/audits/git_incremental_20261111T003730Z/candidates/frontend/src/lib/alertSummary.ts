// Plain-Romanian summary of an alert for the "Pe scurt" card: what happened, why the alarm
// fired and what the dispatcher can do. Pure: everything comes in through the input.

export interface AlertSummaryInput {
  type: string
  /** Label of the type, used only for a type this file does not know. */
  typeLabel?: string
  cameraName?: string
  /** ISO timestamp of the event. */
  at?: string
  /** UI object class (autoturism, camion, autobuz, motocicleta, pieton, obiect). */
  objectClass?: string
  speedKmh?: number | null
  limitKmh?: number | null
  /** Technical rule text from the pipeline; quoted only for an unknown type. */
  rule?: string
  status: string
  decidedBy?: string
  decidedAt?: string
  /** A person changed the type after watching the clip (demo curation). */
  reclassifiedByHuman?: boolean
}

export interface AlertSummary {
  what: string
  why: string
  next: string
}

const ALIASES: Record<string, string> = {
  excessive_speed: 'very_high_speed',
  high_speed: 'very_high_speed',
  pedestrian_on_highway: 'pedestrian_highway',
  emergency_lane_stop: 'stopped_emergency_lane',
}

// Accusative, indefinite: fits after "Sistemul a semnalat".
const OBJECT: Record<string, string> = {
  autoturism: 'un autoturism',
  camion: 'un camion',
  autobuz: 'un autobuz',
  motocicleta: 'o motocicletă',
}

const kmh = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value) && value > 0 ? `${Math.round(value)} km/h` : null

const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
const two = (n: number) => String(n).padStart(2, '0')

/** "azi la 14:32", "ieri la 14:32" or "pe 18.10.2026 la 14:32"; null for a missing or invalid date. */
export function whenPhrase(iso: string | undefined, now: Date): string | null {
  if (!iso) return null
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return null
  const time = `${two(at.getHours())}:${two(at.getMinutes())}`
  if (sameDay(at, now)) return `azi la ${time}`
  if (sameDay(at, new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))) return `ieri la ${time}`
  return `pe ${two(at.getDate())}.${two(at.getMonth() + 1)}.${at.getFullYear()} la ${time}`
}

interface Wording {
  /** What the system flagged, without place and time. */
  what: (vehicle: string, speed: string | null, limit: string | null, underLimit: boolean) => string
  why: string
}

const WORDING: Record<string, Wording> = {
  very_high_speed: {
    what: (v, speed, limit, underLimit) =>
      speed && limit ? `${v} care circula cu o viteză estimată la ${speed} pe un tronson cu limita de ${limit}`
        : speed && underLimit ? `${v} care circula cu o viteză estimată la ${speed}`
        : speed ? `${v} care circula cu o viteză estimată la ${speed}, peste pragul stabilit pentru această cameră`
          : `${v} care circula cu o viteză peste pragul stabilit pentru această cameră`,
    why: 'Viteza estimată a depășit pragul stabilit pentru această cameră.',
  },
  probable_crash: {
    what: (v) => `${v} care a frânat brusc și apoi s-a oprit pe carosabil, ceea ce poate însemna un accident`,
    why: 'O frânare bruscă urmată de o oprire completă pe carosabil seamănă cu un accident și trebuie verificată de un om.',
  },
  pedestrian_on_road: {
    what: () => 'o persoană pe carosabil',
    why: 'O persoană a fost detectată într-o zonă destinată vehiculelor.',
  },
  pedestrian_highway: {
    what: () => 'o persoană pe autostradă',
    why: 'O persoană a fost detectată pe autostradă, unde pietonii nu au voie.',
  },
  wrong_way: {
    what: (v) => `${v} care se deplasa pe contrasens`,
    why: 'Vehiculul s-a deplasat câteva secunde împotriva sensului de mers stabilit pentru această bandă.',
  },
  stopped_on_road: {
    what: (v) => `${v} care staționa pe carosabil`,
    why: 'Vehiculul a stat pe loc, pe carosabil, mai mult decât timpul stabilit pentru această cameră.',
  },
  stopped_emergency_lane: {
    what: (v) => `${v} care staționa pe banda de urgență`,
    why: 'Vehiculul a stat pe loc, pe banda de urgență, mai mult decât timpul stabilit pentru această cameră.',
  },
  road_object: {
    what: () => 'un obiect pe carosabil',
    why: 'Un obiect nemișcat a fost detectat pe partea carosabilă.',
  },
  near_miss: {
    what: (v) => `${v} care a trecut foarte aproape de un alt participant la trafic`,
    why: 'Doi participanți la trafic au ajuns la o distanță foarte mică unul de celălalt.',
  },
  hard_braking: {
    what: (v) => `${v} care a frânat brusc`,
    why: 'Viteza vehiculului a scăzut mult într-un timp foarte scurt.',
  },
  tailgating: {
    what: (v, speed) => `${v} care circula prea aproape de vehiculul din față${speed ? `, cu o viteză estimată la ${speed}` : ''}`,
    why: 'Distanța față de vehiculul din față a rămas sub pragul de siguranță stabilit pentru această cameră.',
  },
  dangerous_lane_change: {
    what: (v) => `${v} care a schimbat brusc banda, cu un alt vehicul foarte aproape`,
    why: 'Vehiculul s-a mutat rapid pe altă bandă în timp ce un alt vehicul se afla foarte aproape.',
  },
  congestion: {
    what: (_v, speed) => `trafic aglomerat${speed ? `, cu o viteză medie estimată la ${speed}` : ''}`,
    why: 'Multe vehicule au circulat încet pe aceeași porțiune de drum, mai mult timp decât pragul stabilit.',
  },
  road_conditions: {
    what: () => 'condiții de drum care pot îngreuna circulația',
    why: 'Imaginile indică vizibilitate redusă sau carosabil alunecos.',
  },
}

const NO_AUTOMATION = 'Sistemul nu trimite singur echipaje și nu dă amenzi'

export function summarizeAlert(input: AlertSummaryInput, now: Date = new Date()): AlertSummary {
  const wording = WORDING[ALIASES[input.type] ?? input.type]
  const vehicle = OBJECT[input.objectClass ?? ''] ?? 'un vehicul'
  const speed = kmh(input.speedKmh)
  const limitValue = kmh(input.limitKmh)
  // A limit at or above the estimated speed would contradict the sentence; leave it out.
  const underLimit = !!(speed && limitValue && (input.speedKmh ?? 0) <= (input.limitKmh ?? 0))
  const limit = speed && limitValue && !underLimit ? limitValue : null

  const label = (input.typeLabel || input.type || '').replace(/_/g, ' ').trim()
  const subject = wording ? wording.what(vehicle, speed, limit, underLimit)
    : label ? `un eveniment de tip „${label}”` : 'un eveniment rutier'
  const camera = input.cameraName?.trim()
  const at = whenPhrase(input.at, now)
  const what = `Sistemul a semnalat ${subject}${camera ? `, la camera ${camera}` : ''}${at ? `, ${at}` : ''}.`

  const rule = input.rule?.trim()
  const why = input.reclassifiedByHuman
    ? `Sistemul a încadrat inițial altfel acest eveniment; un om a verificat clipul și l-a reîncadrat manual${label ? ` ca „${label.toLowerCase()}”` : ''}.`
    : wording?.why
    ?? (rule ? `Regula care a declanșat alerta: ${rule.replace(/\.$/, '')}.` : 'S-a îndeplinit o regulă configurată pentru această cameră.')

  const decision = input.status === 'confirmed' ? 'Alerta a fost confirmată'
    : input.status === 'rejected' ? 'Alerta a fost respinsă'
      : input.status === 'closed' ? 'Dosarul alertei a fost închis' : null
  if (!decision) {
    return { what, why, next: `Verificați clipul și confirmați sau respingeți alerta. ${NO_AUTOMATION}; decizia este a omului.` }
  }
  const by = input.decidedBy?.trim()
  const decidedAt = whenPhrase(input.decidedAt, now)
  return {
    what, why,
    next: `${decision}${by ? ` de ${by}` : ''}${decidedAt ? `, ${decidedAt}` : ''}. Decizia a fost luată de un om. ${NO_AUTOMATION}.`,
  }
}
