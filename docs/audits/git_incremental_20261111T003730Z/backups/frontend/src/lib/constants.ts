import type {
  ActionType,
  AlertStatus,
  AlertType,
  AuditAction,
  CameraStatus,
  PatrolStatus,
  Role,
  Severity,
  VlmVerdict,
  ZoneKind,
} from '@/types'

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'info']

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Critică',
  high: 'Ridicată',
  medium: 'Medie',
  info: 'Informativă',
}

const ALERT_TYPE_KNOWN: Record<AlertType, { label: string; severity: Severity }> = {
  pedestrian_on_road: { label: 'Pieton pe carosabil', severity: 'critical' },
  very_high_speed: { label: 'Viteză foarte mare', severity: 'high' },
  stopped_emergency_lane: { label: 'Vehicul oprit pe banda de urgență', severity: 'high' },
  stopped_on_road: { label: 'Vehicul oprit pe carosabil', severity: 'high' },
  wrong_way: { label: 'Sens interzis', severity: 'critical' },
  pedestrian_highway: { label: 'Pieton pe autostradă', severity: 'critical' },
  probable_crash: { label: 'Accident probabil', severity: 'critical' },
  road_object: { label: 'Obiect pe carosabil', severity: 'critical' },
  object_on_roadway: { label: 'Obiect pe carosabil', severity: 'critical' },
  high_speed: { label: 'Viteză foarte mare', severity: 'high' },
  emergency_lane_stop: { label: 'Vehicul oprit pe banda de urgență', severity: 'high' },
  near_miss: { label: 'Aproape-accident', severity: 'high' },
  hard_braking: { label: 'Frânare bruscă', severity: 'medium' },
  tailgating: { label: 'Distanță prea mică', severity: 'medium' },
  dangerous_lane_change: { label: 'Schimbare de bandă periculoasă', severity: 'medium' },
  congestion: { label: 'Aglomerare', severity: 'info' },
  road_conditions: { label: 'Condiții de drum', severity: 'info' },
}

// Older data and other producers use a few alternative type names.
const ALERT_TYPE_ALIASES: Record<string, AlertType> = {
  excessive_speed: 'very_high_speed',
  pedestrian_on_highway: 'pedestrian_highway',
}

/** Event type labels; unknown types (new pipeline rules) get a readable fallback instead of crashing. */
export const ALERT_TYPE = new Proxy(ALERT_TYPE_KNOWN, {
  get(target, key: string) {
    return target[(ALERT_TYPE_ALIASES[key] ?? key) as AlertType]
      ?? { label: String(key).replace(/_/g, ' '), severity: 'info' as Severity }
  },
})

export const STATUS_LABEL: Record<AlertStatus, string> = {
  new: 'Nouă',
  in_review: 'În verificare',
  confirmed: 'Confirmată',
  rejected: 'Respinsă',
  closed: 'Închisă',
}

export const VLM_LABEL: Record<VlmVerdict, string> = {
  pending: 'În așteptare',
  skipped: 'Neverificat',
  confirmed: 'VLM: confirmat',
  rejected: 'VLM: infirmat',
  uncertain: 'VLM: incert',
}

export const ACTION_LABEL: Record<ActionType, string> = {
  dispatch_patrol: 'Patrulă trimisă',
  warning_sign: 'Panou de avertizare activat',
  enforcement: 'Transmis către procedura de constatare',
}

export const CAMERA_STATUS_LABEL: Record<CameraStatus, string> = {
  online: 'Online',
  offline: 'Offline',
  degraded: 'Semnal degradat',
}

export const PATROL_STATUS_LABEL: Record<PatrolStatus, string> = {
  available: 'Disponibilă',
  en_route: 'În deplasare',
  on_scene: 'La fața locului',
  off_duty: 'În afara serviciului',
}

export const ZONE_KIND_LABEL: Record<ZoneKind, string> = {
  emergency_lane: 'Bandă de urgență',
  crosswalk: 'Trecere de pietoni',
  one_way: 'Sens unic',
  highway: 'Autostradă',
  roadway: 'Carosabil',
  intersection: 'Intersecție',
}

export const ROLE_LABEL: Record<Role, string> = {
  admin: 'Administrator',
  operator: 'Operator dispecerat',
  anchetator: 'Anchetator',
  patrula: 'Agent patrulă',
  auditor: 'Auditor',
}

export const AUDIT_ACTION_LABEL: Record<AuditAction, string> = {
  detected: 'Detectat', viewed: 'Vizualizat', confirmed: 'Confirmat', rejected: 'Respins',
  vlm_confirmed: 'Verificare confirmată', vlm_rejected: 'Verificare respinsă', vlm_uncertain: 'Verificare incertă',
  login: 'Autentificare',
  logout: 'Deconectare',
  login_failed: 'Autentificare eșuată',
  view_alert: 'A vizualizat alerta',
  confirm_alert: 'A confirmat alerta',
  reject_alert: 'A respins alerta',
  dispatch_patrol: 'A trimis patrulă',
  warning_sign: 'A activat panou de avertizare',
  enforcement: 'A transmis către constatare',
  close_alert: 'A închis dosarul',
  archive_search: 'Căutare în arhivă',
  rule_update: 'A modificat o regulă',
  rule_toggle: 'A activat/dezactivat o regulă',
  export: 'Export date',
  reset_demo: 'Resetare date demo',
}
