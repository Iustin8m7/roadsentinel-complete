import type { VehicleClass, Alert, AlertType, AuditEntry, Camera, Severity, VlmVerdict, ArchiveClip } from '@/types'
import { mediaUrl } from './api'
import { IASI_CAMERAS } from './iasi'

export interface ApiAudit { id: number; event_id: number | null; actor: string; action: AuditEntry['action']; note: string | null; at: string; type?: string }
export interface ApiEvent {
  id: number; camera_id: string; camera_name: string | null; location: string | null
  type: AlertType; priority: Severity; occurred_at: string; video_t: number
  track_id: number | null; object_class: string | null; speed_kmh: number | null
  rule: string; details: Record<string, unknown>; keyframe_url: string | null; clip_url: string | null
  vlm_status: VlmVerdict; vlm_text: string | null; status: 'new' | 'confirmed' | 'rejected'; action: string | null
  audit?: ApiAudit[]; redaction?: string
}
export interface ApiCamera { id: string; name: string; location: string | null; video_url: string | null; latitude?: number | null; longitude?: number | null; is_active?: boolean; last_seen_at?: string | null; source_kind?: string | null }
export interface ApiStats { total: number; by_priority: Record<Severity, number>; by_status: Record<string, number>; by_type: Record<string, number>; vlm_available: boolean }
export interface ApiMeta { event_types: Record<string, { label: string; priority: Severity }>; actions: Record<string, string> }

export const adaptAudit = (entry: ApiAudit): AuditEntry => ({
  id: String(entry.id), at: entry.at, username: entry.actor, role: 'operator', action: entry.action,
  target: entry.event_id === null ? undefined : String(entry.event_id), details: entry.note ?? undefined,
})
const OBJECT_CLASS_RO: Record<string, VehicleClass | undefined> = { car: 'autoturism', truck: 'camion', bus: 'autobuz', motorcycle: 'motocicleta', person: 'pieton' }
export function adaptEvent(event: ApiEvent): Alert {
  const decision = event.audit?.find((entry) => ['confirmed', 'rejected'].includes(entry.action))
  return {
    id: String(event.id), type: event.type, severity: event.priority, cameraId: event.camera_id,
    createdAt: event.occurred_at, status: event.status, ruleId: event.type, ruleSummary: event.rule,
    vlm: { verdict: event.vlm_status, description: event.vlm_text ?? '' },
    metrics: { vehicleClass: OBJECT_CLASS_RO[event.object_class ?? ''], speedKmh: event.speed_kmh ?? undefined, speedLimitKmh: typeof event.details.limit_kmh === 'number' ? event.details.limit_kmh : undefined },
    clip: { durationSec: 0, src: mediaUrl(event.clip_url) }, keyframeUrl: mediaUrl(event.keyframe_url),
    frames: [], actions: [], viewedBy: event.audit?.filter((a) => a.action === 'viewed').map((a) => a.actor) ?? [],
    decidedBy: decision?.actor, decidedAt: decision?.at, decisionNote: decision?.note ?? undefined,
    redaction: event.redaction,
  }
}
// The live pipeline sends a heartbeat every 30 s; a camera counts as live for 2 minutes after.
const LIVE_WINDOW_MS = 2 * 60 * 1000
export const isLive = (lastSeenAt?: string | null, now = Date.now()) =>
  !!lastSeenAt && now - new Date(lastSeenAt).getTime() < LIVE_WINDOW_MS
const LIVE_SOURCE_KINDS = new Set(['owned_optical_live', 'authorized_network_live'])
export const adaptCamera = (camera: ApiCamera): Camera => {
  // A recorded replay with a fresh heartbeat is not a feed at all.
  const heartbeat = camera.is_active !== false && camera.source_kind !== 'recorded_replay' && isLive(camera.last_seen_at)
  // A heartbeat proves the worker runs, not what it reads: LIVE needs a declared live source.
  const live = heartbeat && LIVE_SOURCE_KINDS.has(camera.source_kind ?? '')
  return {
    id: camera.id, name: IASI_CAMERAS[camera.id]?.name ?? camera.name, road: IASI_CAMERAS[camera.id]?.location ?? camera.location ?? '', direction: '',
    lat: camera.latitude ?? IASI_CAMERAS[camera.id]?.lat ?? NaN, lng: camera.longitude ?? IASI_CAMERAS[camera.id]?.lng ?? NaN, status: camera.is_active === false ? 'offline' : heartbeat || camera.video_url ? 'online' : 'degraded', fps: 0, calibrated: false, unit: '', videoUrl: mediaUrl(camera.video_url),
    liveUrl: IASI_CAMERAS[camera.id]?.liveUrl, heartbeat, live,
  }
}
export const adaptStats = (stats: ApiStats) => ({
  total: stats.total, open: stats.by_status.new ?? 0, confirmed: stats.by_status.confirmed ?? 0,
  rejected: stats.by_status.rejected ?? 0, bySeverity: stats.by_priority, byType: stats.by_type,
  vlmAvailable: stats.vlm_available,
})
export const adaptArchive = (event: ApiEvent): ArchiveClip => ({
  id: String(event.id), alertId: String(event.id), cameraId: event.camera_id, startedAt: event.occurred_at,
  durationSec: 0, vehicleClass: 'obiect', eventType: event.type, tags: [], description: event.vlm_text ?? event.rule, clipUrl: mediaUrl(event.clip_url),
})
