import { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useParams } from 'react-router'
import { ArrowLeft, Navigation, CheckCircle2, XCircle, AlertTriangle, Loader2, UserCheck } from 'lucide-react'
import { ApiError, USE_MOCKS } from '@/lib/api'
import { errorMessage, getCase, type CaseDossier } from '@/lib/cases'
import { BookmarksPanel, EvidencePanel, ExportPanel, HistoryPanel, NotesPanel } from '@/components/CaseWorkspace'
import { ContextStrip, FollowupsPanel, LegalHoldPanel, RelatedPanel } from '@/components/CasePanels'
import { useDataStore, decide, loadDetail, reportError, cameraById } from '@/store/data'
import { useCan } from '@/hooks'
import { useAuditStore } from '@/store/audit'
import { AUDIT_ACTION_LABEL } from '@/lib/constants'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusBadge } from '@/components/ui'
import { EvidencePlayer } from '@/components/EvidencePlayer'
import type { Alert } from '@/types'
import { NotFoundPage } from './ErrorPages'

export default function AlertDetailPage() {
  const { id = '' } = useParams()
  // The dashboard queue hides some ids (demo curation in lib/demo.ts); a case opened directly
  // is still shown exactly as the server returns it.
  const stored = useDataStore((s) => s.alerts.find((a) => a.id === id))
  const [direct, setDirect] = useState<Alert | null>(null)
  const alert = stored ?? (direct?.id === id ? direct : undefined)
  const rule = useDataStore((s) => s.rules.find((r) => r.id === alert?.ruleId))
  const { markViewed, startReview, confirmAlert, rejectAlert, addAction } = useDataStore.getState()
  const canDecide = useCan('alerts.decide')
  const canDispatch = useCan('alerts.dispatch')
  const auditEntries = useAuditStore((s) => s.entries)

  const [loadState, setLoadState] = useState<'loading' | 'done' | 'missing'>(USE_MOCKS ? 'done' : 'loading')
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectionNote, setRejectionNote] = useState('')
  const [dispatchSuccess, setDispatchSuccess] = useState(false)
  const [saving, setSaving] = useState(false)
  const [dossier, setDossier] = useState<CaseDossier | null>(null)
  const [dossierError, setDossierError] = useState<string | null>(null)
  const [conflict, setConflict] = useState<string | null>(null)
  const [seekRequest, setSeekRequest] = useState<{ t: number; n: number } | undefined>()
  const [pendingBookmark, setPendingBookmark] = useState<{ evidenceId: string; t: number } | null>(null)

  const reloadCase = useCallback(async () => {
    if (USE_MOCKS) return
    try {
      const [nextDossier, nextAlert] = await Promise.all([getCase(id), loadDetail(id)])
      setDossier(nextDossier); setDirect(nextAlert); setDossierError(null)
    }
    catch (err) {
      setDossierError(err instanceof ApiError && err.status === 403 ? 'Acces refuzat: rolul dumneavoastră nu poate vedea dosarul.' : errorMessage(err))
    }
  }, [id])

  const openedId = useRef<string | null>(null)
  useEffect(() => {
    if (!USE_MOCKS) {
      if (openedId.current === id) return // alert?.id changing must not re-audit the view
      openedId.current = id
      setLoadState('loading')
      setDossier(null)
      loadDetail(id, true)
        .then((loaded) => { setDirect(loaded); setLoadState('done'); return reloadCase() })
        .catch((err) => { setLoadState('missing'); reportError(err) })
      return
    }
    if (!alert) return
    markViewed(alert.id)
    if (canDecide) startReview(alert.id)
  }, [id, alert?.id])

  if (!alert) {
    if (loadState === 'loading') {
      return (
        <div className="h-full flex items-center justify-center gap-2 text-sm text-[#7D8A9B] bg-[#0A0E14]">
          <Loader2 size={18} className="animate-spin text-[#3DA5FF]" /> Se încarcă dosarul alertei…
        </div>
      )
    }
    return <NotFoundPage />
  }
  const cam = cameraById(alert.cameraId)
  const decided = alert.status === 'confirmed' || alert.status === 'rejected' || alert.status === 'closed'

  const run = async (fn: () => Promise<unknown> | unknown) => {
    setSaving(true)
    setConflict(null)
    try { await fn(); await reloadCase() }
    catch (err) {
      // Another operator decided first: the server refused ours (atomic decision).
      if (err instanceof ApiError && err.status === 409) { setConflict(err.message); setRejectModalOpen(false); await reloadCase() }
      else reportError(err)
    } finally { setSaving(false) }
  }
  const handleConfirm = () => run(() => USE_MOCKS ? confirmAlert(alert.id) : decide(id, 'confirm', 'monitor', 'Confirmat de dispecer după verificarea dovezilor'))
  const handleRejectSubmit = () => {
    if (!rejectionNote.trim()) return
    return run(async () => {
      if (USE_MOCKS) rejectAlert(alert.id, rejectionNote.trim())
      else await decide(id, 'reject', undefined, rejectionNote.trim())
      setRejectModalOpen(false)
    })
  }
  const handleDispatchPatrol = () => run(async () => {
    if (USE_MOCKS) addAction(alert.id, 'dispatch_patrol', { patrolId: 'IS-21-POL', note: 'Recomandare patrulă (demo)' })
    else await decide(id, 'confirm', 'dispatch_patrol', 'Confirmat; recomandare de patrulă înregistrată intern')
    setDispatchSuccess(true)
    setTimeout(() => setDispatchSuccess(false), 5000)
  })

  const eventAt = new Date(alert.createdAt).getTime()
  const hhmmss = (ms: number) => new Date(ms).toTimeString().slice(0, 8)

  // Event history from the real audit trail of this alert (most recent last).
  const history = auditEntries
    .filter((e) => e.target === alert.id)
    .sort((x, y) => x.at.localeCompare(y.at))
  const timeline = [
    { time: hhmmss(eventAt), label: 'Detecție automată' },
    ...history.map((e) => ({
      time: hhmmss(new Date(e.at).getTime()),
      label: `${AUDIT_ACTION_LABEL[e.action as keyof typeof AUDIT_ACTION_LABEL] ?? e.action}${e.username ? ` · ${e.username}` : ''}`,
    })),
  ].slice(-5)

  const clipEvidence = dossier?.evidence.find((e) => e.kind === 'clip')
  const clipBookmarks = (dossier?.bookmarks ?? []).filter((b) => b.evidence_id === clipEvidence?.id).map((b) => ({ id: b.id, t: b.offset_s, label: b.label }))
  const seek = (evidenceId: string, t: number) => { if (evidenceId === clipEvidence?.id) setSeekRequest({ t, n: Date.now() }) }
  const prov = dossier?.provenance
  const card = 'bg-[#111821] border border-[#1E2A36] rounded-md p-3.5'
  const cardTitle = "font-sans font-bold text-xs uppercase tracking-wider text-[#7D8A9B] mb-2"

  return (
    <div className="h-full flex flex-col p-4 gap-3 overflow-y-auto bg-[#0A0E14] text-[#E6EDF3]">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link to="/app" className="text-xs text-[#7D8A9B] hover:text-[#3DA5FF] flex items-center gap-1 shrink-0">
            <ArrowLeft size={13} /> Panou
          </Link>
          <span className="font-mono text-sm text-[#3DA5FF] shrink-0">#{alert.id}</span>
          {dossier?.legal_hold?.active && (
            <span className="px-1.5 py-0.5 rounded border border-[#FFC23D]/60 text-[#FFC23D] text-[10px] font-bold uppercase shrink-0" data-testid="legal-hold-badge">Reținere legală</span>
          )}
          <h1 className="font-sans text-xl xl:text-2xl font-bold uppercase tracking-wide truncate">
            {alert.ruleSummary || rule?.name || alert.type}
          </h1>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SeverityBadge severity={alert.severity} dualLabel />
          <StatusBadge status={alert.status} />
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3 shrink-0 min-h-[560px] md:h-[72vh]">
        {/* Evidence player */}
        <div className="col-span-12 md:col-span-8 min-h-0">
          <EvidencePlayer
            src={clipEvidence?.storage_state === 'available' || !dossier ? alert.clip?.src : undefined}
            poster={alert.keyframeUrl}
            title={`${cam?.name || alert.cameraId} · ${hhmmss(eventAt)}`}
            eventLabel={alert.ruleSummary || alert.type}
            eventAt={eventAt}
            downloadName={`alerta_${alert.id}.mp4`}
            bookmarks={clipBookmarks}
            onAddBookmark={clipEvidence && clipEvidence.storage_state === 'available' && dossier?.permissions.can_annotate ? (t) => setPendingBookmark({ evidenceId: clipEvidence.id, t }) : undefined}
            seekRequest={seekRequest}
            unavailableText={clipEvidence?.storage_state === 'purged'
              ? 'Clipul a fost purjat (șters deliberat). Nu se afișează niciun substitut; metadatele și amprenta rămân în dosar.'
              : clipEvidence?.storage_state === 'missing' ? 'Fișierul clipului lipsește din stocare. Înregistrarea probei și amprenta SHA-256 rămân în dosar.'
              : clipEvidence?.storage_state === 'unavailable' ? 'Serviciul de stocare nu a răspuns; clipul poate exista în continuare. Reîncercați mai târziu.' : undefined}
          />
        </div>

        {/* Human decision, context, history */}
        <div className="col-span-12 md:col-span-4 flex flex-col gap-3 min-h-0 overflow-hidden">
          <div className={card}>
            <div className={`${cardTitle} flex items-center gap-1.5`}><UserCheck size={13} /> Verificare umană</div>
            {decided ? (
              <div className="text-xs">
                <div className="flex items-center gap-2">
                  {alert.status === 'confirmed' ? <CheckCircle2 size={16} className="text-[#2ED47A]" /> : <XCircle size={16} className="text-[#FF3B3B]" />}
                  <span className="font-bold uppercase tracking-wider">{alert.status === 'confirmed' ? 'Alertă confirmată' : 'Alertă respinsă'}</span>
                </div>
                {(alert.decidedBy || alert.decidedAt) && (
                  <div className="text-[#7D8A9B] mt-1">{alert.decidedBy}{alert.decidedAt ? ` · ${hhmmss(new Date(alert.decidedAt).getTime())}` : ''}</div>
                )}
                {alert.decisionNote && <div className="text-[#7D8A9B] mt-1 italic">„{alert.decisionNote}”</div>}
              </div>
            ) : canDecide ? (
              <>
                <p className="text-[11px] text-[#7D8A9B] mb-2.5">Urmăriți clipul și decideți. Decizia aparține exclusiv dispecerului; detecția automată nu este o constatare.</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    disabled={saving}
                    onClick={handleConfirm}
                    className="py-2 rounded-md bg-[#2ED47A] text-[#0A0E14] font-sans font-bold text-base tracking-wider uppercase hover:bg-[#26B96A] transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Confirmă
                  </button>
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => setRejectModalOpen(true)}
                    className="py-2 rounded-md border border-[#FF3B3B] text-[#FF3B3B] font-sans font-bold text-base tracking-wider uppercase hover:bg-[#FF3B3B]/10 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Respinge
                  </button>
                </div>
              </>
            ) : (
              <p className="text-xs text-[#7D8A9B]">Rolul dumneavoastră nu permite clasificarea alertelor.</p>
            )}
            {canDispatch && !decided && (
              <button
                type="button"
                disabled={saving}
                onClick={handleDispatchPatrol}
                className="mt-2 w-full py-2 rounded-md bg-[#3DA5FF] text-white font-sans font-bold text-base tracking-wider uppercase hover:bg-[#2C94F0] transition-colors cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Navigation size={15} /> Confirmă · recomandă patrulă
              </button>
            )}
            {dispatchSuccess && (
              <div className="mt-2 p-1.5 rounded bg-[#2ED47A]/15 border border-[#2ED47A]/40 text-[#2ED47A] text-[11px] font-semibold text-center">
                ✓ Recomandarea a fost înregistrată în audit. Nu s-a trimis nicio comandă externă.
              </div>
            )}
            {conflict && (
              <div role="alert" data-testid="decision-conflict" className="mt-2 p-1.5 rounded bg-[#FFC23D]/15 border border-[#FFC23D]/40 text-[#FFC23D] text-[11px] font-semibold">
                Conflict: {conflict} Decizia dumneavoastră nu a fost salvată.
              </div>
            )}
            {dossier && decided && (
              <p className="mt-2 text-[10px] text-[#536070]">{dossier.decision.action_label ? `${dossier.decision.action_label}. ` : ''}{dossier.decision.external_effect}</p>
            )}
          </div>

          <div className={card}>
            <div className={cardTitle}>Context</div>
            <dl className="grid grid-cols-3 gap-y-1.5 text-xs">
              <dt className="text-[#7D8A9B]">Cameră</dt>
              <dd className="col-span-2 font-medium truncate" title={cam?.name}>{cam?.name || alert.cameraId}</dd>
              <dt className="text-[#7D8A9B]">Locație</dt>
              <dd className="col-span-2 truncate" title={cam?.road}>{cam?.road || '—'}</dd>
              <dt className="text-[#7D8A9B]">Ora</dt>
              <dd className="col-span-2 font-mono" title={dossier?.observation_note}>
                {dossier ? `${dossier.observed_at_local.replace('T', ' ').slice(0, 19)} (${dossier.timezone}, UTC${dossier.observed_at_local.slice(-6)})` : new Date(eventAt).toLocaleString('ro-RO')}
              </dd>
              {alert.metrics.speedKmh !== undefined && (
                <>
                  <dt className="text-[#7D8A9B]">Viteză</dt>
                  <dd className="col-span-2 font-mono" data-testid="speed">
                    ~{Math.round(alert.metrics.speedKmh)} km/h{alert.metrics.speedLimitKmh ? ` (prag ${alert.metrics.speedLimitKmh})` : ''}
                    <span className="block font-sans text-[10px] text-[#FFC23D]">estimare necalibrată, nu măsurătoare certificată</span>
                  </dd>
                </>
              )}
              {prov && (
                <>
                  <dt className="text-[#7D8A9B]">Sursă</dt>
                  <dd className="col-span-2" title={prov.source_basis} data-testid="source-kind">
                    {prov.source_kind === 'live' ? 'Flux live' : prov.source_kind === 'recorded_replay' ? 'Înregistrare redată (replay)' : 'Necunoscută (live sau replay nu este raportat)'}
                  </dd>
                  <dt className="text-[#7D8A9B]">Model</dt>
                  <dd className="col-span-2" data-testid="model-status">
                    {prov.model_status === 'recorded' ? `${prov.model_id ?? ''} ${prov.model_hash ? `· ${prov.model_hash.slice(0, 12)}` : ''}` : 'Neînregistrat · model nevalidat pentru acest caz'}
                  </dd>
                </>
              )}
              {alert.metrics.vehicleClass && (
                <>
                  <dt className="text-[#7D8A9B]">Obiect</dt>
                  <dd className="col-span-2 capitalize">{alert.metrics.vehicleClass}</dd>
                </>
              )}
            </dl>
          </div>

          {dossier ? <HistoryPanel dossier={dossier} /> : (
          <div className={`${card} flex-1 min-h-0 overflow-hidden`}>
            <div className={cardTitle}>Istoric · audit</div>
            <ol className="relative border-l border-[#1E2A36] ml-1.5 space-y-2">
              {timeline.map((step, idx) => (
                <li key={idx} className="pl-3 relative">
                  <span className={`absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full ${idx === timeline.length - 1 ? 'bg-[#3DA5FF]' : 'bg-[#17202B] border border-[#2ED47A]'}`} />
                  <div className="text-[11px] font-mono font-bold">{step.time}</div>
                  <div className="text-[11px] text-[#7D8A9B] leading-tight truncate">{step.label}</div>
                </li>
              ))}
            </ol>
          </div>
          )}
        </div>
      </div>

      {USE_MOCKS ? (
        <p className="text-xs text-[#FFC23D] shrink-0">Mod demo (VITE_USE_MOCKS): dosarul de investigație (note, marcaje, export) funcționează doar cu serverul real.</p>
      ) : dossierError ? (
        <p role="alert" className="text-xs text-[#FF3B3B] shrink-0">Dosarul nu a putut fi încărcat: {dossierError}</p>
      ) : !dossier ? (
        <div className="text-xs text-[#7D8A9B] flex items-center gap-2 shrink-0" aria-busy="true"><Loader2 size={14} className="animate-spin" /> Se încarcă dosarul de investigație…</div>
      ) : (
        <div className="grid grid-cols-12 gap-3 shrink-0 pb-4" data-testid="case-workspace">
          <div className="col-span-12">
            <ContextStrip dossier={dossier} />
          </div>
          <div className="col-span-12 lg:col-span-4 flex flex-col gap-3">
            <LegalHoldPanel number={id} dossier={dossier} reload={reloadCase} />
            <EvidencePanel dossier={dossier} />
            <BookmarksPanel number={id} dossier={dossier} reload={reloadCase} onSeek={seek} pendingBookmark={pendingBookmark} clearPendingBookmark={() => setPendingBookmark(null)} />
          </div>
          <div className="col-span-12 lg:col-span-5 flex flex-col gap-3">
            <NotesPanel number={id} dossier={dossier} reload={reloadCase} onSeek={seek} pendingBookmark={pendingBookmark} clearPendingBookmark={() => setPendingBookmark(null)} />
            <FollowupsPanel number={id} dossier={dossier} reload={reloadCase} />
            <RelatedPanel number={id} dossier={dossier} reload={reloadCase} />
          </div>
          <div className="col-span-12 lg:col-span-3">
            <ExportPanel number={id} dossier={dossier} />
          </div>
        </div>
      )}

      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0A0E14]/80 backdrop-blur-sm">
          <div className="bg-[#111821] border border-[#1E2A36] rounded-md p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-[#FF3B3B] mb-2 font-sans text-xl font-bold uppercase">
              <AlertTriangle size={20} /> Motiv respingere alertă
            </div>
            <p className="text-xs text-[#7D8A9B] mb-4">Nota este obligatorie și se păstrează în audit pentru a justifica respingerea alertei.</p>
            <textarea
              rows={3}
              autoFocus
              value={rejectionNote}
              onChange={(e) => setRejectionNote(e.target.value)}
              placeholder="Ex: fals pozitiv – umbră pe carosabil, vehiculul circula regulamentar..."
              className="w-full bg-[#17202B] border border-[#1E2A36] rounded-md p-3 text-xs text-[#E6EDF3] placeholder-[#536070] focus:outline-none focus:border-[#FF3B3B] mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setRejectModalOpen(false)} className="px-4 py-2 rounded-md bg-[#17202B] border border-[#1E2A36] text-xs font-semibold text-[#7D8A9B] hover:text-[#E6EDF3] cursor-pointer">
                Anulează
              </button>
              <button
                type="button"
                disabled={!rejectionNote.trim() || saving}
                onClick={handleRejectSubmit}
                className="px-5 py-2 rounded-md bg-[#FF3B3B] text-white text-xs font-bold uppercase tracking-wider disabled:opacity-50 cursor-pointer"
              >
                Confirmă respingerea
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
