import { formatDistanceToNowStrict } from 'date-fns'
import { ro } from 'date-fns/locale'
import { USE_MOCKS } from '@/lib/api'
import type { Alert, AuditEntry } from '@/types'

// ---------------------------------------------------------------- clip cache
// Every evidence clip is downloaded once into memory and played from a blob URL,
// so playback never waits on the network (the media endpoint has no Range support).
// Signed media URLs change on every reload, so the cache key drops the query string.
const CLIP_IDLE_MS = 20_000
type Entry = { promise: Promise<string>; url?: string; progress: number; listeners: Set<(p: number) => void> }
const cache = new Map<string, Entry>()
const keyOf = (src: string) => src.split('?')[0]

function download(src: string, entry: Entry) {
  return (async () => {
    // A stalled request must not hold a preload slot (or the player) forever, but a slow one that
    // keeps sending must finish: the timer restarts with every chunk.
    const stall = new AbortController()
    let timer = setTimeout(() => stall.abort(), CLIP_IDLE_MS)
    const alive = () => { clearTimeout(timer); timer = setTimeout(() => stall.abort(), CLIP_IDLE_MS) }
    try {
    const res = await fetch(src, { credentials: 'include', signal: stall.signal })
    if (!res.ok || !res.body) throw new Error(String(res.status))
    const total = Number(res.headers.get('content-length')) || 0
    const reader = res.body.getReader()
    const chunks: BlobPart[] = []
    let got = 0
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      alive()
      chunks.push(value)
      got += value.length
      if (total) { entry.progress = got / total; entry.listeners.forEach((l) => l(entry.progress)) }
    }
    entry.url = URL.createObjectURL(new Blob(chunks, { type: res.headers.get('content-type') || 'video/mp4' }))
    entry.progress = 1
    return entry.url
    } finally { clearTimeout(timer) }
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

// The media endpoint shares the API's database pool, so preloading stays at two downloads at
// once across every call; a newer call (the alert list changed) takes over from an older one.
const PRELOAD_PARALLEL = 2
let preloadRun = 0
let preloadActive = 0
const preloadWaiting: (() => void)[] = []

/** Preloads clips in order, two at a time. Failed clips are skipped; the player retries on demand. */
export async function preloadClips(srcs: (string | undefined)[], onEach?: (done: number, total: number) => void) {
  const run = ++preloadRun
  const todo = [...new Set(srcs.filter((s): s is string => !!s))]
  let i = 0
  let done = 0
  onEach?.(0, todo.length)
  const worker = async () => {
    while (i < todo.length && run === preloadRun) {
      const s = todo[i++]
      if (!cachedClip(s)) {
        while (preloadActive >= PRELOAD_PARALLEL) await new Promise<void>((free) => preloadWaiting.push(free))
        preloadActive++
        await getClip(s).catch(() => {})
        preloadActive--
        preloadWaiting.shift()?.()
      }
      done++
      if (run === preloadRun) onEach?.(done, todo.length)
    }
  }
  await Promise.all(Array.from({ length: PRELOAD_PARALLEL }, worker))
}

// ---------------------------------------------------------------- post-login overlay
// The overlay only waits for the first few clips, and never longer than a few seconds:
// everything else keeps loading in the background while the operator already works.
export const PRELOAD_FIRST = 4
export const PRELOAD_MAX_WAIT_MS = 6000
/** Whether the "preparing clips" overlay may close. `total`/`done` count clips to preload. */
export function preloadReady(s: { loaded: boolean; failed: boolean; timedOut: boolean; total: number; done: number }) {
  if (s.failed || s.timedOut) return true
  return s.loaded && s.done >= Math.min(s.total, PRELOAD_FIRST)
}

// ---------------------------------------------------------------- demo curation
// OFF by default: the UI shows exactly what the API returns. Everything below that
// hides, reclassifies, reorders or re-times alerts only acts in mock mode when explicitly enabled.
export const isDemoCurationEnabled = (useMocks: boolean, requested: string | undefined) =>
  useMocks && requested === '1'
export const DEMO_CURATION = isDemoCurationEnabled(USE_MOCKS, import.meta.env.VITE_DEMO_CURATION)

// ---------------------------------------------------------------- pitch order (MOCK)
// For the pitch the queue leads with aggressive driving rather than plain speeding.
// Display-only: the backend keeps its own priorities.
const DEMO_RANK: Record<string, number> = {
  probable_crash: 0, wrong_way: 1, tailgating: 2, dangerous_lane_change: 3, hard_braking: 4,
  stopped_on_road: 5, stopped_emergency_lane: 6, very_high_speed: 7, congestion: 8,
}
// A rejected alert never leads the queue, whatever its type or age.
const rejectedLast = (a: Alert) => Number(a.status === 'rejected')
export const demoSort = (a: Alert, b: Alert) =>
<<<<<<< INTEGRATION
  (DEMO_RANK[a.type] ?? 6) - (DEMO_RANK[b.type] ?? 6) || b.createdAt.localeCompare(a.createdAt)
=======
  rejectedLast(a) - rejectedLast(b) ||
  (DEMO_CURATION ? (DEMO_RANK[a.type] ?? 6) - (DEMO_RANK[b.type] ?? 6) : 0) ||
  b.createdAt.localeCompare(a.createdAt)
>>>>>>> GITHUB_TARGET

// ---------------------------------------------------------------- "acum X"
// The real age of the alert: a staged "acum 4 s" would present old footage as live detection.
export function demoAgo(alert: Alert) {
<<<<<<< INTEGRATION
  const at = (DEMO_CURATION ? fakeCreated.get(alert.id) : undefined) ?? new Date(alert.createdAt).getTime()
=======
  const at = new Date(alert.createdAt).getTime()
>>>>>>> GITHUB_TARGET
  const sec = Math.max(1, Math.round((Date.now() - at) / 1000))
  if (sec < 60) return `acum ${sec} s`
  return formatDistanceToNowStrict(at, { locale: ro, addSuffix: true })
}

// ---------------------------------------------------------------- manual curation (MOCK)
// Every clip on the production demo tenant was reviewed on 2026-11-10 (frame rate measured,
// frames inspected). The demo cameras have guessed calibrations and the stock clips were
// processed several times, so most rows are duplicates of one moment or false positives.
// The kept alerts come from the last run (194-228), whose clips outline each vehicle with
// the detector's box; earlier runs drew the tracker's box, which trails the vehicle.
// Display-only: the backend keeps the original rows.
<<<<<<< INTEGRATION
const RECLASSIFY_ALL: Record<string, { type: Alert['type']; severity?: Alert['severity']; rule?: string }> = {
  '107': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față (autostradă)' },
  '96': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
  '99': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
  '100': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
}
/** False positives and duplicates of the same moment from earlier pipeline runs. */
const HIDDEN_IDS_ALL = new Set([
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
])
export const RECLASSIFY = DEMO_CURATION ? RECLASSIFY_ALL : {}
export const HIDDEN_IDS: Set<string> = DEMO_CURATION ? HIDDEN_IDS_ALL : new Set()
=======
export const RECLASSIFY: Record<string, { type: Alert['type']; severity?: Alert['severity']; rule?: string }> = DEMO_CURATION ? {
  '195': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față (autostradă)' },
  '210': { type: 'tailgating', severity: 'high', rule: 'Distanță prea mică față de vehiculul din față' },
} : {}
/** The alerts whose clip plays smoothly and shows what the alert says:
 *  highway 195 (close following) and 198 (154 km/h); underpass 199 (queue);
 *  night bridge 202 and 205 (speeding on a 50 km/h road) and 210 (close following). */
export const KEPT_IDS = new Set(['195', '198', '199', '202', '205', '210'])
/** Last alert number covered by that review. A later alert is shown until it is reviewed. */
export const REVIEWED_UP_TO = 228
/** Hidden: repeats of a kept moment, the New York avenue clips (turns at a junction read as
 *  lane changes, a bus at a red light read as a crash), speeds under the limit, and every
 *  Piața Unirii clip (5 to 16 frames per second, trams read as crashes, speeds from a rough
 *  calibration). */
export const HIDDEN_IDS = new Set<string>(DEMO_CURATION
  ? Array.from({ length: REVIEWED_UP_TO }, (_, i) => String(i + 1)).filter((id) => !KEPT_IDS.has(id))
  : [])
>>>>>>> GITHUB_TARGET
export function curate(alert: Alert): Alert {
  if (!DEMO_CURATION) return alert
  const fix = RECLASSIFY[alert.id]
  return replay(fix ? { ...alert, type: fix.type, severity: fix.severity ?? alert.severity, ruleId: fix.type, ruleSummary: fix.rule ?? alert.ruleSummary } : alert)
}

// ---------------------------------------------------------------- confirm replay (MOCK)
<<<<<<< INTEGRATION
// Alerts already decided in the backend, shown as new so the pitch can show a confirmation.
// The backend answers 409 (already decided); the decision is then kept in this tab only,
// so a page reload shows them as new again.
export const DEMO_UNDECIDED: Set<string> = DEMO_CURATION ? new Set(['99', '107', '118']) : new Set()
=======
// Alerts shown as new on every page load, so the pitch can show a confirmation more than once.
// The backend takes the first decision and answers 409 (already decided) to later ones; either
// way the decision is kept in this tab only, so a page reload shows them as new again.
export const DEMO_UNDECIDED = new Set<string>(DEMO_CURATION ? ['195', '210'] : [])
>>>>>>> GITHUB_TARGET
type LocalDecision = { status: 'confirmed' | 'rejected'; by: string; at: string; note?: string }
export const localDecisions = new Map<string, LocalDecision>()

const reallyRejected = new Set<string>()
function replay(alert: Alert): Alert {
  if (!DEMO_UNDECIDED.has(alert.id)) return alert
  const d = localDecisions.get(alert.id)
  if (d) return { ...alert, status: d.status, decidedBy: d.by, decidedAt: d.at, decisionNote: d.note }
  // An alert the operator really rejected is never replayed as new; it keeps its history too.
  if (alert.status === 'rejected') { reallyRejected.add(alert.id); return alert }
  return { ...alert, status: 'new', decidedBy: undefined, decidedAt: undefined, decisionNote: undefined }
}
/** Hides the backend's earlier decision on replayed alerts from the history. */
export const keepAudit = (e: AuditEntry) =>
  !(e.target && DEMO_UNDECIDED.has(e.target) && !reallyRejected.has(e.target) && !e.id.startsWith('local-') && ['confirmed', 'rejected'].includes(e.action))
