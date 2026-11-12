// UI model; API wire types and adapters live in lib/adapters.ts.

export type Role = 'admin' | 'operator' | 'anchetator' | 'patrula' | 'auditor'

export interface User {
  id: string
  username: string
  password: string // mock only — never do this with a real backend
  fullName: string
  rank: string
  badge: string
  unit: string
  role: Role
  backendRole?: string
  backendPermissions?: string[]
}

export type SessionUser = Omit<User, 'password'>

export type Severity = 'critical' | 'high' | 'medium' | 'info'

export type AlertType =
  | 'pedestrian_on_road'
  | 'very_high_speed'
  | 'stopped_emergency_lane'
  | 'stopped_on_road'
  | 'wrong_way'
  | 'pedestrian_highway'
  | 'probable_crash'
  | 'road_object'
  | 'object_on_roadway'
  | 'high_speed'
  | 'emergency_lane_stop'
  | 'near_miss'
  | 'hard_braking'
  | 'tailgating'
  | 'dangerous_lane_change'
  | 'congestion'
  | 'road_conditions'

export type AlertStatus = 'new' | 'in_review' | 'confirmed' | 'rejected' | 'closed'

export type VlmVerdict = 'pending' | 'skipped' | 'confirmed' | 'rejected' | 'uncertain'

export interface KeyFrame {
  offsetSec: number
  label: string
}

export interface AlertMetrics {
  speedKmh?: number
  speedLimitKmh?: number
  dwellSec?: number
  distanceM?: number
  decelMs2?: number
  /** Speed was computed from sparse frames (slow stream): lower confidence. */
  lowConfidence?: boolean
  /** Speed comes from a calibration nobody validated against a known-speed reference. */
  speedApprox?: boolean
  vehicleClass?: VehicleClass
}

export interface AlertDetectionInfo {
  trackId?: number | null
  sourceTimeSec?: number
  confidence?: number
  modelId?: string
  modelSha256?: string
  sourceProvenance?: {
    title?: string
    url?: string
    author?: string
    license?: string
    sha256?: string
  }
}

export type VehicleClass = 'autoturism' | 'camion' | 'autobuz' | 'motocicleta' | 'pieton' | 'obiect'

export type ActionType = 'dispatch_patrol' | 'warning_sign' | 'enforcement'

export interface AlertAction {
  type: ActionType
  at: string
  by: string
  patrolId?: string
  note?: string
}

export interface Alert {
  id: string
  type: AlertType
  severity: Severity
  cameraId: string
  createdAt: string
  status: AlertStatus
  ruleId: string
  ruleSummary: string
  vlm: { verdict: VlmVerdict; confidence?: number; description: string }
  keyframeUrl?: string
  redaction?: string
  metrics: AlertMetrics
  detection?: AlertDetectionInfo
  clip: { durationSec: number; src?: string }
  frames: KeyFrame[]
  actions: AlertAction[]
  decidedBy?: string
  decidedAt?: string
  decisionNote?: string
  viewedBy: string[]
}

export type CameraStatus = 'online' | 'offline' | 'degraded'

export interface Camera {
  id: string
  /** Internal registry UUID used for authenticated camera-management mutations. */
  backendUuid?: string
  timezone?: string
  isActive?: boolean
  name: string
  road: string
  direction: string
  lat: number
  lng: number
  status: CameraStatus
  videoUrl?: string
  // Public live stream (HLS) and whether the pipeline reported in recently.
  liveUrl?: string
  live?: boolean
  /** Frame rate measured by the pipeline (0 = not reported). */
  fps: number
  processingFps?: number
  detections?: number
  uniqueTracks?: number
  tracksByClass?: Record<string, number>
  inferenceLatencyP50Ms?: number
  inferenceLatencyP95Ms?: number
  inferenceLatencyP99Ms?: number
  processPeakRssMb?: number
  model?: string
  modelSha256?: string
  telemetryAt?: string
  /** Alert types this camera cannot produce at its measured frame rate (from the heartbeat). */
  unsupportedRules?: { rule: string; reason: string }[]
  traffic?: { total_crossings: number; rolling_flow_per_minute: { total: number; window_seconds: number }; counts_by_line_lane_class: Array<{ line: string; lane: string; object_class: string; count: number }> }
  sourceHealth?: { kind: 'file' | 'network' | 'device'; transport?: 'auto' | 'file' | 'hls' | 'rtsp' | 'http_video' | 'snapshot' | 'uvc'; state: 'waiting' | 'healthy' | 'stale'; replay?: boolean; width?: number | null; height?: number | null; reconnects?: number }
  calibrated: boolean
  unit: string
}

export type ZoneKind = 'emergency_lane' | 'crosswalk' | 'one_way' | 'highway' | 'roadway' | 'intersection'

export interface Rule {
  id: string
  name: string
  alertType: AlertType
  zone: { name: string; kind: ZoneKind }
  cameraIds: string[]
  thresholds: { speedKmh?: number; dwellSec?: number; distanceM?: number; decelMs2?: number }
  enabled: boolean
  unit: string
  updatedAt: string
  updatedBy: string
}

export type PatrolStatus = 'available' | 'en_route' | 'on_scene' | 'off_duty'

export interface Patrol {
  id: string
  callsign: string
  unit: string
  vehicle: string
  status: PatrolStatus
  area: string
  currentAlertId?: string
}

export type AuditAction =
  | 'detected'
  | 'viewed'
  | 'confirmed'
  | 'rejected'
  | 'vlm_confirmed'
  | 'vlm_rejected'
  | 'vlm_uncertain'
  | 'login'
  | 'logout'
  | 'login_failed'
  | 'view_alert'
  | 'confirm_alert'
  | 'reject_alert'
  | 'dispatch_patrol'
  | 'warning_sign'
  | 'enforcement'
  | 'close_alert'
  | 'archive_search'
  | 'rule_update'
  | 'rule_toggle'
  | 'export'
  | 'reset_demo'

export interface AuditEntry {
  id: string
  at: string
  username: string
  role: Role | 'anonim'
  action: AuditAction
  target?: string
  details?: string
}

export interface ArchiveClip {
  id: string
  cameraId: string
  startedAt: string
  durationSec: number
  vehicleClass: VehicleClass
  eventType: AlertType
  tags: string[]
  description: string
  clipUrl?: string
  alertId?: string
}
