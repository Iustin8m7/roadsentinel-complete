import { describe, expect, it } from 'vitest'
import type { AlertType } from '@/types'
import { summarizeAlert, whenPhrase, type AlertSummaryInput } from './alertSummary'

// Local-time dates keep the expected clock text independent of the machine's time zone.
const NOW = new Date(2026, 10, 13, 15, 0)
const iso = (d: number, h: number, m: number) => new Date(2026, 10, d, h, m).toISOString()
const base: AlertSummaryInput = {
  type: 'very_high_speed', cameraName: 'Pasaj Mihai Eminescu', at: iso(13, 14, 32),
  objectClass: 'autoturism', status: 'new',
}
const what = (patch: Partial<AlertSummaryInput>) => summarizeAlert({ ...base, ...patch }, NOW).what
const TAIL = ', la camera Pasaj Mihai Eminescu, azi la 14:32.'

describe('summarizeAlert: what happened, per type', () => {
  const cases: Record<AlertType, [Partial<AlertSummaryInput>, string]> = {
    very_high_speed: [{ speedKmh: 116.4, limitKmh: 50 }, 'Sistemul a semnalat un autoturism care circula cu o viteză estimată la 116 km/h pe un tronson cu limita de 50 km/h'],
    high_speed: [{ speedKmh: 180, limitKmh: 130, objectClass: 'motocicleta' }, 'Sistemul a semnalat o motocicletă care circula cu o viteză estimată la 180 km/h pe un tronson cu limita de 130 km/h'],
    probable_crash: [{}, 'Sistemul a semnalat un autoturism care a frânat brusc și apoi s-a oprit pe carosabil, ceea ce poate însemna un accident'],
    pedestrian_on_road: [{ objectClass: 'pieton' }, 'Sistemul a semnalat o persoană pe carosabil'],
    pedestrian_highway: [{ objectClass: 'pieton' }, 'Sistemul a semnalat o persoană pe autostradă'],
    wrong_way: [{ objectClass: 'camion' }, 'Sistemul a semnalat un camion care se deplasa pe contrasens'],
    stopped_on_road: [{ objectClass: 'autobuz' }, 'Sistemul a semnalat un autobuz care staționa pe carosabil'],
    stopped_emergency_lane: [{}, 'Sistemul a semnalat un autoturism care staționa pe banda de urgență'],
    emergency_lane_stop: [{}, 'Sistemul a semnalat un autoturism care staționa pe banda de urgență'],
    road_object: [{ objectClass: 'obiect' }, 'Sistemul a semnalat un obiect pe carosabil'],
    near_miss: [{}, 'Sistemul a semnalat un autoturism care a trecut foarte aproape de un alt participant la trafic'],
    hard_braking: [{ speedKmh: 80 }, 'Sistemul a semnalat un autoturism care a frânat brusc'],
    tailgating: [{ speedKmh: 92 }, 'Sistemul a semnalat un autoturism care circula prea aproape de vehiculul din față, cu o viteză estimată la 92 km/h'],
    dangerous_lane_change: [{}, 'Sistemul a semnalat un autoturism care a schimbat brusc banda, cu un alt vehicul foarte aproape'],
    congestion: [{ objectClass: undefined, speedKmh: 11.6 }, 'Sistemul a semnalat trafic aglomerat, cu o viteză medie estimată la 12 km/h'],
    road_conditions: [{}, 'Sistemul a semnalat condiții de drum care pot îngreuna circulația'],
  }
  for (const [type, [patch, expected]] of Object.entries(cases)) {
    it(type, () => {
      const summary = summarizeAlert({ ...base, ...patch, type }, NOW)
      expect(summary.what).toBe(expected + TAIL)
      expect(summary.why).toMatch(/^[A-ZĂÂÎȘȚ].+\.$/)
      expect(summary.next).toContain('confirmați sau respingeți')
    })
  }

  it('reads the older type names like the current ones', () => {
    expect(what({ type: 'excessive_speed', speedKmh: 116, limitKmh: 50 })).toBe(what({ speedKmh: 116, limitKmh: 50 }))
    expect(what({ type: 'pedestrian_on_highway' })).toBe(what({ type: 'pedestrian_highway' }))
  })
})

describe('summarizeAlert: missing or odd data', () => {
  const clean = (text: string) => expect(text).not.toMatch(/undefined|NaN|null|,\s*,|\s{2}/)

  it('speed without a limit', () => {
    expect(what({ speedKmh: 116 })).toBe('Sistemul a semnalat un autoturism care circula cu o viteză estimată la 116 km/h, peste pragul stabilit pentru această cameră' + TAIL)
  })
  it('no speed at all', () => {
    for (const speedKmh of [undefined, null, Number.NaN, 0]) {
      expect(what({ speedKmh, limitKmh: 50 })).toBe('Sistemul a semnalat un autoturism care circula cu o viteză peste pragul stabilit pentru această cameră' + TAIL)
    }
  })
  it('drops a limit that is not below the estimated speed', () => {
    expect(what({ speedKmh: 129, limitKmh: 130 })).not.toContain('limita')
  })
  it('tailgating and congestion without a speed print no unit', () => {
    expect(what({ type: 'tailgating' })).toBe('Sistemul a semnalat un autoturism care circula prea aproape de vehiculul din față' + TAIL)
    expect(what({ type: 'congestion', speedKmh: null })).toBe('Sistemul a semnalat trafic aglomerat' + TAIL)
  })
  it('unknown object class, camera and time', () => {
    const summary = summarizeAlert({ type: 'wrong_way', status: 'new', at: 'not a date', cameraName: '  ' }, NOW)
    expect(summary.what).toBe('Sistemul a semnalat un vehicul care se deplasa pe contrasens.')
    Object.values(summary).forEach(clean)
  })
  it('unknown type falls back to its label and the rule text', () => {
    const summary = summarizeAlert({ ...base, type: 'red_light', typeLabel: 'Trecere pe roșu', rule: 'Vehicul în intersecție pe roșu.' }, NOW)
    expect(summary.what).toBe('Sistemul a semnalat un eveniment de tip „Trecere pe roșu”' + TAIL)
    expect(summary.why).toBe('Regula care a declanșat alerta: Vehicul în intersecție pe roșu.')
  })
  it('unknown type with nothing else known', () => {
    const summary = summarizeAlert({ type: '', status: 'new' }, NOW)
    expect(summary.what).toBe('Sistemul a semnalat un eveniment rutier.')
    expect(summary.why).toBe('S-a îndeplinit o regulă configurată pentru această cameră.')
    expect(summarizeAlert({ type: 'red_light', status: 'new' }, NOW).what).toBe('Sistemul a semnalat un eveniment de tip „red light”.')
    Object.values(summary).forEach(clean)
  })
})

describe('summarizeAlert: next step', () => {
  it('undecided alerts ask for a human decision', () => {
    for (const status of ['new', 'in_review']) {
      expect(summarizeAlert({ ...base, status }, NOW).next)
        .toBe('Verificați clipul și confirmați sau respingeți alerta. Sistemul nu trimite singur echipaje și nu dă amenzi; decizia este a omului.')
    }
  })
  it('says who decided and when', () => {
    expect(summarizeAlert({ ...base, status: 'confirmed', decidedBy: 'operator', decidedAt: iso(13, 14, 40) }, NOW).next)
      .toBe('Alerta a fost confirmată de operator, azi la 14:40. Decizia a fost luată de un om. Sistemul nu trimite singur echipaje și nu dă amenzi.')
    expect(summarizeAlert({ ...base, status: 'rejected', decidedBy: 'admin', decidedAt: iso(12, 9, 5) }, NOW).next)
      .toMatch(/^Alerta a fost respinsă de admin, ieri la 09:05\./)
  })
  it('a decision without author or time stays a clean sentence', () => {
    expect(summarizeAlert({ ...base, status: 'closed' }, NOW).next).toMatch(/^Dosarul alertei a fost închis\. /)
    expect(summarizeAlert({ ...base, status: 'confirmed', decidedAt: 'x' }, NOW).next).toMatch(/^Alerta a fost confirmată\. /)
  })
})

describe('whenPhrase', () => {
  it('today, yesterday, older, invalid', () => {
    expect(whenPhrase(iso(13, 0, 7), NOW)).toBe('azi la 00:07')
    expect(whenPhrase(iso(12, 23, 59), NOW)).toBe('ieri la 23:59')
    expect(whenPhrase(iso(2, 8, 30), NOW)).toBe('pe 02.11.2026 la 08:30')
    expect(whenPhrase(undefined, NOW)).toBeNull()
    expect(whenPhrase('', NOW)).toBeNull()
  })
})

describe('summarizeAlert: honesty edge cases', () => {
  it('does not claim a threshold was exceeded when the speed is under the limit', () => {
    expect(what({ speedKmh: 120, limitKmh: 130 })).toBe('Sistemul a semnalat un autoturism care circula cu o viteză estimată la 120 km/h' + TAIL)
  })
  it('says a person reclassified the alert instead of naming a rule that never fired', () => {
    const s = summarizeAlert({ ...base, type: 'tailgating', typeLabel: 'Distanță prea mică', reclassifiedByHuman: true }, NOW)
    expect(s.why).toBe('Sistemul a încadrat inițial altfel acest eveniment; un om a verificat clipul și l-a reîncadrat manual ca „distanță prea mică”.')
  })
})
