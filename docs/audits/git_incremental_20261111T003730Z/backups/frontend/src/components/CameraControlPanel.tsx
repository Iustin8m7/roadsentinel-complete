import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Lock, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  activate, ageLabel, ATTESTATION_LABEL, cameraAction, createDraft, diffVersion, frozenLabel, getControl, getVersion,
  healthHistory, listVersions, LIFECYCLE_LABEL, metric, SOURCE_LABEL, STATE_LABEL, stateTone, validateDraft, VERSION_LABEL,
  versionAction,
  type CameraAction, type Change, type ConfigError, type ControlDetail, type HealthEvent, type Version, type VersionAction,
} from '@/lib/cameraControl'
import { Button } from '@/components/ui'
import { useModalFocus } from '@/hooks'

const TONE: Record<string, string> = {
  live: 'bg-rose-500/20 text-rose-300 border-rose-500/50',
  info: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
  muted: 'bg-elevation text-text-secondary border-border',
  bad: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
}

export function StateBadge({ state, label }: { state: string; label?: string }) {
  return (
    <span data-testid="runtime-state" data-state={state}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono font-semibold ${TONE[stateTone(state)]}`}>
      {label ?? STATE_LABEL[state] ?? state}
    </span>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border border-border rounded-md bg-panel p-3 flex flex-col gap-2">
      <h3 className="text-[11px] font-mono uppercase tracking-wider text-text-secondary">{title}</h3>
      {children}
    </section>
  )
}

const Row = ({ k, v, testId }: { k: string; v: ReactNode; testId?: string }) => (
  <div className="flex justify-between gap-3 text-xs"><span className="text-text-secondary">{k}</span>
    <span className="text-text-primary font-mono text-right break-all" data-testid={testId}>{v}</span></div>
)
const fmt = (iso: string | null) => iso ? new Date(iso).toLocaleString('ro-RO') : '—'
const TEMPLATE = {
  schema_version: 1, reference_frame: { width: 1920, height: 1080, coordinate_convention: 'pixels_top_left' },
  calibration: null, min_y: null, zones: [], rules: [], thresholds: {},
  acquisition: { target_fps: 25, reconnect_backoff_s: 2, read_timeout_s: 10, max_reconnect_attempts: 100 },
  model: { id: 'stock-yolox-s' },
}

/** Camera control plane detail: truthful runtime state, revisions, authorization, versions.
 *  Mutation controls are rendered only for administrators; the server enforces them anyway. */
export function CameraControlPanel({ cameraId, isAdmin, onClose }: { cameraId: string; isAdmin: boolean; onClose: () => void }) {
  const [detail, setDetail] = useState<ControlDetail | null>(null)
  const [versions, setVersions] = useState<Version[]>([])
  const [history, setHistory] = useState<HealthEvent[]>([])
  const [loadError, setLoadError] = useState<{ status: number; message: string } | null>(null)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'warn' | 'bad'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [reason, setReason] = useState('')
  const [confirmDisable, setConfirmDisable] = useState(false)
  const [diff, setDiff] = useState<{ revision: number; from: number | null; changes: Change[] } | null>(null)
  const [draft, setDraft] = useState<string | null>(null)
  const [draftErrors, setDraftErrors] = useState<ConfigError[] | null>(null)
  const panelRef = useRef<HTMLElement>(null)
  // An open draft holds unsaved work: only its own "Renunță" or the X button may discard it.
  const dismiss = () => { if (draft === null) onClose() }
  useModalFocus(panelRef, dismiss)

  const load = useCallback(async () => {
    try {
      const [d, v, h] = await Promise.all([getControl(cameraId), listVersions(cameraId), healthHistory(cameraId)])
      setDetail(d); setVersions(v); setHistory(h); setLoadError(null)
    } catch (error) {
      setLoadError({ status: error instanceof ApiError ? error.status : 0, message: (error as Error).message })
    }
  }, [cameraId])
  useEffect(() => {
    void load()
    const timer = window.setInterval(() => { void load() }, 10_000)
    return () => window.clearInterval(timer)
  }, [load])

  async function run(label: string, action: () => Promise<unknown>): Promise<boolean> {
    setBusy(true); setNotice(null)
    let ok = false
    try {
      await action()
      ok = true
      setNotice({ tone: 'ok', text: `${label}: efectuat.` })
    } catch (error) {
      const e = error instanceof ApiError ? error : null
      if (e?.status === 409 && e.code === 'revision_conflict') {
        setNotice({ tone: 'warn', text: 'Conflict: camera a fost modificată între timp de alt administrator. Datele au fost reîncărcate; verificați și reîncercați.' })
      } else if (e?.status === 409 && e.code === 'camera_not_managed') {
        setNotice({ tone: 'warn', text: 'Camera nu este adoptată în planul de control, deci nu poate fi dezactivată de aici.' })
      } else if (e?.status === 403) {
        setNotice({ tone: 'bad', text: `Refuzat de server: ${e.message}` })
      } else {
        const unmet = (e?.detail as { unmet?: { message: string }[] } | undefined)?.unmet
        setNotice({ tone: 'bad', text: `${label}: ${(error as Error).message}${unmet?.length ? ` (${unmet.map((u) => u.message).join('; ')})` : ''}` })
      }
    } finally {
      setBusy(false)
      await load()
    }
    return ok
  }
  const camAct = (action: CameraAction, label: string) => run(label, () => cameraAction(cameraId, action, detail!.revision, reason))
  const verAct = (v: Version, action: VersionAction, label: string) => run(label, () => versionAction(cameraId, v.id, action, reason))

  async function openDraft() {
    try {
      let base: unknown = TEMPLATE
      if (detail?.active_version_id) base = (await getVersion(cameraId, detail.active_version_id)).config
      setDraft(JSON.stringify(base, null, 2)); setDraftErrors(null)
    } catch (error) {
      setNotice({ tone: 'bad', text: `Ciornă nouă: ${(error as Error).message}` })
    }
  }
  function parsedDraft() {
    try { return JSON.parse(draft ?? '') as unknown } catch { setDraftErrors([{ path: '', code: 'invalid_json', message: 'JSON invalid' }]); return undefined }
  }

  const rt = detail?.runtime
  // Same minimum as the server's reason field. Only actions that really send the reason need it.
  const blocked = busy || reason.trim().length < 3
  const managed = detail?.lifecycle_state !== 'legacy' && detail?.lifecycle_state !== 'discovered'
  const canDisable = detail?.lifecycle_state !== 'disabled' && detail?.lifecycle_state !== 'legacy'
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end" onClick={dismiss}>
      <aside ref={panelRef} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Control cameră"
        className="w-full max-w-2xl h-full overflow-y-auto bg-deep-void border-l border-border p-4 flex flex-col gap-3 outline-none"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-heading text-xl font-bold text-text-primary">{detail?.name ?? 'Control cameră'}</h2>
            {detail && <p className="text-xs font-mono text-text-secondary">id stabil: {detail.slug} · revizie cameră {detail.revision}</p>}
          </div>
          <div className="flex items-center gap-1">
            <button type="button" onClick={() => void load()} className="p-1.5 rounded hover:bg-elevation" aria-label="Reîncarcă"><RefreshCw className="w-4 h-4" /></button>
            <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-elevation" aria-label="Închide"><X className="w-5 h-5" /></button>
          </div>
        </div>

        {!detail && !loadError && <div className="animate-pulse h-40 rounded bg-elevation" aria-label="Se încarcă" />}
        {loadError && (
          <div role="alert" className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">
            {loadError.status === 403 ? 'Acces interzis: rolul dumneavoastră nu poate vedea starea camerelor.'
              : loadError.status === 404 ? 'Camera nu există.' : `Nu s-au putut încărca datele: ${loadError.message}`}
          </div>
        )}
        {notice && (
          <div role="status" data-testid="control-notice" className={`rounded border p-2 text-xs ${notice.tone === 'ok' ? 'border-emerald-500/40 text-emerald-300' : notice.tone === 'warn' ? 'border-amber-500/40 text-amber-300' : 'border-rose-500/40 text-rose-300'}`}>{notice.text}</div>
        )}

        {detail && rt && (
          <>
            <div className="flex flex-wrap gap-1.5">
              <StateBadge state={rt.state} />
              <span data-testid="source-kind" className="px-2 py-0.5 rounded border border-border text-[10px] font-mono text-text-primary">
                {detail.source_kind ? SOURCE_LABEL[detail.source_kind] : 'Sursă nedeclarată'}
              </span>
              <span data-testid="lifecycle" className="px-2 py-0.5 rounded border border-border text-[10px] font-mono text-text-secondary">{LIFECYCLE_LABEL[detail.lifecycle_state]}</span>
              {!isAdmin && <span className="px-2 py-0.5 rounded border border-border text-[10px] font-mono text-text-secondary inline-flex items-center gap-1"><Lock className="w-3 h-3" />Doar citire</span>}
            </div>

            <Section title="Stare de rulare (calculată pe server)">
              <Row k="Ultimul semnal worker" v={`${ageLabel(rt.heartbeat_age_s)} (învechit după ${rt.stale_after_s} s)`} testId="heartbeat-age" />
              <Row k="Revizie dorită" v={rt.desired_revision ?? '—'} testId="desired-revision" />
              <Row k="Revizie aplicată de worker" v={rt.applied_revision ?? '—'} testId="applied-revision" />
              <Row k="Sincronizat" v={rt.revision_in_sync ? 'da' : 'nu'} />
              {rt.blocked_reason && <Row k="Motiv blocare" v={rt.blocked_reason} />}
              {detail.disabled_reason && <Row k="Motiv dezactivare" v={detail.disabled_reason} />}
              {rt.duplicate_worker && <p className="text-xs text-amber-300 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" />Două workere au raportat aceeași cameră; doar deținătorul lease-ului procesează.</p>}
              {rt.reference_frame_mismatch && <p className="text-xs text-amber-300">Rezoluția sursei diferă de cadrul de referință al configurației: coordonatele/calibrarea pot fi invalide.</p>}
              {detail.worker && (
                <>
                  <Row k="Worker (epocă)" v={detail.worker.lease_epoch ?? '—'} />
                  <Row k="FPS sursă / procesare" v={`${detail.worker.source_fps ?? '—'} / ${detail.worker.processing_fps ?? '—'}`} />
                  <Row k="Ultimul cadru" v={fmt(detail.worker.last_frame_at)} />
                  <Row k="Model" v={detail.worker.model_id ?? '—'} />
                  <Row k="Ultima confirmare" v={detail.worker.last_ack_status ? `${detail.worker.last_ack_status} r${detail.worker.last_ack_revision}${detail.worker.last_ack_reason ? ` (${detail.worker.last_ack_reason})` : ''}` : '—'} />
                  {detail.worker.last_error && <Row k="Ultima eroare" v={detail.worker.last_error} />}
                </>
              )}
              <Row k="Sursă (afișare)" v={detail.source_display ?? '—'} />
              <Row k="Atestare sursă (amprentă, fără URL)" v={<span className={rt.source_attestation === 'mismatch' ? 'text-amber-300' : undefined}>{ATTESTATION_LABEL[rt.source_attestation]}</span>} testId="source-attestation" />
            </Section>

            {detail.worker && (
              <Section title="Metrici worker (măsurate de worker)">
                <p data-testid="metrics-freshness" className={`text-[11px] ${rt.freshness === 'fresh' ? 'text-text-secondary' : 'text-amber-300'}`}>
                  {rt.freshness === 'fresh'
                    ? `Trimise cu ultimul semnal (${ageLabel(rt.heartbeat_age_s)}).`
                    : `Învechite: ultimul semnal ${ageLabel(rt.heartbeat_age_s)}; valorile nu mai descriu starea curentă.`}
                </p>
                <div role="group" aria-label="Metrici worker" className="flex flex-col gap-2">
                  <Row k="FPS procesare end-to-end (toată bucla, nu rata modelului)" v={metric(detail.worker.processing_fps, 'cadre/s', 1)} testId="metric-processing-fps" />
                  <Row k="Latență model.track p50 / p95" v={`${metric(detail.worker.inference_p50_ms, 'ms')} / ${metric(detail.worker.inference_p95_ms, 'ms')}`} testId="metric-latency" />
                  <Row k="Memorie proces (RSS)" v={metric(detail.worker.rss_mb, 'MB')} testId="metric-rss" />
                  <Row k="Cadre pierdute (sursă live)" v={metric(detail.worker.dropped_frames, '')} testId="metric-dropped" />
                  <Row k="Evenimente în coadă de trimitere" v={metric(detail.worker.queue_depth, '')} testId="metric-queue" />
                  <Row k="Reconectări" v={metric(detail.worker.retries, '')} testId="metric-retries" />
                  <Row k="Ultimul cod de eroare" v={detail.worker.last_error_code ?? '—'} testId="metric-error-code" />
                  <Row k="Imagine înghețată" v={frozenLabel(detail.worker.health, detail.worker)} testId="metric-frozen" />
                </div>
              </Section>
            )}

            <Section title="Autorizare de procesare">
              {detail.eligibility.eligible
                ? <p className="text-xs text-emerald-300 flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5" />Toate cerințele sunt îndeplinite.</p>
                : <ul data-testid="unmet" className="text-xs text-amber-300 list-disc pl-4">{detail.eligibility.unmet.map((u) => <li key={u.code}>{u.message} <span className="font-mono text-text-secondary">[{u.code}]</span></li>)}</ul>}
              {detail.grants.length === 0 && <p className="text-xs text-text-secondary">Nicio autorizare înregistrată. Un link către o pagină publică nu este o autorizare.</p>}
              {detail.grants.map((g) => (
                <div key={g.id} className="text-xs border-t border-border/60 pt-1">
                  <span className={g.status === 'active' ? 'text-emerald-300' : 'text-rose-300'}>{g.status === 'active' ? 'Activă' : 'Revocată'}</span>
                  {' · '}{g.granting_party} · {g.basis_reference} · {SOURCE_LABEL[g.capture_method]} · valabilă {fmt(g.valid_from)} – {fmt(g.valid_until)} · max {g.max_analysis_fps} fps / {g.max_frame_height}p
                </div>
              ))}
            </Section>

            {isAdmin && (
              <Section title="Acțiuni administrator (verificate pe server)">
                <label className="text-xs text-text-secondary flex flex-col gap-1">Motiv (intră în jurnalul de audit)
                  <input data-testid="control-reason" required value={reason} onChange={(e) => setReason(e.target.value)} className="bg-elevation border border-border rounded px-2 py-1 text-text-primary" />
                  {reason.trim().length < 3 && <span className="text-[11px]">Completați motivul (minimum 3 caractere) pentru a activa acțiunile.</span>}
                </label>
                <div className="flex flex-wrap gap-2">
                  {detail.lifecycle_state === 'approved' && detail.desired_enabled && <Button size="sm" variant="secondary" disabled={blocked} onClick={() => void camAct('pause', 'Pauză')}>Pauză</Button>}
                  {detail.lifecycle_state === 'approved' && !detail.desired_enabled && <Button size="sm" variant="secondary" disabled={blocked} onClick={() => void camAct('resume', 'Reluare')}>Reia</Button>}
                  {canDisable && <Button size="sm" variant="danger" disabled={blocked} onClick={() => setConfirmDisable(true)}>Dezactivează</Button>}
                  {detail.lifecycle_state === 'disabled' && !detail.enable_requested_by && <Button size="sm" variant="secondary" disabled={blocked} onClick={() => void camAct('enable-request', 'Cerere reactivare')}>Cere reactivarea</Button>}
                  {detail.lifecycle_state === 'disabled' && detail.enable_requested_by && <Button size="sm" disabled={blocked} onClick={() => void camAct('enable', 'Confirmare reactivare')}>Confirmă reactivarea (alt administrator)</Button>}
                  {Object.entries(detail.unsupported_actions).map(([key, why]) => (
                    <Button key={key} size="sm" variant="secondary" disabled title={why} aria-label={`Repornire indisponibilă: ${why}`}>Repornire (indisponibil)</Button>
                  ))}
                  {managed && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void openDraft()}>Ciornă nouă de configurație</Button>}
                </div>
                {confirmDisable && canDisable && (
                  <div role="group" aria-label="Confirmare dezactivare" data-testid="confirm-disable" className="rounded border border-rose-500/40 bg-rose-500/10 p-2 text-xs text-rose-200 flex flex-col gap-2">
                    <p>Dezactivarea oprește procesarea acestei camere. Reactivarea cere confirmarea unui al doilea administrator. Continuați?</p>
                    <div className="flex gap-2">
                      <Button size="sm" variant="danger" disabled={blocked} onClick={() => { setConfirmDisable(false); void camAct('disable', 'Dezactivare') }}>Da, dezactivează</Button>
                      <Button size="sm" variant="ghost" onClick={() => setConfirmDisable(false)}>Anulează</Button>
                    </div>
                  </div>
                )}
                {!managed && <p data-testid="adoption-note" className="text-[11px] text-text-secondary">Adoptarea camerei în planul de control se face momentan prin API.</p>}
                {Object.values(detail.unsupported_actions).map((why) => <p key={why} className="text-[11px] text-text-secondary">{why}</p>)}
              </Section>
            )}

            {isAdmin && draft !== null && (
              <Section title="Ciornă (schema v1, fără cale video sau secrete)">
                <textarea aria-label="Configurație JSON" value={draft} onChange={(e) => setDraft(e.target.value)} rows={12}
                  className="font-mono text-[11px] bg-elevation border border-border rounded p-2 text-text-primary" />
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" disabled={busy} onClick={() => { const c = parsedDraft(); if (c !== undefined) void validateDraft(cameraId, c).then((r) => setDraftErrors(r.errors)).catch((e: Error) => setNotice({ tone: 'bad', text: e.message })) }}>Verifică (fără salvare)</Button>
                  <Button size="sm" disabled={blocked} onClick={() => { const c = parsedDraft(); if (c !== undefined) void run('Ciornă salvată', () => createDraft(cameraId, c, reason)).then((ok) => { if (ok) setDraft(null) }) }}>Salvează ca ciornă</Button>
                  <Button size="sm" variant="ghost" onClick={() => setDraft(null)}>Renunță</Button>
                </div>
                {draftErrors && (draftErrors.length === 0
                  ? <p className="text-xs text-emerald-300 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Configurația este validă.</p>
                  : <ul className="text-xs text-amber-300 list-disc pl-4">{draftErrors.map((e, i) => <li key={i}><span className="font-mono">{e.path || '(rădăcină)'}</span>: {e.message} [{e.code}]</li>)}</ul>)}
              </Section>
            )}

            <Section title="Versiuni de configurație (imuabile)">
              {versions.length === 0 && <p className="text-xs text-text-secondary">Nicio versiune încă.</p>}
              {versions.map((v) => (
                <div key={v.id} data-testid={`version-${v.revision}`} className="border-t border-border/60 pt-1.5 flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono text-accent">r{v.revision}</span>
                    <span data-testid="version-status" className="px-1.5 rounded border border-border font-mono text-[10px]">{VERSION_LABEL[v.status]}</span>
                    <span className="font-mono text-text-secondary" title={v.fingerprint}>{v.fingerprint.slice(0, 12)}…</span>
                    <span className="text-text-secondary">{fmt(v.created_at)}</span>
                    <span className="text-text-secondary truncate">{v.reason}</span>
                  </div>
                  {v.validation_errors.length > 0 && <p className="text-[11px] text-amber-300">{v.validation_errors.length} erori de validare (ex.: {v.validation_errors[0].path}: {v.validation_errors[0].message})</p>}
                  <div className="flex flex-wrap gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => void diffVersion(cameraId, v.id).then((d) => setDiff({ revision: v.revision, from: d.from_revision, changes: d.changes })).catch((e: Error) => setNotice({ tone: 'bad', text: `Diferențe: ${e.message}` }))}>Diferențe față de activă</Button>
                    {isAdmin && v.status === 'draft' && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void verAct(v, 'validate', 'Validare')}>Validează</Button>}
                    {isAdmin && v.status === 'validated' && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void verAct(v, 'submit', 'Trimis spre aprobare')}>Trimite spre aprobare</Button>}
                    {isAdmin && v.status === 'awaiting_approval' && <>
                      <Button size="sm" variant="confirm" disabled={blocked} onClick={() => void verAct(v, 'approve', 'Aprobare')}>Aprobă (alt administrator)</Button>
                      <Button size="sm" variant="reject" disabled={blocked} onClick={() => void verAct(v, 'reject', 'Respingere')}>Respinge</Button>
                    </>}
                    {isAdmin && v.status === 'approved' && <Button size="sm" disabled={blocked} onClick={() => void run('Activare', () => activate(cameraId, v.id, detail.revision, reason))}>Activează</Button>}
                    {isAdmin && v.status === 'superseded' && <Button size="sm" variant="secondary" disabled={blocked} onClick={() => void run('Revenire', () => activate(cameraId, v.id, detail.revision, reason, true))}>Revino la această versiune</Button>}
                  </div>
                </div>
              ))}
              {diff && (
                <div className="text-[11px] font-mono bg-elevation rounded p-2">
                  <div className="text-text-secondary mb-1">r{diff.revision} față de {diff.from ? `r${diff.from}` : 'nimic activ'}:</div>
                  {diff.changes.length === 0 ? 'Fără diferențe.' : diff.changes.map((c) => (
                    <div key={c.path}>{c.op === 'added' ? '+' : c.op === 'removed' ? '−' : '~'} {c.path}: {JSON.stringify(c.before)} → {JSON.stringify(c.after)}</div>
                  ))}
                </div>
              )}
            </Section>

            <Section title="Istoric stare (ultimele evenimente)">
              {history.length === 0 && <p className="text-xs text-text-secondary">Niciun eveniment.</p>}
              {history.map((h, i) => (
                <div key={i} className="text-[11px] font-mono text-text-secondary">
                  {fmt(h.at)} · {h.kind}{h.health ? ` · ${h.health}` : ''}{h.revision ? ` · r${h.revision}` : ''}{h.reason_code ? ` · ${h.reason_code}` : ''}{h.message ? ` · ${h.message}` : ''}
                </div>
              ))}
            </Section>
          </>
        )}
      </aside>
    </div>
  )
}
