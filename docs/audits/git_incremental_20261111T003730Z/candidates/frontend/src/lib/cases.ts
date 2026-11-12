// Investigation workspace API (backend app/api/investigation.py). Real API only: in
// VITE_USE_MOCKS=1 demo mode these calls are not made and the UI says so.
import { api, ApiError, apiUrl } from './api'
import type { ApiAudit, ApiEvent } from './adapters'
import { HIDDEN_IDS } from './demo'
import { HIDDEN_TYPES } from '@/store/data'

export type StorageState = 'available' | 'missing' | 'purged' | 'unavailable'

export interface EvidenceItem {
  id: string; kind: string; content_type: string; redaction: string; redaction_label: string
  original_exists: boolean; size_bytes: number; sha256_recorded: boolean
  storage_state: StorageState; purged_at: string | null; duration_s: number | null; media_url: string | null
}
export interface CaseNote {
  id: string; kind: 'observation' | 'interpretation'; author: string; author_is_me: boolean
  created_at: string; updated_at: string; revision: number; body: string; tags: string[]
  evidence_id: string | null; offset_s: number | null; track_id: number | null; bbox?: number[] | null
  retracted_at: string | null; retracted_by: string | null; retract_reason: string | null
  can_revise: boolean; can_retract: boolean
}
export interface NoteRevision { revision: number; author: string; created_at: string; body: string; tags: string[] }
export interface Bookmark { id: string; evidence_id: string; offset_s: number; label: string; author: string; created_at: string; can_remove: boolean }
export interface CaseDossier {
  number: number; status: string; priority: string; type: string; type_label: string
  camera_id: string; camera_name: string; location: string; timezone: string
  observed_at: string; observed_at_local: string; first_observed_at: string; last_observed_at: string | null
  observation_note: string; video_t_s: number | null; track_id: number | null; object_class: string | null; rule: string
  provenance: {
    source_kind: 'live' | 'recorded_replay' | 'unknown'; source_basis: string
    model_id: string | null; model_hash: string | null; model_status: 'recorded' | 'not_recorded'
    speed_kmh: number | null; speed_status: 'uncalibrated_estimate' | 'not_applicable'
    recorded_details: Record<string, unknown>
  }
  evidence: EvidenceItem[]
  decision: { status: string; action: string | null; action_label: string | null; note: string | null; decided_by: string | null; decided_at: string | null; external_effect: string }
  notes: CaseNote[]; bookmarks: Bookmark[]; history: ApiAudit[]
  permissions: { can_decide: boolean; can_annotate: boolean; can_request_export: boolean; can_approve_export: boolean }
  tag_catalog: Record<string, string>
  related?: RelatedCase[]; context?: TimelineContext | null; followups?: Followup[]
  legal_hold?: LegalHoldState | null; detection_ref?: DetectionRef | null
}
export interface RelationReason {
  kind: 'link' | 'same_track' | 'same_camera_window'; label: string; link_id: string | null; reason: string | null
  created_by: string | null; created_at: string | null; can_remove: boolean
}
export interface RelatedCase { number: number; type: string; type_label: string; status: string; priority: string; observed_at: string; camera_id: string; reasons: RelationReason[] }
export interface ContextEvent { number: number; type: string; type_label: string; status: string; observed_at: string; delta_s: number }
export interface TimelineContext { window_s: number; limit_per_side: number; before: ContextEvent[]; after: ContextEvent[]; truncated_before: boolean; truncated_after: boolean; note: string }
export type FollowupStatus = 'open' | 'done' | 'cancelled'
export interface FollowupEvent { revision: number; change: string; status: FollowupStatus; assignee: string | null; due_date: string | null; actor: string; at: string }
export interface Followup {
  id: string; body: string; status: FollowupStatus; author: string; author_is_me: boolean
  assignee_id: string | null; assignee: string | null; assignee_is_me: boolean; due_date: string | null; overdue: boolean
  created_at: string; updated_at: string; revision: number; can_change_status: boolean; can_reassign: boolean; history: FollowupEvent[]
}
export interface Person { id: string; name: string; role: string; is_me: boolean }
export interface LegalHold { id: string; active: boolean; reason: string; placed_by: string; placed_at: string; released_at: string | null; released_by: string | null; release_reason: string | null }
export interface LegalHoldState { active: LegalHold | null; history: LegalHold[]; can_manage: boolean; effect: string }
export interface DetectionRef { track_id: number | null; bbox: number[] | null; bbox_status: 'recorded' | 'not_recorded' | 'malformed'; video_t_s: number | null; run_id: string | null; note: string }
export interface PackageVerifyResult {
  ok: boolean; manifest_sha256: string | null; expected_manifest_sha256: string | null; files_checked: number; errors: string[]
  size_bytes: number; server_record: { export_id: string; event_id: number; state: string } | null; note: string
}
export type IntegrityState = 'match' | 'mismatch' | 'missing' | 'purged' | 'unavailable' | 'unreadable' | 'no_hash' | 'not_checked'
export interface IntegrityItem {
  id: string; kind: string; event_id: number | null; camera_id: string | null; created_at: string; size_bytes: number
  sha256_recorded: boolean; distinct_original: boolean; storage_state: StorageState; integrity: IntegrityState
}
export interface IntegrityPage { items: IntegrityItem[]; next_cursor: string | null; total: number; verified: boolean; note: string }
export interface AuditVerify { ok: boolean; checked: number; first_broken_seq: number | null; reason: string | null; head_hash: string | null }
export interface ExportJob {
  id: string; event_id: number; state: 'pending_approval' | 'queued' | 'processing' | 'completed' | 'failed' | 'denied' | 'canceled' | 'expired'
  include_original: boolean; requester: string; requested_by_me: boolean; created_at: string
  approval_id: string | null; approval_status: string | null; approved_by: string | null; attempt: number; error: string | null
  completed_at: string | null; expires_at: string | null; manifest_sha256: string | null; package_sha256: string | null
  package_size: number | null; file_count: number | null; signature: 'none'; legal_hold?: boolean; storage_retries?: number
}
export interface TokenInterpretation { token: string; status: 'recognized' | 'ignored' | 'unsupported'; meanings: string[]; ambiguous: boolean }
export interface ArchiveFilters {
  camera_id?: string; types?: string[]; statuses?: string[]; priorities?: string[]
  date_from?: string; date_to?: string; has_evidence?: boolean
  assigned_to?: string; evidence_types?: ('keyframe' | 'clip' | 'camera_video')[]
}
export interface FilterChip { key: string; label: string }
export interface ArchivePage { results: ApiEvent[]; next_cursor: string | null; total: number; sort: string; filter: Record<string, unknown>; interpretation: TokenInterpretation[]; applied_filters?: FilterChip[] }
export interface SavedSearch { id: string; name: string; filters: ArchiveFilters; created_at: string }

const enc = encodeURIComponent
const send = <T>(path: string, method: string, body?: unknown) =>
  api<T>(path, { method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })

export const getCase = (n: string) => api<CaseDossier>(`/api/events/${enc(n)}/case`)
export const addNote = (n: string, body: { kind: CaseNote['kind']; body: string; tags: string[]; evidence_id?: string; offset_s?: number; track_id?: number; bbox?: number[] }) =>
  send<CaseNote>(`/api/events/${enc(n)}/notes`, 'POST', body)
export const reviseNote = (n: string, id: string, body: { body: string; tags: string[] }) =>
  send<CaseNote>(`/api/events/${enc(n)}/notes/${enc(id)}/revisions`, 'POST', body)
export const retractNote = (n: string, id: string, reason: string) =>
  send<CaseNote>(`/api/events/${enc(n)}/notes/${enc(id)}/retract`, 'POST', { reason })
export const noteHistory = (n: string, id: string) => api<NoteRevision[]>(`/api/events/${enc(n)}/notes/${enc(id)}/revisions`)
export const addBookmark = (n: string, body: { evidence_id: string; offset_s: number; label: string }) =>
  send<Bookmark>(`/api/events/${enc(n)}/bookmarks`, 'POST', body)
export const removeBookmark = (n: string, id: string) => send<void>(`/api/events/${enc(n)}/bookmarks/${enc(id)}`, 'DELETE')

export const addLink = (n: string, number: number, reason: string) => send<RelatedCase[]>(`/api/events/${enc(n)}/links`, 'POST', { number, reason })
export const removeLink = (n: string, id: string) => send<void>(`/api/events/${enc(n)}/links/${enc(id)}`, 'DELETE')
export const addFollowup = (n: string, body: { body: string; assignee_id?: string; due_date?: string }) =>
  send<Followup>(`/api/events/${enc(n)}/followups`, 'POST', body)
export const updateFollowup = (n: string, id: string, body: { revision: number; status?: FollowupStatus; assignee_id?: string | null; due_date?: string | null }) =>
  send<Followup>(`/api/events/${enc(n)}/followups/${enc(id)}`, 'PATCH', body)
export const followupAssignees = (n: string) => api<Person[]>(`/api/events/${enc(n)}/followup-assignees`)
export const placeHold = (n: string, reason: string) => send<LegalHoldState>(`/api/events/${enc(n)}/legal-hold`, 'POST', { reason })
export const releaseHold = (n: string, reason: string) => send<LegalHoldState>(`/api/events/${enc(n)}/legal-hold/release`, 'POST', { reason })
export const archiveAssignees = () => api<Person[]>('/api/archive/assignees')
export const auditVerify = () => api<AuditVerify>('/api/audit/verify')
export const evidenceIntegrity = (verify: boolean, cursor?: string | null) =>
  api<IntegrityPage>(`/api/audit/evidence?${new URLSearchParams({ limit: verify ? '20' : '25', verify: String(verify), ...(cursor ? { cursor } : {}) })}`)
/** The file is sent as the raw request body (streamed by the browser), never stored by the server. */
export const verifyPackage = (file: Blob, expectedSha256?: string) =>
  api<PackageVerifyResult>(`/api/exports/verify${expectedSha256 ? `?manifest_sha256=${enc(expectedSha256)}` : ''}`, {
    method: 'POST', body: file, headers: { 'Content-Type': 'application/zip' },
  })
// The web gateway refuses request bodies over 64 MB; larger packages are verified with the CLI.
export const MAX_VERIFY_BYTES = 60 * 1024 * 1024

const VERIFY_ERRORS: [string, string][] = [
  ['sha256 mismatch: ', 'Conținut modificat (amprenta nu corespunde): '],
  ['size mismatch: ', 'Dimensiune diferită față de manifest: '],
  ['listed file missing: ', 'Fișier din manifest care lipsește din pachet: '],
  ['file not listed in manifest: ', 'Fișier care nu apare în manifest: '],
  ['file listed more than once: ', 'Fișier trecut de mai multe ori în manifest: '],
  ['unsafe entry name: ', 'Nume de fișier nepermis: '],
  ['not a readable zip file', 'Fișierul nu este o arhivă ZIP care poate fi citită.'],
  ['unreadable zip content', 'Conținutul arhivei nu poate fi citit (date corupte sau arhivă protejată).'],
  ['manifest digest differs', 'Amprenta manifestului diferă de cea oficială introdusă.'],
  ['manifest.json missing', 'Pachetul nu conține manifestul (manifest.json).'],
  ['manifest.json is not', 'Manifestul nu are forma așteptată.'],
  ['manifest has an invalid file path', 'Manifestul conține o cale de fișier nevalidă.'],
  ['manifest lists no files', 'Manifestul nu enumeră niciun fișier.'],
  ['unknown manifest schema', 'Manifestul are un format necunoscut.'],
  ['duplicate entry names', 'Arhiva conține două fișiere cu același nume.'],
  ['too many entries', 'Arhiva conține prea multe fișiere.'],
  ['declared uncompressed size', 'Pachetul depășește dimensiunea maximă care poate fi verificată aici.'],
]
/** Romanian text for a verifier error; an unknown one is shown as received. */
export function verifyErrorRo(error: string): string {
  for (const [prefix, text] of VERIFY_ERRORS) {
    if (error.startsWith(prefix)) return text.endsWith(': ') ? text + error.slice(prefix.length) : text
  }
  return error
}

export const listExports = (n: string) => api<ExportJob[]>(`/api/events/${enc(n)}/exports`)
export const requestExport = (n: string, body: { justification: string; case_reference: string; include_original: boolean; idempotency_key: string }) =>
  send<ExportJob>(`/api/events/${enc(n)}/exports`, 'POST', body)
export const runExport = (id: string) => send<ExportJob>(`/api/exports/${enc(id)}/run`, 'POST', {})
export const cancelExport = (id: string) => send<ExportJob>(`/api/exports/${enc(id)}/cancel`, 'POST', {})
export const approveExport = (approvalId: string) => send<unknown>(`/api/approvals/${enc(approvalId)}/approve`, 'POST', {})
export const denyExport = (approvalId: string) => send<unknown>(`/api/approvals/${enc(approvalId)}/deny`, 'POST', {})
export const exportLink = (id: string) => send<{ url: string; expires_at: string }>(`/api/exports/${enc(id)}/link`, 'POST', {})

/** POST body, never a URL: the text may contain plates or names and URLs reach access logs. */
export const archiveBody = (q: string, filters: ArchiveFilters, cursor?: string | null, limit = 24) => ({
  ...(q.trim() ? { q: q.trim() } : {}), filters, ...(cursor ? { cursor } : {}), limit,
})
/** Same visibility as the queue. Added only to the search request, so saved filters never hold it. */
const HIDDEN_FROM_ARCHIVE = {
  exclude_types: [...HIDDEN_TYPES],
  exclude_numbers: [...HIDDEN_IDS].filter((id) => /^\d+$/.test(id)).map(Number),
}
export const searchArchive = (q: string, f: ArchiveFilters, cursor?: string | null) =>
  send<ArchivePage>('/api/archive/search', 'POST', archiveBody(q, { ...f, ...HIDDEN_FROM_ARCHIVE }, cursor))
export interface ArchiveRun { q: string; filters: ArchiveFilters }
/** The server binds a cursor to its query: appending must ignore edits made since the last run. */
export const archiveRequest = (append: boolean, edited: ArchiveRun, last: ArchiveRun | null, cursor: string | null) =>
  append && last ? { run: last, cursor } : { run: edited, cursor: null }
export const listSaved = () => api<SavedSearch[]>('/api/archive/saved')
export const saveSearch = (name: string, filters: ArchiveFilters) => send<SavedSearch>('/api/archive/saved', 'POST', { name, filters })
export const deleteSaved = (id: string) => send<void>(`/api/archive/saved/${enc(id)}`, 'DELETE')

/** Short-lived, user-bound package URL (POST /link) -> blob download, without exposing it in the DOM. */
export async function downloadPackage(job: ExportJob) {
  const { url } = await exportLink(job.id)
  const res = await fetch(apiUrl(url), { credentials: 'include' })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, typeof body.detail === 'string' ? body.detail : `Descărcarea a eșuat (${res.status}).`)
  }
  const blob = await res.blob()
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = `roadsentinel-caz-${job.event_id}-${job.id.slice(0, 8)}.zip`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 10_000)
  return blob
}

export const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'Eroare de conexiune.'
export const newIdempotencyKey = () => (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g, '')
export const fmtOffset = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(2).padStart(5, '0')}`
