import type { VehicleClass, Alert, AlertType, AuditEntry, Camera, Severity, VlmVerdict, ArchiveClip } from '@/types'
import { mediaUrl } from './api'
import { IASI_CAMERAS, iasiCameraName } from './iasi'

export interface ApiAudit { id: number; event_id: number | null; actor: string; action: AuditEntry['action']; note: string | null; at: string; type?: string }
export interface ApiEvent {
  id: number; camera_id: string; camera_name: string | null; location: string | null
  type: AlertType; priority: Severity; occurred_at: string; video_t: number
  track_id: number | null; object_class: string | null; speed_kmh: number | null
  rule: string; details: Record<string, unknown>; keyframe_url: string | null; clip_url: string | null
  vlm_status: VlmVerdict; vlm_text: string | null; status: 'new' | 'confirmed' | 'rejected'; action: string | null
  audit?: ApiAudit[]; redaction?: string
}
export interface ApiCameraStatus { fps?: number | null; processing_fps?: number | null; detections?: number; unique_tracks?: number; tracks_by_class?: Record<string, number>; inference_latency_ms_p50?: number | null; inference_latency_ms_p95?: number | null; inference_latency_ms_p99?: number | null; process_peak_rss_mb?: number | null; model?: string | null; model_sha256?: string | null; rules?: Record<string, { supported: boolean; min_fps: number; reason?: string | null }>; source?: { kind: 'file' | 'network'; state: 'waiting' | 'healthy' | 'stale'; replay?: boolean; width?: number | null; height?: number | null; reconnects?: number }; traffic?: { total_crossings: number; rolling_flow_per_minute: { total: number; window_seconds: number }; counts_by_line_lane_class: Array<{ line: string; lane: string; object_class: string; count: number }> }; reported_at?: string }
export interface ApiCamera { id: string; uuid?: string; name: string; location: string | null; video_url: string | null; timezone?: string; latitude?: number | null; longitude?: number | null; is_active?: boolean; last_seen_at?: string | null; status_info?: ApiCameraStatus | null }
export interface ApiStats { total: number; by_priority: Record<Severity, number>; by_status: Record<string, number>; by_type: Record<string, number>; vlm_available: boolean }
export interface ApiMeta { event_types: Record<string, { label: string; priority: Severity }>; actions: Record<string, string> }

// The audit API sends the actor's name but not their role, so no role is shown ('anonim' renders as none).
export const adaptAudit = (entry: ApiAudit): AuditEntry => ({
  id: String(entry.id), at: entry.at, username: entry.actor, role: 'anonim', action: entry.action,
  target: entry.event_id === null ? undefined : String(entry.event_id), details: entry.note ?? undefined,
})
const OBJECT_CLASS_RO: Record<string, VehicleClass | undefined> = { car: 'autoturism', truck: 'camion', bus: 'autobuz', motorcycle: 'motocicleta', person: 'pieton', object: 'obiect' }
export function adaptEvent(event: ApiEvent): Alert {
  const decision = event.audit?.find((entry) => ['confirmed', 'rejected'].includes(entry.action))
  return {
    id: String(event.id), type: event.type, severity: event.priority, cameraId: event.camera_id,
    createdAt: event.occurred_at, status: event.status, ruleId: event.type, ruleSummary: `${event.details.synthetic === true ? '[SYNTHETIC TEST] ' : ''}${event.details.origin === 'recorded_upload' ? '[RECORDED] ' : event.details.origin === 'local_replay' ? '[LOCAL RECORDED REPLAY] ' : event.details.origin === 'live_camera' ? '[LIVE] ' : '[SOURCE UNVERIFIED] '}${event.rule}`,
    vlm: { verdict: event.vlm_status, description: event.vlm_text ?? '' },
    metrics: { vehicleClass: OBJECT_CLASS_RO[event.object_class ?? ''], speedKmh: event.speed_kmh ?? undefined, speedLimitKmh: typeof event.details.limit_kmh === 'number' ? event.details.limit_kmh : undefined,
      lowConfidence: event.details.confidence === 'low', speedApprox: event.details.speed_calibration !== 'validated' },
    detection: {
      trackId: event.track_id,
      sourceTimeSec: event.video_t,
      confidence: typeof event.details.detection_confidence === 'number' ? event.details.detection_confidence : undefined,
      modelId: typeof event.details.model_id === 'string' ? event.details.model_id : undefined,
      modelSha256: typeof event.details.model_sha256 === 'string' ? event.details.model_sha256 : undefined,
      sourceProvenance: typeof event.details.source_provenance === 'object' && event.details.source_provenance !== null
        ? event.details.source_provenance as { title?: string; url?: string; author?: string; license?: string; sha256?: string }
        : undefined,
    },
    clip: { durationSec: 0, src: mediaUrl(event.clip_url) }, keyframeUrl: mediaUrl(event.keyframe_url),
    frames: [], actions: [], viewedBy: event.audit?.filter((a) => a.action === 'viewed').map((a) => a.actor) ?? [],
    decidedBy: decision?.actor, decidedAt: decision?.at, decisionNote: decision?.note ?? undefined,
    redaction: event.details.synthetic === true && event.details.source === 'app.services.seed' ? 'synthetic' : event.redaction,
  }
}
/** External public stream (third-party host, not covered by the gateway CSP): opt-in demo only. */
export const LIVE_STREAM = import.meta.env.VITE_LIVE_STREAM === '1'
// The live pipeline sends a heartbeat every 30 s; a camera counts as live for 2 minutes after.
const LIVE_WINDOW_MS = 2 * 60 * 1000
export const isLive = (lastSeenAt?: string | null, now = Date.now()) =>
  !!lastSeenAt && now - new Date(lastSeenAt).getTime() < LIVE_WINDOW_MS
export const adaptCamera = (camera: ApiCamera): Camera => {
  const live = camera.is_active !== false && isLive(camera.last_seen_at)
  const sourceState = camera.status_info?.source?.state
  const status = camera.is_active === false
    ? 'offline'
    : sourceState === 'stale' || sourceState === 'waiting'
      ? 'degraded'
      : live ? 'online' : 'degraded'
  return {
<<<<<<< INTEGRATION
    id: camera.id, backendUuid: camera.uuid, timezone: camera.timezone ?? 'Europe/Bucharest', isActive: camera.is_active !== false,
    name: camera.name || IASI_CAMERAS[camera.id]?.name || camera.id, road: camera.location ?? IASI_CAMERAS[camera.id]?.location ?? '', direction: '',
    lat: camera.latitude ?? IASI_CAMERAS[camera.id]?.lat ?? NaN, lng: camera.longitude ?? IASI_CAMERAS[camera.id]?.lng ?? NaN, status, fps: camera.status_info?.fps ?? 0,
    processingFps: camera.status_info?.processing_fps ?? 0, detections: camera.status_info?.detections ?? 0, uniqueTracks: camera.status_info?.unique_tracks ?? 0,
    tracksByClass: camera.status_info?.tracks_by_class ?? {}, inferenceLatencyP50Ms: camera.status_info?.inference_latency_ms_p50 ?? undefined,
    inferenceLatencyP95Ms: camera.status_info?.inference_latency_ms_p95 ?? undefined, model: camera.status_info?.model ?? undefined,
    inferenceLatencyP99Ms: camera.status_info?.inference_latency_ms_p99 ?? undefined, processPeakRssMb: camera.status_info?.process_peak_rss_mb ?? undefined,
    modelSha256: camera.status_info?.model_sha256 ?? undefined, calibrated: false,
    telemetryAt: camera.status_info?.reported_at,
    unsupportedRules: Object.entries(camera.status_info?.rules ?? {}).filter(([, r]) => !r.supported).map(([rule, r]) => ({ rule, reason: r.reason ?? '' })), traffic: camera.status_info?.traffic,
    sourceHealth: camera.status_info?.source ? { ...camera.status_info.source, replay: camera.status_info.source.replay ?? camera.status_info.source.kind === 'file' } : undefined, unit: '', videoUrl: mediaUrl(camera.video_url),
    liveUrl: LIVE_STREAM ? IASI_CAMERAS[camera.id]?.liveUrl : undefined, live,
=======
    id: camera.id, name: iasiCameraName(camera.id) ?? camera.name, road: IASI_CAMERAS[camera.id]?.location ?? camera.location ?? '', direction: '',
    lat: camera.latitude ?? IASI_CAMERAS[camera.id]?.lat ?? NaN, lng: camera.longitude ?? IASI_CAMERAS[camera.id]?.lng ?? NaN, status: camera.is_active === false ? 'offline' : heartbeat || camera.video_url ? 'online' : 'degraded', fps: 0, calibrated: false, unit: '', videoUrl: mediaUrl(camera.video_url),
    liveUrl: IASI_CAMERAS[camera.id]?.liveUrl, heartbeat, live,
>>>>>>> GITHUB_TARGET
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
