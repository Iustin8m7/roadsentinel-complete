import { useEffect, useMemo, useState } from 'react'
import { Archive, Bookmark as BookmarkIcon, CheckCircle2, Clock, Download, FileWarning, History, Loader2, Lock, NotebookPen, ShieldCheck, Trash2, XCircle } from 'lucide-react'
import {
  addBookmark, addNote, approveExport, cancelExport, denyExport, downloadPackage, errorMessage, fmtOffset, listExports,
  newIdempotencyKey, noteHistory, removeBookmark, requestExport, retractNote, reviseNote, runExport,
  type CaseDossier, type CaseNote, type EvidenceItem, type ExportJob, type NoteRevision,
} from '@/lib/cases'
import { VerifyPackageForm } from './CasePanels'

const card = 'bg-[#111821] border border-[#1E2A36] rounded-md p-3.5'
const title = 'font-sans font-bold text-xs uppercase tracking-wider text-[#7D8A9B] mb-2 flex items-center gap-1.5'
const input = 'w-full bg-[#17202B] border border-[#1E2A36] rounded-md p-2 text-xs text-[#E6EDF3] placeholder-[#536070] focus:outline-none focus:border-[#3DA5FF]'
const btn = 'px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-[#3DA5FF]'
const primary = `${btn} bg-[#3DA5FF] text-white hover:bg-[#2C94F0]`
const ghost = `${btn} bg-[#17202B] border border-[#1E2A36] text-[#7D8A9B] hover:text-[#E6EDF3]`
const fmtTime = (iso: string) => new Date(iso).toLocaleString('ro-RO', { dateStyle: 'short', timeStyle: 'medium' })

const KIND_LABEL: Record<string, string> = { keyframe: 'Cadru cheie', clip: 'Clip video', camera_video: 'Înregistrare cameră' }
const STATE: Record<EvidenceItem['storage_state'], { label: string; cls: string }> = {
  available: { label: 'Disponibilă', cls: 'text-[#2ED47A] border-[#2ED47A]/40 bg-[#2ED47A]/10' },
  missing: { label: 'Lipsește din stocare', cls: 'text-[#FFC23D] border-[#FFC23D]/40 bg-[#FFC23D]/10' },
  purged: { label: 'Purjată', cls: 'text-[#FF3B3B] border-[#FF3B3B]/40 bg-[#FF3B3B]/10' },
  unavailable: { label: 'Stocare indisponibilă', cls: 'text-[#3DA5FF] border-[#3DA5FF]/40 bg-[#3DA5FF]/10' },
}
const EXPORT_STATE: Record<ExportJob['state'], string> = {
  pending_approval: 'Așteaptă aprobarea unui al doilea administrator',
  queued: 'Aprobat · în coadă pentru generare',
  processing: 'Se generează…',
  completed: 'Gata de descărcare',
  failed: 'Eșuat',
  denied: 'Respins de aprobator',
  canceled: 'Anulat',
  expired: 'Expirat (pachet șters)',
}
export const HISTORY_LABEL: Record<string, string> = {
  detected: 'Detecție automată', viewed: 'Vizualizat', confirmed: 'Confirmat', rejected: 'Respins', assigned: 'Asignat patrulei',
  vlm_verdict: 'Verificare VLM', decision_conflict: 'Decizie concurentă refuzată', note_created: 'Notă adăugată',
  note_revised: 'Notă revizuită', note_retracted: 'Notă retrasă', bookmark_created: 'Marcaj adăugat', bookmark_removed: 'Marcaj șters',
  evidence_missing: 'Probă lipsă la acces', export_requested: 'Export solicitat', export_approved: 'Export aprobat',
  export_denied: 'Export respins', export_canceled: 'Export anulat', export_generated: 'Pachet generat',
  export_failed: 'Export eșuat', export_downloaded: 'Pachet descărcat', export_expired: 'Pachet expirat',
  link_created: 'Legătură adăugată', link_removed: 'Legătură eliminată', followup_created: 'Sarcină adăugată',
  followup_updated: 'Sarcină modificată', legal_hold_placed: 'Reținere legală plasată', legal_hold_released: 'Reținere legală ridicată',
  purge_refused: 'Purjare refuzată (reținere legală)',
}

interface Props {
  number: string
  dossier: CaseDossier
  reload: () => Promise<void>
  onSeek: (evidenceId: string, t: number) => void
  pendingBookmark: { evidenceId: string; t: number } | null
  clearPendingBookmark: () => void
}

function Status({ error }: { error: string | null }) {
  return error ? <p role="alert" className="text-[11px] text-[#FF3B3B] mt-1.5">{error}</p> : null
}

export function EvidencePanel({ dossier }: { dossier: CaseDossier }) {
  return (
    <section className={card} aria-labelledby="ev-title">
      <h2 id="ev-title" className={title}><ShieldCheck size={13} /> Probe ({dossier.evidence.length})</h2>
      {dossier.evidence.length === 0 && <p className="text-xs text-[#7D8A9B]">Cazul nu are probe stocate.</p>}
      <ul className="space-y-2">
        {dossier.evidence.map((ev) => (
          <li key={ev.id} className="text-[11px] border border-[#1E2A36] rounded p-2" data-testid={`evidence-${ev.kind}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-[#E6EDF3]">{KIND_LABEL[ev.kind] ?? ev.kind}</span>
              <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${STATE[ev.storage_state].cls}`} data-testid="storage-state">
                {STATE[ev.storage_state].label}{ev.purged_at ? ` · ${fmtTime(ev.purged_at)}` : ''}
              </span>
            </div>
            <div className="text-[#7D8A9B] mt-1">Mascare: {ev.redaction_label}</div>
            <div className="text-[#7D8A9B]">
              {ev.original_exists ? 'Există original nemascat (acces doar cu aprobare)' : 'Nu există original nemascat stocat'}
              {' · '}{ev.sha256_recorded ? 'SHA-256 înregistrat la preluare' : 'fără amprentă SHA-256'}
              {ev.duration_s ? ` · ${ev.duration_s.toFixed(2)} s` : ''}
            </div>
            {ev.storage_state !== 'available' && (
              <div className="mt-1 flex items-center gap-1 text-[#FFC23D]"><FileWarning size={12} />
                {ev.storage_state === 'purged' ? 'Fișierul a fost șters deliberat; nu se afișează niciun substitut.'
                  : ev.storage_state === 'unavailable' ? 'Serviciul de stocare nu a răspuns; fișierul poate exista în continuare. Reîncercați mai târziu.'
                  : 'Înregistrarea există, dar fișierul nu mai este în stocare.'}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

export function BookmarksPanel({ number, dossier, reload, onSeek, pendingBookmark, clearPendingBookmark }: Props) {
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { if (pendingBookmark) { setLabel(''); setError(null) } }, [pendingBookmark])
  const save = async () => {
    if (!pendingBookmark || !label.trim()) return
    setBusy(true); setError(null)
    try {
      await addBookmark(number, { evidence_id: pendingBookmark.evidenceId, offset_s: Number(pendingBookmark.t.toFixed(3)), label: label.trim() })
      clearPendingBookmark(); await reload()
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  const remove = async (id: string) => {
    setError(null)
    try { await removeBookmark(number, id); await reload() } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <section className={card} aria-labelledby="bm-title">
      <h2 id="bm-title" className={title}><BookmarkIcon size={13} /> Marcaje pe cronologie ({dossier.bookmarks.length})</h2>
      {pendingBookmark && (
        <form onSubmit={(e) => { e.preventDefault(); void save() }} className="mb-2 flex gap-2 items-center" aria-label="Marcaj nou">
          <span className="font-mono text-[11px] text-[#FFC23D] shrink-0">{fmtOffset(pendingBookmark.t)}</span>
          <input autoFocus value={label} maxLength={120} onChange={(e) => setLabel(e.target.value)} placeholder="Etichetă marcaj" aria-label="Etichetă marcaj" className={input} />
          <button type="submit" disabled={busy || !label.trim()} className={primary}>Salvează</button>
          <button type="button" onClick={clearPendingBookmark} className={ghost}>Renunță</button>
        </form>
      )}
      {dossier.bookmarks.length === 0 && !pendingBookmark && (
        <p className="text-xs text-[#7D8A9B]">{dossier.permissions.can_annotate ? 'Folosiți butonul „Marcaj” din player pentru a marca momentul curent.' : 'Niciun marcaj.'}</p>
      )}
      <ul className="space-y-1">
        {dossier.bookmarks.map((b) => (
          <li key={b.id} className="flex items-center gap-2 text-[11px]" data-testid="bookmark-item">
            <button type="button" onClick={() => onSeek(b.evidence_id, b.offset_s)} className="font-mono text-[#FFC23D] hover:underline cursor-pointer" aria-label={`Sari la ${fmtOffset(b.offset_s)}`}>
              {fmtOffset(b.offset_s)}
            </button>
            <span className="text-[#E6EDF3] truncate flex-1">{b.label}</span>
            <span className="text-[#536070] shrink-0">{b.author}</span>
            {b.can_remove && (
              <button type="button" onClick={() => void remove(b.id)} className="text-[#7D8A9B] hover:text-[#FF3B3B] cursor-pointer" aria-label={`Șterge marcajul ${b.label}`}><Trash2 size={12} /></button>
            )}
          </li>
        ))}
      </ul>
      <Status error={error} />
    </section>
  )
}

function NoteItem({ number, note, catalog, reload, onSeek }: { number: string; note: CaseNote; catalog: Record<string, string>; reload: () => Promise<void>; onSeek: Props['onSeek'] }) {
  const [mode, setMode] = useState<'view' | 'edit' | 'retract' | 'history'>('view')
  const [text, setText] = useState(note.body)
  const [reason, setReason] = useState('')
  const [history, setHistory] = useState<NoteRevision[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const retracted = !!note.retracted_at
  const act = async (fn: () => Promise<unknown>) => {
    setError(null)
    try { await fn(); setMode('view'); await reload() } catch (e) { setError(errorMessage(e)) }
  }
  const showHistory = async () => {
    setMode('history')
    try { setHistory(await noteHistory(number, note.id)) } catch (e) { setError(errorMessage(e)) }
  }
  return (
    <li className="border border-[#1E2A36] rounded p-2 text-[11px]" data-testid="note-item">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`px-1.5 rounded text-[10px] font-bold uppercase ${note.kind === 'observation' ? 'bg-[#3DA5FF]/15 text-[#3DA5FF]' : 'bg-[#B48CFF]/15 text-[#B48CFF]'}`}>
          {note.kind === 'observation' ? 'Observație' : 'Interpretare'}
        </span>
        <span className="text-[#E6EDF3] font-semibold">{note.author}</span>
        <span className="text-[#536070]">{fmtTime(note.created_at)}</span>
        {note.revision > 1 && (
          <button type="button" onClick={() => void showHistory()} className="text-[#7D8A9B] hover:text-[#3DA5FF] underline cursor-pointer">
            revizia {note.revision} · istoric
          </button>
        )}
        {note.track_id !== null && <span className="font-mono text-[#7D8A9B]" data-testid="note-track-ref">traseu #{note.track_id}</span>}
        {note.bbox && <span className="font-mono text-[#7D8A9B]" data-testid="note-bbox-ref" title="Chenarul detecției înregistrat de pipeline (pixeli)">chenar [{note.bbox.map((v) => Math.round(v * 10) / 10).join(', ')}]</span>}
        {note.evidence_id && note.offset_s !== null && (
          <button type="button" onClick={() => onSeek(note.evidence_id!, note.offset_s!)} className="font-mono text-[#FFC23D] hover:underline cursor-pointer">
            @ {fmtOffset(note.offset_s)}
          </button>
        )}
      </div>
      {/* Plain text only: React escapes it; no HTML or markdown is interpreted. */}
      <p className={`mt-1 whitespace-pre-wrap break-words ${retracted ? 'line-through text-[#536070]' : 'text-[#E6EDF3]'}`}>{note.body}</p>
      {note.tags.length > 0 && <div className="mt-1 flex flex-wrap gap-1">{note.tags.map((t) => <span key={t} className="px-1.5 rounded bg-[#17202B] text-[#7D8A9B]">{catalog[t] ?? t}</span>)}</div>}
      {retracted && <p className="mt-1 text-[#FF8A1F]">Retrasă de {note.retracted_by} · {fmtTime(note.retracted_at!)} — motiv: {note.retract_reason}</p>}
      {mode === 'view' && (note.can_revise || note.can_retract) && (
        <div className="mt-1.5 flex gap-2">
          {note.can_revise && <button type="button" className={ghost} onClick={() => { setText(note.body); setMode('edit') }}>Revizuiește</button>}
          {note.can_retract && <button type="button" className={ghost} onClick={() => setMode('retract')}>Retrage</button>}
        </div>
      )}
      {mode === 'edit' && (
        <form className="mt-1.5 space-y-1.5" onSubmit={(e) => { e.preventDefault(); void act(() => reviseNote(number, note.id, { body: text, tags: note.tags })) }}>
          <textarea rows={3} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} className={input} aria-label="Text revizuit" />
          <p className="text-[10px] text-[#536070]">Revizia nouă se adaugă; textul anterior rămâne în istoric.</p>
          <div className="flex gap-2"><button type="submit" disabled={!text.trim()} className={primary}>Salvează revizia</button><button type="button" onClick={() => setMode('view')} className={ghost}>Renunță</button></div>
        </form>
      )}
      {mode === 'retract' && (
        <form className="mt-1.5 space-y-1.5" onSubmit={(e) => { e.preventDefault(); void act(() => retractNote(number, note.id, reason)) }}>
          <input autoFocus value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} placeholder="Motivul retragerii (obligatoriu)" aria-label="Motivul retragerii" className={input} />
          <div className="flex gap-2"><button type="submit" disabled={reason.trim().length < 3} className={primary}>Retrage nota</button><button type="button" onClick={() => setMode('view')} className={ghost}>Renunță</button></div>
        </form>
      )}
      {mode === 'history' && (
        <div className="mt-1.5 border-l-2 border-[#1E2A36] pl-2 space-y-1">
          {!history && <Loader2 size={12} className="animate-spin" />}
          {history?.map((h) => (
            <div key={h.revision}><span className="text-[#536070]">rev. {h.revision} · {h.author} · {fmtTime(h.created_at)}</span><p className="whitespace-pre-wrap text-[#7D8A9B]">{h.body}</p></div>
          ))}
          <button type="button" onClick={() => setMode('view')} className={ghost}>Închide istoricul</button>
        </div>
      )}
      <Status error={error} />
    </li>
  )
}

export function NotesPanel({ number, dossier, reload, onSeek }: Props) {
  const [filter, setFilter] = useState<'all' | CaseNote['kind']>('all')
  const [kind, setKind] = useState<CaseNote['kind']>('observation')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [offset, setOffset] = useState('')
  const [citeTrack, setCiteTrack] = useState(false)
  const [citeBox, setCiteBox] = useState(false)
  const ref = dossier.detection_ref
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const clip = dossier.evidence.find((e) => e.kind === 'clip' && e.storage_state === 'available')
  const notes = useMemo(() => dossier.notes.filter((n) => filter === 'all' || n.kind === filter), [dossier.notes, filter])
  const submit = async () => {
    setBusy(true); setError(null)
    try {
      const at = offset.trim() === '' ? undefined : Number(offset.replace(',', '.'))
      await addNote(number, {
        kind, body, tags, ...(at !== undefined && clip ? { evidence_id: clip.id, offset_s: at } : {}),
        ...(citeTrack && ref?.track_id != null ? { track_id: ref.track_id } : {}),
        ...(citeBox && ref?.bbox ? { bbox: ref.bbox } : {}),
      })
      setBody(''); setTags([]); setOffset(''); setCiteTrack(false); setCiteBox(false); await reload()
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  return (
    <section className={card} aria-labelledby="notes-title">
      <h2 id="notes-title" className={title}><NotebookPen size={13} /> Note de investigație ({dossier.notes.length})</h2>
      <div className="flex gap-1 mb-2" role="group" aria-label="Filtru note">
        {(['all', 'observation', 'interpretation'] as const).map((f) => (
          <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className={`${btn} ${filter === f ? 'bg-[#3DA5FF]/20 text-[#3DA5FF]' : 'text-[#7D8A9B]'}`}>
            {f === 'all' ? 'Toate' : f === 'observation' ? 'Observații' : 'Interpretări'}
          </button>
        ))}
      </div>
      <ol className="space-y-2 mb-3">
        {notes.length === 0 && <li className="text-xs text-[#7D8A9B]">Nicio notă.</li>}
        {notes.map((n) => <NoteItem key={n.id} number={number} note={n} catalog={dossier.tag_catalog} reload={reload} onSeek={onSeek} />)}
      </ol>
      {dossier.permissions.can_annotate ? (
        <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="space-y-1.5 border-t border-[#1E2A36] pt-2" aria-label="Notă nouă">
          <div className="flex gap-3 text-[11px]" role="radiogroup" aria-label="Tipul notei">
            {(['observation', 'interpretation'] as const).map((k) => (
              <label key={k} className="flex items-center gap-1 cursor-pointer">
                <input type="radio" name="note-kind" checked={kind === k} onChange={() => setKind(k)} />
                {k === 'observation' ? 'Observație (ce se vede)' : 'Interpretare (concluzia analistului)'}
              </label>
            ))}
          </div>
          <textarea rows={3} maxLength={4000} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Text simplu, fără formatare" aria-label="Textul notei" className={input} />
          <div className="text-[10px] text-[#536070] text-right">{body.length}/4000</div>
          <fieldset className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
            <legend className="sr-only">Etichete din catalog</legend>
            {Object.entries(dossier.tag_catalog).map(([key, label]) => (
              <label key={key} className="flex items-center gap-1 cursor-pointer text-[#7D8A9B]">
                <input type="checkbox" checked={tags.includes(key)} onChange={() => setTags((t) => t.includes(key) ? t.filter((x) => x !== key) : [...t, key])} />{label}
              </label>
            ))}
          </fieldset>
          {clip && (
            <label className="flex items-center gap-2 text-[11px] text-[#7D8A9B]">
              Moment în clip (s, opțional)
              <input value={offset} onChange={(e) => setOffset(e.target.value)} inputMode="decimal" className={`${input} w-24`} aria-label="Moment în clip în secunde" />
            </label>
          )}
          {ref && (
            <fieldset className="text-[11px] text-[#7D8A9B] space-y-0.5" data-testid="detection-ref">
              <legend className="sr-only">Referințe la detecție</legend>
              {ref.track_id !== null && (
                <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={citeTrack} onChange={(e) => setCiteTrack(e.target.checked)} />Citează traseul #{ref.track_id} (înregistrat de pipeline)</label>
              )}
              {ref.bbox_status === 'recorded' && ref.bbox ? (
                <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={citeBox} onChange={(e) => setCiteBox(e.target.checked)} />Citează chenarul detecției [{ref.bbox.join(', ')}]</label>
              ) : <p className="text-[10px] text-[#536070]">{ref.note}</p>}
            </fieldset>
          )}
          <button type="submit" disabled={busy || !body.trim()} className={primary}>{busy ? 'Se salvează…' : 'Adaugă nota'}</button>
          <Status error={error} />
        </form>
      ) : <p className="text-[11px] text-[#7D8A9B]">Rolul dumneavoastră nu permite adăugarea de note.</p>}
    </section>
  )
}

export function ExportPanel({ number, dossier }: { number: string; dossier: CaseDossier }) {
  const [jobs, setJobs] = useState<ExportJob[] | null>(null)
  const [justification, setJustification] = useState('')
  const [reference, setReference] = useState('')
  const [original, setOriginal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const originalPossible = dossier.evidence.length > 0 && dossier.evidence.every((e) => e.original_exists)
  const refresh = async () => { try { setJobs(await listExports(number)) } catch (e) { setError(errorMessage(e)) } }
  useEffect(() => { void refresh() }, [number])
  const act = async (fn: () => Promise<unknown>, done?: string) => {
    setBusy(true); setError(null); setNotice(null)
    try { await fn(); if (done) setNotice(done); await refresh() } catch (e) { setError(errorMessage(e)); await refresh() } finally { setBusy(false) }
  }
  const submit = () => act(async () => {
    await requestExport(number, { justification, case_reference: reference, include_original: original, idempotency_key: newIdempotencyKey() })
    setJustification(''); setReference(''); setOriginal(false)
  }, 'Cererea a fost înregistrată; așteaptă aprobarea unui alt administrator.')
  return (
    <section className={card} aria-labelledby="export-title">
      <h2 id="export-title" className={title}><Archive size={13} /> Pachet de probe (export controlat)</h2>
      <p className="text-[11px] text-[#7D8A9B] mb-2">
        Pachetul conține probele mascate ale cazului, manifestul cu amprente SHA-256 și instrucțiuni de verificare. Necesită aprobarea unui al doilea administrator; linkul de descărcare este de unică folosință pe termen scurt.
      </p>
      {jobs === null && <div className="text-xs text-[#7D8A9B] flex items-center gap-1"><Loader2 size={12} className="animate-spin" /> Se încarcă…</div>}
      <ul className="space-y-2 mb-2">
        {jobs?.map((j) => (
          <li key={j.id} className="border border-[#1E2A36] rounded p-2 text-[11px]" data-testid="export-item" data-state={j.state}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-[#E6EDF3]">{EXPORT_STATE[j.state]}</span>
              <span className="text-[#536070]">{j.requester} · {fmtTime(j.created_at)}</span>
            </div>
            <div className="text-[#7D8A9B]">{j.include_original ? 'Include originale nemascate (aprobate)' : 'Doar variante mascate'}{j.approved_by ? ` · aprobat de ${j.approved_by}` : ''}{j.error ? ` · cod: ${j.error}` : ''}</div>
            {j.state === 'processing' && j.error === 'storage_unavailable' && (
              <div className="text-[#FFC23D]">Stocarea nu a răspuns; generarea se reia automat (încercări de stocare: {j.storage_retries ?? 0}). Nu s-a consumat nicio încercare.</div>
            )}
            {j.legal_hold && (j.state === 'completed' || j.state === 'canceled') && (
              <div className="text-[#FFC23D]" data-testid="export-held">Păstrat sub reținere legală: nu se șterge la expirare; descărcarea cere în continuare o aprobare activă.</div>
            )}
            {j.state === 'completed' && (
              <div className="mt-1 text-[#7D8A9B] break-all">
                Manifest SHA-256: <code className="text-[#E6EDF3]" data-testid="manifest-sha256">{j.manifest_sha256}</code>
                <div>{j.file_count} fișiere · {((j.package_size ?? 0) / 1024).toFixed(1)} KiB · nesemnat (verificare prin amprente) · expiră {j.expires_at ? fmtTime(j.expires_at) : '—'}</div>
              </div>
            )}
            <div className="mt-1.5 flex flex-wrap gap-2">
              {j.state === 'pending_approval' && dossier.permissions.can_approve_export && !j.requested_by_me && j.approval_id && (
                <>
                  <button type="button" disabled={busy} className={`${btn} bg-[#2ED47A] text-[#0A0E14]`} onClick={() => void act(() => approveExport(j.approval_id!), 'Export aprobat.')}><CheckCircle2 size={12} className="inline mr-1" />Aprobă exportul</button>
                  <button type="button" disabled={busy} className={`${btn} border border-[#FF3B3B] text-[#FF3B3B]`} onClick={() => void act(() => denyExport(j.approval_id!))}><XCircle size={12} className="inline mr-1" />Respinge</button>
                </>
              )}
              {j.state === 'pending_approval' && j.requested_by_me && <span className="text-[#536070] flex items-center gap-1"><Lock size={11} /> Nu vă puteți aproba propria cerere.</span>}
              {(j.state === 'queued' || j.state === 'processing') && (
                <button type="button" disabled={busy} className={primary} onClick={() => void act(() => runExport(j.id))}><Clock size={12} className="inline mr-1" />Generează pachetul</button>
              )}
              {j.state === 'completed' && j.requested_by_me && (
                <button type="button" disabled={busy} className={primary} onClick={() => void act(() => downloadPackage(j), 'Pachet descărcat. Verificați amprenta manifestului cu cea afișată.')}>
                  <Download size={12} className="inline mr-1" />Descarcă pachetul
                </button>
              )}
              {(j.state === 'pending_approval' || j.state === 'queued') && (j.requested_by_me || dossier.permissions.can_approve_export) && (
                <button type="button" disabled={busy} className={ghost} onClick={() => void act(() => cancelExport(j.id))}>Anulează</button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {dossier.permissions.can_request_export ? (
        <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="space-y-1.5 border-t border-[#1E2A36] pt-2" aria-label="Cerere export">
          <textarea rows={2} maxLength={2000} value={justification} onChange={(e) => setJustification(e.target.value)} placeholder="Justificare (minimum 10 caractere)" aria-label="Justificare export" className={input} />
          <input value={reference} maxLength={100} onChange={(e) => setReference(e.target.value)} placeholder="Referință dosar (ex. DOS-2026-17)" aria-label="Referință dosar" className={input} />
          <label className={`flex items-center gap-2 text-[11px] ${originalPossible ? 'text-[#7D8A9B]' : 'text-[#536070]'}`}>
            <input type="checkbox" checked={original} disabled={!originalPossible} onChange={(e) => setOriginal(e.target.checked)} />
            Include originalele nemascate {originalPossible ? '(necesită aprobare de demascare activă pentru fiecare probă)' : '— indisponibil: nu există original nemascat stocat'}
          </label>
          <button type="submit" disabled={busy || justification.trim().length < 10 || !reference.trim()} className={primary}>Solicită export</button>
        </form>
      ) : <p className="text-[11px] text-[#7D8A9B]">Rolul dumneavoastră nu permite solicitarea exportului.</p>}
      {notice && <p role="status" className="text-[11px] text-[#2ED47A] mt-1.5">{notice}</p>}
      <Status error={error} />
      <VerifyPackageForm />
    </section>
  )
}

export function HistoryPanel({ dossier }: { dossier: CaseDossier }) {
  return (
    <section className={`${card} min-h-0 overflow-hidden`} aria-labelledby="hist-title">
      <h2 id="hist-title" className={title}><History size={13} /> Istoric · audit</h2>
      <ol className="relative border-l border-[#1E2A36] ml-1.5 space-y-2 max-h-64 overflow-y-auto pr-1">
        {dossier.history.map((h) => (
          <li key={h.id} className="pl-3 relative">
            <span className="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-[#17202B] border border-[#2ED47A]" />
            <div className="text-[11px] font-mono font-bold">{new Date(h.at).toLocaleTimeString('ro-RO')}</div>
            <div className="text-[11px] text-[#7D8A9B] leading-tight">{HISTORY_LABEL[h.action] ?? h.action} · {h.actor}{h.note ? ` — ${h.note}` : ''}</div>
          </li>
        ))}
      </ol>
    </section>
  )
}
