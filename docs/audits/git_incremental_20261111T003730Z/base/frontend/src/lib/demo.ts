import { formatDistanceToNowStrict } from 'date-fns'
import { ro } from 'date-fns/locale'
import type { Alert, AuditEntry } from '@/types'

// ---------------------------------------------------------------- clip cache
// Every evidence clip is downloaded once into memory and played from a blob URL,
// so playback never waits on the network (the media endpoint has no Range support).
// Signed media URLs change on every reload, so the cache key drops the query string.
type Entry = { promise: Promise<string>; url?: string; progress: number; listeners: Set<(p: number) => void> }
const cache = new Map<string, Entry>()
const keyOf = (src: string) => src.split('?')[0]

function download(src: string, entry: Entry) {
  return (async () => {
    const res = await fetch(src, { credentials: 'include' })
    if (!res.ok || !res.body) throw new Error(String(res.status))
    const total = Number(res.headers.get('content-length')) || 0
    const reader = res.body.getReader()
    const chunks: BlobPart[] = []
    let got = 0
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(value)
      got += value.length
      if (total) { entry.progress = got / total; entry.listeners.forEach((l) => l(entry.progress)) }
    }
    entry.url = URL.createObjectURL(new Blob(chunks, { type: res.headers.get('content-type') || 'video/mp4' }))
    entry.progress = 1
    return entry.url
  })()
}

/** Blob URL of a clip; starts the download if needed. */
export function getClip(src: string, onProgress?: (p: number) => void): Promise<string> {
  const key = keyOf(src)
  let entry = cache.get(key)
  if (!entry) {
    entry = { promise: Promise.resolve(''), progress: 0, listeners: new Set() }
    entry.promise = download(src, entry).catch((err) => { cache.delete(key); throw err })
    cache.set(key, entry)
  }
  if (onProgress) { entry.listeners.add(onProgress); onProgress(entry.progress) }
  return entry.promise
}
export const cachedClip = (src?: string) => (src ? cache.get(keyOf(src))?.url : undefined)
export const unsubscribeClip = (src: string, onProgress: (p: number) => void) => cache.get(keyOf(src))?.listeners.delete(onProgress)

/** Preloads clips in order, a few at a time. */
export async function preloadClips(srcs: (string | undefined)[], onEach?: (done: number, total: number) => void, parallel = 4) {
  const todo = [...new Set(srcs.filter((s): s is string => !!s))]
  let i = 0
  let done = 0
  onEach?.(0, todo.length)
  const worker = async () => {
    while (i < todo.length) {
      const s = todo[i++]
      await getClip(s).catch(() => {})
      onEach?.(++done, todo.length)
    }
  }
  await Promise.all(Array.from({ length: parallel }, worker))
}
/** Warms the browser cache for still images (keyframes). */
export const preloadImages = (srcs: (string | undefined)[]) => srcs.forEach((s) => { if (s) new Image().src = s })

// ---------------------------------------------------------------- pitch staging switch
// Everything marked (MOCK) below stages the production demo tenant for the pitch. It changes
// how real data looks, so it is opt-in at build time (VITE_DEMO_CURATION=1, set only by the
// production web gateway); every other build shows the API's data unchanged.
export const DEMO_CURATION = import.meta.env.VITE_DEMO_CURATION === '1'

// ---------------------------------------------------------------- pitch order (MOCK)
// For the pitch the queue leads with aggressive driving rather than plain speeding.
// Display-only: the backend keeps its own priorities.
const DEMO_RANK: Record<string, number> = {
  probable_crash: 0, wrong_way: 1, tailgating: 2, dangerous_lane_change: 3, hard_braking: 4,
  stopped_on_road: 5, stopped_emergency_lane: 6, very_high_speed: 7, congestion: 8,
}
export const demoSort = (a: Alert, b: Alert) =>
  (DEMO_CURATION ? (DEMO_RANK[a.type] ?? 6) - (DEMO_RANK[b.type] ?? 6) : 0) ||
  b.createdAt.localeCompare(a.createdAt)

// ---------------------------------------------------------------- "acum X" (MOCK)
// Relative times are faked from the queue position so the pitch shows fresh alerts:
// the first one a few seconds ago, then growing. Fixed at first sight, then they tick.
const fakeCreated = new Map<string, number>()
const ageFor = (i: number) => Math.round(4 + i * 23 + i * i * 6) // s: 4s, 33s, 1m14s, 2m7s, ...
export function assignDemoTimes(queue: Alert[]) {
  if (!DEMO_CURATION) return
  const now = Date.now()
  queue.forEach((a, i) => { if (!fakeCreated.has(a.id)) fakeCreated.set(a.id, now - ageFor(i) * 1000) })
}
export function demoAgo(alert: Alert) {
  const at = fakeCreated.get(alert.id) ?? new Date(alert.createdAt).getTime()
  const sec = Math.max(1, Math.round((Date.now() - at) / 1000))
  if (sec < 60) return `acum ${sec} s`
  return formatDistanceToNowStrict(at, { locale: ro, addSuffix: true })
}

// ---------------------------------------------------------------- manual curation (MOCK)
// Reviewed by hand on the clips, 2026-10-18. The demo cameras have guessed calibrations,
// so the pipeline labelled close following as speeding and produced false positives.
// Display-only: the backend keeps the original rows.
export const RECLASSIFY: Record<string, { type: Alert['type']; severity?: Alert['severity']; rule?: string }> = DEMO_CURATION ? {
  '107': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față (autostradă)' },
  '96': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
  '99': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
  '100': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
} : {}
/** False positives and duplicates of the same moment from earlier pipeline runs. */
export const HIDDEN_IDS = new Set<string>(DEMO_CURATION ? [
  // highway: duplicates of #107/#121 and 129–134 km/h under the 130 km/h limit
  '106', '108', '111', '122', '123', '124', '125', '127',
  // bridge at night: single cars at normal speed, tiny off-road boxes
  '89', '91', '92', '93', '94', '95', '97', '98',
  // avenue: food cart / pedestrian boxes, duplicate scenes, bus stopping at the light
  '102', '105', '109', '112', '119', '120', '104', '113', '115', '114', '116',
  // congestion duplicate
  '128',
  // evidence lost in earlier redeploys; each is a duplicate of a newer run
  '1', '2', '3', '4', '5', '6', '7', '8', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78',
  '79', '80', '81', '82', '83', '84', '85', '86', '87', '88',
] : [])
export function curate(alert: Alert): Alert {
  const fix = RECLASSIFY[alert.id]
  return replay(fix ? { ...alert, type: fix.type, severity: fix.severity ?? alert.severity, ruleId: fix.type, ruleSummary: fix.rule ?? alert.ruleSummary } : alert)
}

// ---------------------------------------------------------------- confirm replay (MOCK)
// Alerts already decided in the backend, shown as new so the pitch can show a confirmation.
// The backend answers 409 (already decided); the decision is then kept in this tab only,
// so a page reload shows them as new again.
export const DEMO_UNDECIDED = new Set<string>(DEMO_CURATION ? ['99', '107', '118'] : [])
type LocalDecision = { status: 'confirmed' | 'rejected'; by: string; at: string; note?: string }
export const localDecisions = new Map<string, LocalDecision>()

function replay(alert: Alert): Alert {
  if (!DEMO_UNDECIDED.has(alert.id)) return alert
  const d = localDecisions.get(alert.id)
  return d
    ? { ...alert, status: d.status, decidedBy: d.by, decidedAt: d.at, decisionNote: d.note }
    : { ...alert, status: 'new', decidedBy: undefined, decidedAt: undefined, decisionNote: undefined }
}
/** Hides the backend's earlier decision on replayed alerts from the history. */
export const keepAudit = (e: AuditEntry) =>
  !(e.target && DEMO_UNDECIDED.has(e.target) && !e.id.startsWith('local-') && ['confirmed', 'rejected'].includes(e.action))
