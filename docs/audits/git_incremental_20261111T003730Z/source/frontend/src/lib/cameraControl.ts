// Camera control plane client (backend: /api/camera-control, see docs/camera-config-contract.md).
// The server enforces every permission and four-eyes rule; the UI only hides what it cannot use.
import { api, post } from './api'

export type Lifecycle = 'legacy' | 'discovered' | 'onboarding' | 'approved' | 'disabled'
export type SourceKind = 'recorded_replay' | 'owned_optical_live' | 'authorized_network_live'
export type VersionStatus = 'draft' | 'validated' | 'awaiting_approval' | 'approved' | 'active' | 'superseded' | 'rejected'

export interface Unmet { code: string; message: string }
export interface ConfigError { path: string; code: string; message: string }
export interface Runtime {
  state: string; is_live: boolean; freshness: 'never' | 'fresh' | 'stale' | 'offline'
  heartbeat_age_s: number | null; stale_after_s: number; offline_after_s: number
  runnable: boolean; blocked_reason: string | null; unmet: Unmet[]
  desired_revision: number | null; desired_fingerprint: string | null
  applied_revision: number | null; applied_fingerprint: string | null; revision_in_sync: boolean
  reference_frame_mismatch: boolean | null; duplicate_worker: boolean; server_time: string
  source_attestation: Attestation
}
export type Attestation = 'match' | 'mismatch' | 'unreported' | 'unknown'
export interface ControlSummary {
  id: string; slug: string; name: string; location: string; timezone: string
  lifecycle_state: Lifecycle; source_kind: SourceKind | null; source_display: string | null
  source_has_credentials: boolean; desired_enabled: boolean; revision: number
  active_version_id: string | null; disabled_reason: string | null
  enable_requested_by: string | null; enable_requested_at: string | null; runtime: Runtime
}
export interface Grant {
  id: string; granting_party: string; basis: string; basis_reference: string; purpose: string
  valid_from: string; valid_until: string; capture_method: SourceKind; max_analysis_fps: number
  max_frame_height: number; retention_days: number; export_allowed: boolean; media_scope: string
  status: 'active' | 'revoked'; revoked_at: string | null; revocation_reason: string | null
}
export interface Worker {
  lease_epoch: string | null; last_heartbeat_at: string | null; health: string | null
  applied_revision: number | null; last_ack_status: string | null; last_ack_revision: number | null
  last_ack_reason: string | null; source_fps: number | null; processing_fps: number | null
  last_frame_at: string | null; dropped_frames: number | null; queue_depth: number | null
  model_id: string | null; frame_width: number | null; frame_height: number | null
  last_error_code: string | null; last_error: string | null; conflict_epoch: string | null
  retries: number | null; inference_p50_ms: number | null; inference_p95_ms: number | null
  rss_mb: number | null; frozen_signal: number | null; frozen_confidence: number | null; unchanged_s: number | null
}
export interface ControlDetail extends ControlSummary {
  worker: Worker | null; grants: Grant[]
  eligibility: { eligible: boolean; unmet: Unmet[]; version_id: string | null }
  unsupported_actions: Record<string, string>
}
export interface Version {
  id: string; revision: number; fingerprint: string; status: VersionStatus; reason: string
  validation_errors: ConfigError[]; created_by: string; created_at: string
  submitted_by: string | null; decided_by: string | null; decision_note: string | null
  activated_at: string | null; activation_reason: string | null
}
export interface VersionWithConfig extends Version { config: Record<string, unknown> }
export interface Change { path: string; op: 'added' | 'removed' | 'changed'; before: unknown; after: unknown }
export interface HealthEvent { at: string; kind: string; worker_epoch: string | null; health: string | null; revision: number | null; reason_code: string | null; message: string | null }

const BASE = '/api/camera-control/cameras'
const cam = (id: string) => `${BASE}/${encodeURIComponent(id)}`

export const listControl = () => api<ControlSummary[]>(BASE)
export const getControl = (id: string) => api<ControlDetail>(cam(id))
export const listVersions = (id: string) => api<Version[]>(`${cam(id)}/versions`)
export const getVersion = (id: string, v: string) => api<VersionWithConfig>(`${cam(id)}/versions/${v}`)
export const diffVersion = (id: string, v: string) => api<{ from_revision: number | null; changes: Change[] }>(`${cam(id)}/versions/${v}/diff`)
export const healthHistory = (id: string, limit = 20) => api<HealthEvent[]>(`${cam(id)}/health?limit=${limit}`)
export const validateDraft = (id: string, config: unknown) => post<{ valid: boolean; errors: ConfigError[]; fingerprint: string }>(`${cam(id)}/config/validate`, { config })
export const createDraft = (id: string, config: unknown, reason: string) => post<VersionWithConfig>(`${cam(id)}/versions`, { config, reason })
export type VersionAction = 'validate' | 'submit' | 'approve' | 'reject'
export const versionAction = (id: string, v: string, action: VersionAction, note?: string) =>
  post<Version>(`${cam(id)}/versions/${v}/${action}`, action === 'approve' || action === 'reject' ? { note } : {})
export const activate = (id: string, versionId: string, expectedRevision: number, reason: string, rollback = false) =>
  post<{ changed: boolean }>(`${cam(id)}/${rollback ? 'rollback' : 'activate'}`, { version_id: versionId, expected_revision: expectedRevision, reason })
export interface GrantInput {
  granting_party: string; basis: 'written_agreement' | 'licence' | 'own_infrastructure' | 'statutory_mandate'; basis_reference: string
  purpose: string; valid_from: string; valid_until: string; capture_method: SourceKind; max_analysis_fps: number
  max_frame_height: number; retention_days: number; export_allowed: boolean; media_scope: 'events_only' | 'events_and_recordings'
}
/** Registers a camera in the "onboarding" state: never enabled by creation. */
export const createCamera = (body: { name: string; location: string; slug?: string }) => post<{ id: string; slug: string }>('/api/cameras', body)
/** The full source address is never returned; responses carry only its short display form. */
export const registerSource = (id: string, kind: SourceKind, url: string, expectedRevision: number, reason: string) =>
  post<ControlSummary>(`${cam(id)}/source`, { kind, url, expected_revision: expectedRevision, reason })
export const createGrant = (id: string, body: GrantInput) => post<Grant>(`${cam(id)}/grants`, body)
export const revokeGrant = (id: string, grantId: string, reason: string) => post<Grant>(`${cam(id)}/grants/${grantId}/revoke`, { reason })
export type CameraAction = 'pause' | 'resume' | 'disable' | 'enable-request' | 'enable'
export const cameraAction = (id: string, action: CameraAction, expectedRevision: number, reason: string) =>
  post<ControlSummary>(`${cam(id)}/${action}`, { expected_revision: expectedRevision, reason })

// --------------------------------------------------------------------------- labels (ro)

export const LIFECYCLE_LABEL: Record<Lifecycle, string> = {
  legacy: 'Înregistrată anterior (necontrolată)', discovered: 'Candidat descoperit', onboarding: 'În configurare',
  approved: 'Aprobată', disabled: 'Dezactivată',
}
export const SOURCE_LABEL: Record<SourceKind, string> = {
  recorded_replay: 'Înregistrare redată (replay)', owned_optical_live: 'Cameră optică proprie (live)',
  authorized_network_live: 'Sursă de rețea autorizată (live)',
}
export const VERSION_LABEL: Record<VersionStatus, string> = {
  draft: 'Ciornă', validated: 'Validată', awaiting_approval: 'Așteaptă aprobare', approved: 'Aprobată',
  active: 'Activă', superseded: 'Înlocuită', rejected: 'Respinsă',
}
/** Runtime state → badge text. Only `live` (a fresh, healthy live source) is ever LIVE. */
export const STATE_LABEL: Record<string, string> = {
  live: 'LIVE', replay: 'REDARE (nu e live)', processing: 'Procesare (sursă nedeclarată)', stale: 'Semnal învechit',
  never_seen: 'Niciun semnal', paused: 'În pauză', disabled: 'Dezactivată', onboarding: 'În configurare',
  not_onboarded: 'Neînregistrată', permission_blocked: 'Blocată: autorizare lipsă', reconnecting: 'Se reconectează',
  source_failed: 'Sursă indisponibilă', decoder_failed: 'Eroare decodare', model_unavailable: 'Model indisponibil',
  config_rejected: 'Configurație respinsă', auth_failed: 'Autentificare eșuată', starting: 'Pornire', stopped: 'Oprită',
  frozen_image: 'Imagine înghețată', source_mismatch: 'Sursă diferită de cea înregistrată',
}
/** Does the worker holding the lease report the registered source? (Detects misconfiguration;
 *  a worker with a valid key could still lie.) */
export const ATTESTATION_LABEL: Record<Attestation, string> = {
  match: 'corespunde sursei înregistrate', mismatch: 'NU corespunde sursei înregistrate',
  unreported: 'neraportată de niciun worker activ', unknown: 'necunoscută (sursa a fost înregistrată înainte de atestare)',
}
export const stateTone = (state: string) =>
  state === 'live' ? 'live' : state === 'replay' || state === 'processing' ? 'info'
    : ['paused', 'onboarding', 'never_seen', 'not_onboarded', 'starting'].includes(state) ? 'muted' : 'bad'

export type ConfigStage = 'none' | 'requested' | 'rejected' | 'applied' | 'effective'
/** Where the activated revision stands. Activation is only a request: a revision is "applied"
 *  once a worker acknowledged it, and "in effect" only while a worker with a fresh signal runs it. */
export function configStage(rt: Runtime, worker: Pick<Worker, 'health' | 'last_ack_status' | 'last_ack_revision' | 'last_ack_reason'> | null): { stage: ConfigStage; label: string; detail: string } {
  if (rt.desired_revision == null) return { stage: 'none', label: 'Nicio configurație activată', detail: 'camera nu are o versiune aprobată și activată' }
  if (!rt.revision_in_sync) {
    if (worker?.last_ack_status === 'rejected' && worker.last_ack_revision === rt.desired_revision) {
      return { stage: 'rejected', label: 'Respinsă de worker', detail: `worker-ul a refuzat revizia ${rt.desired_revision} (${worker.last_ack_reason ?? 'fără motiv raportat'}) și rulează în continuare ${rt.applied_revision == null ? 'fără configurație' : `revizia ${rt.applied_revision}`}` }
    }
    return { stage: 'requested', label: 'Cerută, neaplicată încă', detail: rt.applied_revision == null ? `niciun worker nu a confirmat revizia ${rt.desired_revision}` : `worker-ul rulează încă revizia ${rt.applied_revision}` }
  }
  const running = rt.freshness === 'fresh' && worker?.health !== 'stopped' && ['live', 'replay', 'processing'].includes(rt.state)
  return running
    ? { stage: 'effective', label: 'În vigoare', detail: `un worker rulează acum revizia ${rt.desired_revision} (semnal ${ageLabel(rt.heartbeat_age_s)})` }
    : { stage: 'applied', label: 'Aplicată de worker', detail: `revizia ${rt.desired_revision} a fost confirmată, dar acum niciun worker nu o rulează (ultimul semnal ${ageLabel(rt.heartbeat_age_s)})` }
}

export function ageLabel(seconds: number | null) {
  if (seconds == null) return 'niciodată'
  if (seconds < 90) return `acum ${Math.round(seconds)} s`
  if (seconds < 3600) return `acum ${Math.round(seconds / 60)} min`
  return `acum ${Math.round(seconds / 3600)} h`
}

/** A measured number with its unit, or an em dash when the worker did not send it. */
export function metric(value: number | null | undefined, unit: string, digits = 0) {
  if (value == null) return '—'
  return `${value.toLocaleString('ro-RO', { maximumFractionDigits: digits, minimumFractionDigits: digits })} ${unit}`.trim()
}

/** Frozen-image check as reported by the worker: never claims more than the signal shows. */
export function frozenLabel(health: string | null, w: Pick<Worker, 'frozen_signal' | 'frozen_confidence' | 'unchanged_s'>) {
  if (w.frozen_signal == null && w.unchanged_s == null) return 'nemăsurat'
  const detail = `diferență ${metric(w.frozen_signal, '', 2)}, neschimbat ${metric(w.unchanged_s, 's', 0)}, încredere ${metric(w.frozen_confidence, '', 2)}`
  if (health === 'frozen_image') return `DA, imagine înghețată (${detail})`
  if ((w.frozen_confidence ?? 0) > 0) return `suspect, neconfirmat (${detail})`
  return `nu (${detail})`
}
