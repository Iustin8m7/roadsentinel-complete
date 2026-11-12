import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ActionType, Alert, ArchiveClip, Patrol, Rule } from '@/types'
import { RULES, PATROLS } from '@/mocks/rules'
import { makeAlert, mulberry32, seedAlerts, seedArchive } from '@/mocks/generator'
import { useAuditStore } from './mock-audit'
import { actor } from './mock-auth'

export interface Settings {
  liveFeed: boolean
  liveIntervalSec: number
  soundOnCritical: boolean
  blurByDefault: boolean
}

interface DataState {
  alerts: Alert[]
  rules: Rule[]
  patrols: Patrol[]
  archive: ArchiveClip[]
  settings: Settings

  markViewed: (alertId: string) => void
  startReview: (alertId: string) => void
  confirmAlert: (alertId: string, note?: string) => void
  rejectAlert: (alertId: string, note: string) => void
  addAction: (alertId: string, type: ActionType, opts?: { patrolId?: string; note?: string }) => void
  closeAlert: (alertId: string) => void
  pushLiveAlert: () => Alert

  toggleRule: (ruleId: string) => void
  updateRule: (ruleId: string, patch: Partial<Pick<Rule, 'name' | 'thresholds' | 'cameraIds' | 'enabled'>>) => void

  setPatrolStatus: (patrolId: string, status: Patrol['status']) => void
  updateSettings: (patch: Partial<Settings>) => void
  resetDemo: () => void
}

const audit = (action: Parameters<ReturnType<typeof useAuditStore.getState>['log']>[0]['action'], target?: string, details?: string) =>
  useAuditStore.getState().log({ ...actor(), action, target, details })

const DEFAULT_SETTINGS: Settings = { liveFeed: true, liveIntervalSec: 30, soundOnCritical: true, blurByDefault: true }
const liveRand = mulberry32(Date.now() & 0xffff)

const initial = () => ({
  alerts: seedAlerts(),
  rules: structuredClone(RULES),
  patrols: structuredClone(PATROLS),
  archive: seedArchive(),
  settings: DEFAULT_SETTINGS,
})

const patchAlert = (alerts: Alert[], id: string, fn: (a: Alert) => Alert) => alerts.map((a) => (a.id === id ? fn(a) : a))

export const useDataStore = create<DataState>()(
  persist(
    (set, get) => ({
      ...initial(),

      markViewed(id) {
        const me = actor().username
        const a = get().alerts.find((x) => x.id === id)
        if (!a || a.viewedBy.includes(me)) return
        set((s) => ({ alerts: patchAlert(s.alerts, id, (x) => ({ ...x, viewedBy: [...x.viewedBy, me] })) }))
        audit('view_alert', id)
      },
      startReview(id) {
        set((s) => ({ alerts: patchAlert(s.alerts, id, (x) => (x.status === 'new' ? { ...x, status: 'in_review' } : x)) }))
      },
      confirmAlert(id, note) {
        const now = new Date().toISOString()
        set((s) => ({
          alerts: patchAlert(s.alerts, id, (x) => ({ ...x, status: 'confirmed', decidedBy: actor().username, decidedAt: now, decisionNote: note })),
        }))
        audit('confirm_alert', id, note)
      },
      rejectAlert(id, note) {
        const now = new Date().toISOString()
        set((s) => ({
          alerts: patchAlert(s.alerts, id, (x) => ({ ...x, status: 'rejected', decidedBy: actor().username, decidedAt: now, decisionNote: note })),
        }))
        audit('reject_alert', id, note)
      },
      addAction(id, type, opts) {
        const action = { type, at: new Date().toISOString(), by: actor().username, ...opts }
        set((s) => ({
          alerts: patchAlert(s.alerts, id, (x) => ({ ...x, actions: [...x.actions, action] })),
          patrols:
            type === 'dispatch_patrol' && opts?.patrolId
              ? s.patrols.map((p) => (p.id === opts.patrolId ? { ...p, status: 'en_route', currentAlertId: id } : p))
              : s.patrols,
        }))
        const callsign = opts?.patrolId ? get().patrols.find((p) => p.id === opts.patrolId)?.callsign : undefined
        audit(type, id, [callsign && `Patrula ${callsign}`, opts?.note].filter(Boolean).join(' — ') || undefined)
      },
      closeAlert(id) {
        set((s) => ({
          alerts: patchAlert(s.alerts, id, (x) => ({ ...x, status: 'closed' })),
          patrols: s.patrols.map((p) => (p.currentAlertId === id ? { ...p, status: 'available', currentAlertId: undefined } : p)),
        }))
        audit('close_alert', id)
      },
      pushLiveAlert() {
        const rules = get().rules.filter((r) => r.enabled)
        const type = rules.length ? rules[Math.floor(liveRand() * rules.length)].alertType : undefined
        const a = makeAlert(liveRand, new Date(), type)
        // Keep IDs unique across reloads: makeAlert's counter restarts, so derive from time.
        a.id = `RS-2026-${Date.now().toString().slice(-6)}`
        set((s) => ({ alerts: [a, ...s.alerts].slice(0, 500) }))
        return a
      },

      toggleRule(id) {
        set((s) => ({
          rules: s.rules.map((r) => (r.id === id ? { ...r, enabled: !r.enabled, updatedAt: new Date().toISOString(), updatedBy: actor().username } : r)),
        }))
        const r = get().rules.find((x) => x.id === id)
        audit('rule_toggle', id, r ? `${r.name}: ${r.enabled ? 'activată' : 'dezactivată'}` : undefined)
      },
      updateRule(id, patch) {
        set((s) => ({
          rules: s.rules.map((r) => (r.id === id ? { ...r, ...patch, updatedAt: new Date().toISOString(), updatedBy: actor().username } : r)),
        }))
        audit('rule_update', id, JSON.stringify(patch))
      },

      setPatrolStatus(id, status) {
        set((s) => ({
          patrols: s.patrols.map((p) => (p.id === id ? { ...p, status, currentAlertId: status === 'available' ? undefined : p.currentAlertId } : p)),
        }))
      },
      updateSettings(patch) {
        set((s) => ({ settings: { ...s.settings, ...patch } }))
      },
      resetDemo() {
        set(initial())
        audit('reset_demo')
      },
    }),
    { name: 'rs.data', version: 1 },
  ),
)
