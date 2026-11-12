export type Role = "system_admin" | "tenant_admin" | "operator" | "patrol" | "auditor";
export type Priority = "critical" | "high" | "medium" | "info";

export interface Me {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  tenant_id: string;
  tenant_name: string;
  permissions: string[];
  session_id: string;
  mfa_fresh_until: string;
}

export interface Alert {
  id: string;
  camera_id: string;
  camera_name: string | null;
  priority: Priority;
  status: "new" | "confirmed" | "rejected";
  event_type: string;
  description: string;
  detected_at: string;
  plate_masked: string | null;
  assigned_to: string | null;
  assigned_to_name?: string | null;
  patrol_status?: "assigned" | "en_route" | "on_scene" | "done" | null;
  patrol_status_at?: string | null;
  decided_by: string | null;
  decided_at: string | null;
  evidence_ids: string[];
}

export interface Evidence {
  id: string;
  alert_id: string;
  kind: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  /** full | heads_only | off | unknown, as reported by the pipeline. */
  redaction: string;
  /** false: one stored copy only, nothing to unblur or export. */
  has_original: boolean;
  unblur_grant_expires_at: string | null;
  plate: string | null;
}

export interface SignedUrl {
  url: string;
  expires_at: string;
}

export interface Approval {
  id: string;
  kind: "unblur" | "export" | "account_reset";
  resource_type: string;
  resource_id: string;
  requester_id: string;
  justification: string;
  case_reference: string;
  status: "pending" | "approved" | "denied" | "revoked";
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  grant_expires_at: string | null;
  grant_active: boolean;
  created_at: string;
}

export interface SessionInfo {
  id: string;
  user_id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  ip: string | null;
  user_agent: string | null;
  revoked_at: string | null;
  revoked_reason: string | null;
  current: boolean;
}

export interface AuditEntry {
  seq: number;
  ts: string;
  actor_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip: string | null;
  details: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
}

export interface AuditVerify {
  ok: boolean;
  checked: number;
  first_broken_seq: number | null;
  reason: string | null;
  head_hash: string | null;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  mfa_enabled: boolean;
}

export interface Patrol {
  id: string;
  display_name: string;
  open_assignments: number;
}

export interface RetentionState {
  days: Record<string, number>;
  defaults: Record<string, number>;
  due_now: number;
  held_skipped: number;
}

export interface PurgeResult {
  dry_run: boolean;
  candidates: number;
  purged: number;
  held_skipped: number;
  errors: number;
  by_kind: Record<string, number>;
}

export interface UserRow {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
}
