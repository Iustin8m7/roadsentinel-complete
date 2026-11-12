import { api, apiUrl, USE_MOCKS, type Me } from '@/lib/api'
import { adaptAudit, adaptEvent } from '@/lib/adapters'
import { mergeAudit } from '@/store/audit'
import { loadDetail, reloadData, reloadStats, reportError, upsertAlert } from '@/store/data'
import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import { useDataStore } from '@/store/data'
import { useAuthStore } from '@/store/auth'
import { useConnection } from '@/store/connection'
import { can, type Permission } from '@/lib/permissions'
import { SEVERITY_ORDER } from '@/lib/constants'
<<<<<<< INTEGRATION
import { assignDemoTimes, DEMO_CURATION, demoSort } from '@/lib/demo'
=======
import { demoSort } from '@/lib/demo'
>>>>>>> GITHUB_TARGET
import type { Alert, Severity } from '@/types'

const openModals: HTMLElement[] = []
const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])'

/** Modal keyboard contract: focus moves in on open (to [data-autofocus] if any), Tab stays inside,
 *  Esc calls onEscape, focus returns to the opener on close. Only the topmost modal reacts. */
export function useModalFocus(ref: RefObject<HTMLElement | null>, onEscape: () => void) {
  const escape = useRef(onEscape)
  escape.current = onEscape
  useEffect(() => {
    const root = ref.current
    if (!root) return
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    openModals.push(root)
    ;(root.querySelector<HTMLElement>('[data-autofocus]') ?? root).focus()
    const onKey = (e: KeyboardEvent) => {
      if (openModals[openModals.length - 1] !== root) return
      if (e.key === 'Escape') { escape.current(); return }
      if (e.key !== 'Tab') return
      const items = [...root.querySelectorAll<HTMLElement>(FOCUSABLE)]
      if (!items.length) { e.preventDefault(); return }
      const active = document.activeElement
      const outside = active === root || !root.contains(active)
      if (e.shiftKey && (outside || active === items[0])) { e.preventDefault(); items[items.length - 1].focus() }
      else if (!e.shiftKey && (outside || active === items[items.length - 1])) { e.preventDefault(); items[0].focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      openModals.splice(openModals.indexOf(root), 1)
      opener?.focus()
    }
  }, [ref])
}


export function useCan(p: Permission) {
  const role = useAuthStore((s) => s.user?.role)
  return can(role, p)
}

/** Simulated real-time feed: pushes a new alert every N seconds while enabled. */

// A refresh nobody asked for must not raise the operator's error banner; the next one retries.
const background = (error: unknown) => console.warn('background refresh failed', error)

export function useLiveFeed(onAlert?: (a: Alert) => void) {
  const { liveFeed, liveIntervalSec } = useDataStore((s) => s.settings)
  const mayReadAlerts = useAuthStore((s) => s.user?.backendPermissions?.includes('alerts:read') ?? false)
  const push = useDataStore((s) => s.pushLiveAlert)
  const cb = useRef(onAlert)
  cb.current = onAlert
  useEffect(() => {
    if (USE_MOCKS) useConnection.getState().set('demo')
    else void reloadData().catch(reportError)
    if (!liveFeed || (!USE_MOCKS && !mayReadAlerts)) return
    if (!USE_MOCKS) {
      const stream = new EventSource(apiUrl('/api/stream'), { withCredentials: true })
<<<<<<< INTEGRATION
      stream.onopen = () => { useConnection.getState().set('live'); void reloadData().catch(reportError) }
=======
      stream.onopen = () => { void reloadData().catch(background) }
>>>>>>> GITHUB_TARGET
      stream.addEventListener('alert', (message) => {
        try { const alert = adaptEvent(JSON.parse(message.data)); upsertAlert(alert); cb.current?.(alert); void reloadStats().catch(background) }
        catch (error) { background(error) }
      })
      stream.addEventListener('audit', (message) => {
        try {
          const entry = adaptAudit(JSON.parse(message.data))
          mergeAudit([entry])
          if (entry.target) void loadDetail(entry.target).catch(background)
          if (['confirmed', 'rejected'].includes(entry.action)) void reloadStats().catch(background)
        }
        catch (error) { background(error) }
      })
      stream.onerror = () => { useConnection.getState().set('reconnecting'); void api<Me>('/api/me').then((me) => {
        if (!me.operator && me.auth_required) { stream.close(); location.assign('/login') }
      }).catch(background) }
      return () => stream.close()
    }
    const t = setInterval(() => cb.current?.(push()), liveIntervalSec * 1000)
    return () => clearInterval(t)
  }, [liveFeed, liveIntervalSec, push, mayReadAlerts])
}

/** Re-render periodically so relative times ("acum 3 minute") stay fresh. */
export function useNow(ms = 30_000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(t)
  }, [ms])
  return now
}

export const sortBySeverity = (a: Alert, b: Alert) =>
  SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity) || b.createdAt.localeCompare(a.createdAt)

/** Open queue for the operator: new + in review, sorted by severity then time. */
export function useQueue() {
  const alerts = useDataStore((s) => s.alerts)
  return useMemo(() => {
    // Every shown alert stays in the list after a decision; its status is shown on the row.
<<<<<<< INTEGRATION
    const queue = [...alerts].sort(DEMO_CURATION ? demoSort : sortBySeverity)
    assignDemoTimes(queue)
    return queue
=======
    return [...alerts].sort(demoSort)
>>>>>>> GITHUB_TARGET
  }, [alerts])
}

export function useStats() {
  const serverStats = useDataStore((s) => s.stats)
  const alerts = useDataStore((s) => s.alerts)
  return useMemo(() => {
    const bySeverity = Object.fromEntries(SEVERITY_ORDER.map((s) => [s, 0])) as Record<Severity, number>
    const byType: Record<string, number> = {}
    const byCamera: Record<string, number> = {}
    const byHour = Array.from({ length: 24 }, () => 0)
    const byDay: Record<string, number> = {}
    let confirmed = 0
    let rejected = 0
    const responseMin: number[] = []
    for (const a of alerts) {
      bySeverity[a.severity]++
      byType[a.type] = (byType[a.type] ?? 0) + 1
      byCamera[a.cameraId] = (byCamera[a.cameraId] ?? 0) + 1
      const d = new Date(a.createdAt)
      byHour[d.getHours()]++
      const key = d.toISOString().slice(0, 10)
      byDay[key] = (byDay[key] ?? 0) + 1
      if (a.status === 'confirmed' || a.status === 'closed') confirmed++
      if (a.status === 'rejected') rejected++
      if (a.decidedAt) {
        responseMin.push((new Date(a.decidedAt).getTime() - d.getTime()) / 60_000)
      }
    }
    const open = alerts.filter((a) => a.status === 'new' || a.status === 'in_review').length
    return {
      total: alerts.length,
      open,
      confirmed,
      rejected,
      avgResponseMin: responseMin.length ? responseMin.reduce((s, x) => s + x, 0) / responseMin.length : 0,
      bySeverity,
      byType,
      byCamera,
      byHour,
      byDay: Object.entries(byDay).sort(([a], [b]) => a.localeCompare(b)),
      // Computed from the shown alerts only, so hidden types never skew the numbers.
      vlmAvailable: serverStats?.vlmAvailable ?? false,
    }
  }, [alerts, serverStats])
}
