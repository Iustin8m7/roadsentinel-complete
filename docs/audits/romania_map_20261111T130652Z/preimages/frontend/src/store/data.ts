import { create } from 'zustand'
import { api, ApiError, post, USE_MOCKS } from '@/lib/api'
import { adaptAudit, adaptCamera, adaptEvent, adaptStats, type ApiAudit, type ApiCamera, type ApiEvent, type ApiMeta, type ApiStats } from '@/lib/adapters'
import { ALERT_TYPE } from '@/lib/constants'
import type { Alert, Camera, AuditEntry } from '@/types'
import { useDataStore as mockStore } from './mock-data'
import { CAMERAS } from '@/mocks/cameras'
import { mergeAudit, useAuditStore } from './audit'
import { curate, DEMO_CURATION, DEMO_UNDECIDED, HIDDEN_IDS, keepAudit, localDecisions } from '@/lib/demo'
import { useAuthStore } from './auth'
export type { Settings } from './mock-data'

type State = ReturnType<typeof mockStore.getState> & {
  cameras: Camera[]; stats: ReturnType<typeof adaptStats> | null; actions: Record<string, string>; error: string | null; loaded: boolean
}
const unsupported = () => { realStore.setState({ error: 'Această funcție este disponibilă doar în modul demo.' }) }
const realStore = create<State>((set) => ({
  alerts: [], rules: [], patrols: [], archive: [], cameras: [], stats: null, actions: {}, error: null, loaded: false,
  settings: { liveFeed: true, liveIntervalSec: 30, soundOnCritical: true, blurByDefault: true },
  markViewed(id) { void loadDetail(id, true).catch(reportError) },
  startReview() {},
  confirmAlert(id, note) { void decide(id, 'confirm', Object.keys(realStore.getState().actions)[0], note).catch(reportError) },
  rejectAlert(id, note) { void decide(id, 'reject', undefined, note).catch(reportError) },
  addAction: unsupported, closeAlert: unsupported, toggleRule: unsupported, updateRule: unsupported,
  setPatrolStatus: unsupported, resetDemo: unsupported,
  pushLiveAlert() { throw new Error('Synthetic alerts require VITE_USE_MOCKS=1') },
  updateSettings(patch) { set((state) => ({ settings: { ...state.settings, ...patch } })) },
}))
export const useDataStore = USE_MOCKS ? mockStore as unknown as typeof realStore : realStore
if (USE_MOCKS) useDataStore.setState({ cameras: CAMERAS, stats: null, actions: {}, error: null, loaded: true })
export const cameraById = (id: string) => useDataStore.getState().cameras.find((camera) => camera.id === id)
export function reportError(error: unknown) { realStore.setState({ error: error instanceof Error ? error.message : 'Eroare de conexiune.' }) }
/** Alert types hidden from the UI (pedestrian-on-road was all false positives in the demo zones). */
export const HIDDEN_TYPES = new Set<string>(DEMO_CURATION ? ['pedestrian_on_road'] : [])
export const isShown = (alert: Alert) => !HIDDEN_TYPES.has(alert.type) && !HIDDEN_IDS.has(alert.id)
export function upsertAlert(raw: Alert) {
  const alert = curate(raw)
  if (!isShown(alert)) return
  realStore.setState((state) => ({ alerts: [alert, ...state.alerts.filter((a) => a.id !== alert.id)] }))
}
export async function reloadStats() {
  if (!useAuthStore.getState().user?.backendPermissions?.includes('stats:read')) return
  realStore.setState({ stats: adaptStats(await api<ApiStats>('/api/stats')) })
}
export async function reloadData() {
  const permissions = useAuthStore.getState().user?.backendPermissions ?? []
  if (!permissions.includes('alerts:read')) {
    realStore.setState({alerts: [], cameras: [], stats: null, actions: {}, error: null, loaded: true})
    if (permissions.includes('audit:read')) {
      const chain = await api<Array<{seq:number;ts:string;actor_id:string|null;action:string;resource_id:string|null;details:Record<string,unknown>}>>('/api/audit/chain?limit=100')
      useAuditStore.setState({entries:chain.map(row => ({id:String(row.seq),at:row.ts,username:row.actor_id ?? 'system',role:'anonim' as const,action:row.action as AuditEntry['action'],target:row.resource_id ?? undefined,details:JSON.stringify(row.details)}))})
    }
    return
  }
  const [events, cameras, stats, meta, audit] = await Promise.all([
    api<ApiEvent[]>('/api/events'), api<ApiCamera[]>('/api/cameras'), permissions.includes('stats:read') ? api<ApiStats>('/api/stats') : Promise.resolve(null),
    api<ApiMeta>('/api/meta'), api<ApiAudit[]>('/api/audit?limit=100'),
  ])
  for (const [key, value] of Object.entries(meta.event_types)) {
    ALERT_TYPE[key as keyof typeof ALERT_TYPE] = { label: value.label, severity: value.priority }
  }
  realStore.setState({ alerts: events.map((e) => curate(adaptEvent(e))).filter(isShown), cameras: cameras.map(adaptCamera), stats: stats ? adaptStats(stats) : null, actions: meta.actions, error: null, loaded: true })
  useAuditStore.setState({ entries: audit.map(adaptAudit).filter(keepAudit) })
}
export async function loadDetail(id: string, viewed = false) {
  if (viewed) await post(`/api/events/${encodeURIComponent(id)}/view`)
  const event = await api<ApiEvent>(`/api/events/${encodeURIComponent(id)}`)
  upsertAlert(adaptEvent(event))
  if (event.audit) mergeAudit(event.audit.map(adaptAudit).filter(keepAudit))
}
export async function decide(id: string, decision: 'confirm' | 'reject', action?: string, note?: string) {
  // Replayed alert: the decision is kept in the tab, whether the backend took it now or holds an earlier one.
  const keepInTab = () => {
    const at = new Date().toISOString()
    const by = useAuthStore.getState().user?.username ?? 'operator'
    const status = decision === 'confirm' ? 'confirmed' : 'rejected'
    localDecisions.set(id, { status, by, at, note })
    const current = realStore.getState().alerts.find((a) => a.id === id)
    if (current) upsertAlert(current)
    mergeAudit([{ id: `local-${id}-${Date.now()}`, at, username: by, role: 'operator', action: status, target: id, details: note }])
  }
  try {
    const event = await post<ApiEvent>(`/api/events/${encodeURIComponent(id)}/decision`, { decision, action, note })
    if (DEMO_UNDECIDED.has(id)) return keepInTab()
    upsertAlert(adaptEvent(event))
    if (event.audit) mergeAudit(event.audit.map(adaptAudit).filter(keepAudit))
  } catch (error) {
    if (error instanceof ApiError && error.status === 409 && DEMO_UNDECIDED.has(id)) return keepInTab()
    if (error instanceof ApiError && error.status === 409) await loadDetail(id)
    throw error
  }
}
