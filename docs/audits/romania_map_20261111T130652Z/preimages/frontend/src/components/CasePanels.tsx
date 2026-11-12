// Investigation completion panels: related cases and links, follow-up items, legal hold,
// neighbouring-event context and uploaded-package verification. Real API only.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { CheckCircle2, FileCheck2, GitBranch, ListTodo, Loader2, Scale, Trash2, XCircle } from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  addFollowup, addLink, errorMessage, followupAssignees, MAX_VERIFY_BYTES, placeHold, releaseHold, removeLink,
  updateFollowup, verifyErrorRo, verifyPackage,
  type CaseDossier, type ContextEvent, type Followup, type FollowupStatus, type PackageVerifyResult, type Person,
} from '@/lib/cases'
import { HIDDEN_IDS } from '@/lib/demo'
import { HIDDEN_TYPES } from '@/store/data'

const card = 'bg-[#111821] border border-[#1E2A36] rounded-md p-3.5'
const title = 'font-sans font-bold text-xs uppercase tracking-wider text-[#7D8A9B] mb-2 flex items-center gap-1.5'
const input = 'w-full bg-[#17202B] border border-[#1E2A36] rounded-md p-2 text-xs text-[#E6EDF3] placeholder-[#536070] focus:outline-none focus:border-[#3DA5FF]'
const btn = 'px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-[#3DA5FF]'
const primary = `${btn} bg-[#3DA5FF] text-white hover:bg-[#2C94F0]`
const ghost = `${btn} bg-[#17202B] border border-[#1E2A36] text-[#7D8A9B] hover:text-[#E6EDF3]`
const fmtTime = (iso: string) => new Date(iso).toLocaleString('ro-RO', { dateStyle: 'short', timeStyle: 'medium' })
const fmtDate = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString('ro-RO')
const denied = (e: unknown) => e instanceof ApiError && e.status === 403
  ? 'Acces refuzat: rolul dumneavoastră nu permite această acțiune.' : errorMessage(e)

function Status({ error }: { error: string | null }) {
  return error ? <p role="alert" className="text-[11px] text-[#FF3B3B] mt-1.5">{error}</p> : null
}

// Alerts hidden everywhere else in the demo (lib/demo.ts) stay hidden in these panels too.
const shownCase = (c: { number: number; type: string }) => !HIDDEN_TYPES.has(c.type) && !HIDDEN_IDS.has(String(c.number))

interface PanelProps { number: string; dossier: CaseDossier; reload: () => Promise<void> }

// --------------------------------------------------------------------------- legal hold

export function LegalHoldPanel({ number, dossier, reload }: PanelProps) {
  const state = dossier.legal_hold
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [armed, setArmed] = useState(false)
  if (!state) return null
  const active = state.active
  const submit = async () => {
    if (active && !armed) { setArmed(true); return }  // releasing a hold takes a second, explicit click
    setArmed(false); setBusy(true); setError(null)
    try { await (active ? releaseHold(number, reason.trim()) : placeHold(number, reason.trim())); setReason(''); await reload() }
    catch (e) { setError(denied(e)) } finally { setBusy(false) }
  }
  return (
    <section className={`${card} ${active ? 'border-[#FFC23D]/60' : ''}`} aria-labelledby="hold-title" data-testid="legal-hold">
      <h2 id="hold-title" className={title}><Scale size={13} /> Reținere legală</h2>
      <p className="text-[11px] font-semibold mb-1" data-testid="legal-hold-state">
        {active ? <span className="text-[#FFC23D]">Activă din {fmtTime(active.placed_at)} · {active.placed_by}</span>
          : <span className="text-[#7D8A9B]">Cazul nu este sub reținere legală.</span>}
      </p>
      {active && <p className="text-[11px] text-[#E6EDF3] whitespace-pre-wrap break-words mb-1">Motiv: {active.reason}</p>}
      <p className="text-[10px] text-[#536070] mb-2">{state.effect}</p>
      {state.can_manage ? (
        <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="space-y-1.5" aria-label={active ? 'Ridicare reținere' : 'Plasare reținere'}>
          <input value={reason} maxLength={500} onChange={(e) => { setReason(e.target.value); setArmed(false) }} className={input}
            placeholder={active ? 'Motivul ridicării (minimum 10 caractere)' : 'Temeiul reținerii (minimum 10 caractere)'}
            aria-label={active ? 'Motivul ridicării reținerii' : 'Temeiul reținerii legale'} />
          <button type="submit" disabled={busy || reason.trim().length < 10} className={active ? ghost : primary}>
            {active ? (armed ? 'Confirmă ridicarea reținerii' : 'Ridică reținerea') : 'Plasează reținerea'}
          </button>
        </form>
      ) : <p className="text-[11px] text-[#7D8A9B]">Doar un administrator al unității poate plasa sau ridica reținerea.</p>}
      {state.history.filter((h) => !h.active).length > 0 && (
        <details className="mt-2 text-[10px] text-[#536070]">
          <summary className="cursor-pointer">Istoric rețineri ({state.history.filter((h) => !h.active).length})</summary>
          <ul className="mt-1 space-y-1">
            {state.history.filter((h) => !h.active).map((h) => (
              <li key={h.id}>{fmtTime(h.placed_at)} {h.placed_by} → ridicată {h.released_at ? fmtTime(h.released_at) : ''} de {h.released_by}: {h.release_reason}</li>
            ))}
          </ul>
        </details>
      )}
      <Status error={error} />
    </section>
  )
}

// --------------------------------------------------------------------------- related cases

export function RelatedPanel({ number, dossier, reload }: PanelProps) {
  const related = (dossier.related ?? []).filter(shownCase)
  const [other, setOther] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async () => {
    setBusy(true); setError(null)
    try { await addLink(number, Number(other), reason.trim()); setOther(''); setReason(''); await reload() }
    catch (e) { setError(denied(e)) } finally { setBusy(false) }
  }
  const [confirming, setConfirming] = useState<string | null>(null)
  const armedAt = useRef(0)
  const remove = async (id: string) => {
    if (confirming !== id) { setConfirming(id); armedAt.current = Date.now(); return }  // first click only asks
    if (Date.now() - armedAt.current < 400) return  // a double-click is not a confirmation
    setConfirming(null); setError(null)
    try { await removeLink(number, id); await reload() } catch (e) { setError(denied(e)) }
  }
  return (
    <section className={card} aria-labelledby="rel-title" data-testid="related-cases">
      <h2 id="rel-title" className={title}><GitBranch size={13} /> Cazuri legate ({related.length})</h2>
      {related.length === 0 && <p className="text-xs text-[#7D8A9B]">Niciun caz legat sau apropiat pe care îl puteți deschide.</p>}
      <ul className="space-y-1.5 mb-2">
        {related.map((r) => (
          <li key={r.number} className="text-[11px] border border-[#1E2A36] rounded p-2" data-testid="related-item">
            <div className="flex items-center justify-between gap-2">
              <Link to={`/app/alerte/${r.number}`} className="font-semibold text-[#3DA5FF] hover:underline">#{r.number} · {r.type_label}</Link>
              <span className="text-[#536070] shrink-0">{fmtTime(r.observed_at)}</span>
            </div>
            <ul className="mt-0.5 space-y-0.5">
              {r.reasons.map((why, i) => (
                <li key={`${why.kind}-${i}`} className="text-[#7D8A9B] flex items-start gap-1.5" data-testid={`relation-${why.kind}`}>
                  <span className="flex-1 break-words">
                    {why.label}{why.reason ? ` — „${why.reason}”` : ''}{why.created_by ? ` · ${why.created_by}` : ''}
                  </span>
                  {why.can_remove && why.link_id && (
                    <button type="button" onClick={() => void remove(why.link_id!)} onBlur={() => setConfirming(null)} className="text-[#7D8A9B] hover:text-[#FF3B3B] cursor-pointer" aria-label={confirming === why.link_id ? `Confirmă eliminarea legăturii cu cazul #${r.number}` : `Elimină legătura cu cazul #${r.number}`}>{confirming === why.link_id ? <span className="text-[#FF3B3B] font-semibold">Confirmă eliminarea</span> : <Trash2 size={12} />}</button>
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      {dossier.permissions.can_annotate ? (
        <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="space-y-1.5 border-t border-[#1E2A36] pt-2" aria-label="Legătură nouă">
          <div className="flex gap-2">
            <input value={other} onChange={(e) => setOther(e.target.value.replace(/\D/g, ''))} inputMode="numeric" placeholder="Nr. caz" aria-label="Numărul cazului de legat" className={`${input} w-24`} />
            <input value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} placeholder="Motivul legăturii" aria-label="Motivul legăturii" className={input} />
          </div>
          <button type="submit" disabled={busy || !other || reason.trim().length < 3} className={primary}>Leagă cazurile</button>
        </form>
      ) : null}
      <Status error={error} />
    </section>
  )
}

// --------------------------------------------------------------------------- context strip

const fmtDelta = (s: number) => {
  const abs = Math.abs(s)
  const text = abs < 60 ? `${abs.toFixed(0)} s` : `${(abs / 60).toFixed(1).replace('.', ',')} min`
  return s < 0 ? `${text} înainte` : `${text} după`
}

export function ContextStrip({ dossier }: { dossier: CaseDossier }) {
  const ctx = dossier.context
  if (!ctx) return null
  const events: ContextEvent[] = [...ctx.before, ...ctx.after].filter(shownCase)
  const pos = (d: number) => `${50 + (d / ctx.window_s) * 50}%`
  return (
    <section className={card} aria-labelledby="ctx-title" data-testid="timeline-context">
      <h2 id="ctx-title" className={title}>Context pe cronologie · aceeași cameră, ±{Math.round(ctx.window_s / 60)} min</h2>
      <div className="relative h-8 mx-3" role="list" aria-label="Evenimente vecine">
        <div className="absolute top-1/2 left-0 right-0 h-px bg-[#1E2A36]" aria-hidden />
        <span className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-[#3DA5FF] ring-2 ring-[#3DA5FF]/30" style={{ left: '50%' }} title="Acest caz" aria-hidden />
        {events.map((e) => (
          <div role="listitem" key={e.number}>
            <Link to={`/app/alerte/${e.number}`} data-testid="context-marker"
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-[#FFC23D] hover:scale-150 focus:scale-150 focus:outline focus:outline-2 focus:outline-[#3DA5FF] transition-transform"
              style={{ left: pos(e.delta_s) }}
              aria-label={`Caz #${e.number}, ${e.type_label}, ${fmtDelta(e.delta_s)}`} title={`#${e.number} · ${e.type_label} · ${fmtDelta(e.delta_s)}`} />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-[#536070] font-mono"><span>−{Math.round(ctx.window_s / 60)} min</span><span>detecție</span><span>+{Math.round(ctx.window_s / 60)} min</span></div>
      {events.length === 0 && <p className="text-[11px] text-[#7D8A9B] mt-1">Niciun alt eveniment vizibil al acestei camere în fereastră.</p>}
      {(ctx.truncated_before || ctx.truncated_after) && <p className="text-[10px] text-[#FFC23D] mt-1">Se afișează cel mult {ctx.limit_per_side} evenimente de fiecare parte.</p>}
      <p className="text-[10px] text-[#536070] mt-1">{ctx.note}</p>
    </section>
  )
}

// --------------------------------------------------------------------------- follow-ups

const FU_STATUS: Record<FollowupStatus, { label: string; cls: string }> = {
  open: { label: 'Deschisă', cls: 'text-[#3DA5FF] border-[#3DA5FF]/40' },
  done: { label: 'Finalizată', cls: 'text-[#2ED47A] border-[#2ED47A]/40' },
  cancelled: { label: 'Anulată', cls: 'text-[#7D8A9B] border-[#536070]/40' },
}
const CHANGE_LABEL: Record<string, string> = { created: 'creată', status: 'stare', assignee: 'responsabil', due_date: 'termen' }

function usePeople(number: string, enabled: boolean) {
  const [people, setPeople] = useState<Person[] | null>(null)
  const asked = useRef(false)
  useEffect(() => {
    if (!enabled || asked.current) return
    asked.current = true
    followupAssignees(number).then(setPeople).catch(() => setPeople([]))
  }, [number, enabled])
  return people
}

function FollowupItem({ number, fu, people, reload }: { number: string; fu: Followup; people: Person[] | null; reload: () => Promise<void> }) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const change = async (body: Parameters<typeof updateFollowup>[2]) => {
    setBusy(true); setError(null)
    try { await updateFollowup(number, fu.id, body); await reload() }
    catch (e) { setError(e instanceof ApiError && e.status === 409 ? `${e.message}` : denied(e)); await reload() }
    finally { setBusy(false) }
  }
  const st = FU_STATUS[fu.status]
  return (
    <li className="border border-[#1E2A36] rounded p-2 text-[11px]" data-testid="followup-item" data-status={fu.status}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`px-1.5 rounded border text-[10px] font-bold ${st.cls}`}>{st.label}</span>
        <span className="text-[#536070]">{fu.author} · {fmtTime(fu.created_at)}</span>
        {fu.due_date && <span className={fu.overdue ? 'text-[#FF3B3B] font-semibold' : 'text-[#7D8A9B]'}>termen {fmtDate(fu.due_date)}{fu.overdue ? ' · depășit' : ''}</span>}
      </div>
      <p className={`mt-1 whitespace-pre-wrap break-words ${fu.status === 'cancelled' ? 'line-through text-[#536070]' : 'text-[#E6EDF3]'}`}>{fu.body}</p>
      <div className="text-[#7D8A9B] mt-0.5">Responsabil: {fu.assignee ?? 'nealocat'}</div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {fu.can_change_status && fu.status === 'open' && (
          <>
            <button type="button" disabled={busy} className={`${btn} bg-[#2ED47A] text-[#0A0E14]`} onClick={() => void change({ revision: fu.revision, status: 'done' })}><CheckCircle2 size={12} className="inline mr-1" />Finalizează</button>
            <button type="button" disabled={busy} className={ghost} onClick={() => void change({ revision: fu.revision, status: 'cancelled' })}><XCircle size={12} className="inline mr-1" />Anulează</button>
          </>
        )}
        {fu.can_change_status && fu.status !== 'open' && (
          <button type="button" disabled={busy} className={ghost} onClick={() => void change({ revision: fu.revision, status: 'open' })}>Redeschide</button>
        )}
        {fu.can_reassign && people && people.length > 0 && (
          <label className="flex items-center gap-1 text-[#7D8A9B]">Responsabil
            <select value={fu.assignee_id ?? ''} disabled={busy} onChange={(e) => void change({ revision: fu.revision, assignee_id: e.target.value || null })}
              className="bg-[#17202B] border border-[#1E2A36] rounded p-1 text-[11px] text-[#E6EDF3]" aria-label={`Responsabil pentru sarcina: ${fu.body.slice(0, 40)}`}>
              <option value="">nealocat</option>
              {people.map((p) => <option key={p.id} value={p.id}>{p.name}{p.is_me ? ' (eu)' : ''}</option>)}
            </select>
          </label>
        )}
        <button type="button" onClick={() => setShowHistory((v) => !v)} aria-expanded={showHistory} className="text-[#7D8A9B] hover:text-[#3DA5FF] underline cursor-pointer">
          istoric ({fu.history.length})
        </button>
      </div>
      {showHistory && (
        <ol className="mt-1.5 border-l-2 border-[#1E2A36] pl-2 space-y-0.5 text-[10px] text-[#7D8A9B]">
          {fu.history.map((h) => (
            <li key={h.revision}>rev. {h.revision} · {CHANGE_LABEL[h.change] ?? h.change} · {FU_STATUS[h.status].label}{h.assignee ? ` · ${h.assignee}` : ''}{h.due_date ? ` · termen ${fmtDate(h.due_date)}` : ''} — {h.actor}, {fmtTime(h.at)}</li>
          ))}
        </ol>
      )}
      <Status error={error} />
    </li>
  )
}

export function FollowupsPanel({ number, dossier, reload }: PanelProps) {
  const items = dossier.followups ?? []
  const canAnnotate = dossier.permissions.can_annotate
  const people = usePeople(number, canAnnotate)
  const [body, setBody] = useState('')
  const [assignee, setAssignee] = useState('')
  const [due, setDue] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async () => {
    setBusy(true); setError(null)
    try {
      await addFollowup(number, { body: body.trim(), ...(assignee ? { assignee_id: assignee } : {}), ...(due ? { due_date: due } : {}) })
      setBody(''); setAssignee(''); setDue(''); await reload()
    } catch (e) { setError(denied(e)) } finally { setBusy(false) }
  }
  const open = items.filter((f) => f.status === 'open').length
  return (
    <section className={card} aria-labelledby="fu-title" data-testid="followups">
      <h2 id="fu-title" className={title}><ListTodo size={13} /> Sarcini de urmărire ({open} deschise / {items.length})</h2>
      <ol className="space-y-2 mb-2">
        {items.length === 0 && <li className="text-xs text-[#7D8A9B]">Nicio sarcină.</li>}
        {items.map((f) => <FollowupItem key={f.id} number={number} fu={f} people={people} reload={reload} />)}
      </ol>
      {canAnnotate ? (
        <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="space-y-1.5 border-t border-[#1E2A36] pt-2" aria-label="Sarcină nouă">
          <textarea rows={2} maxLength={500} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Ce trebuie făcut (text simplu)" aria-label="Textul sarcinii" className={input} />
          <div className="flex flex-wrap gap-2 items-center text-[11px] text-[#7D8A9B]">
            <label className="flex items-center gap-1">Responsabil
              <select value={assignee} onChange={(e) => setAssignee(e.target.value)} className="bg-[#17202B] border border-[#1E2A36] rounded p-1 text-[#E6EDF3]" aria-label="Responsabilul sarcinii noi">
                <option value="">nealocat</option>
                {people?.map((p) => <option key={p.id} value={p.id}>{p.name}{p.is_me ? ' (eu)' : ''}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1">Termen
              <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className="bg-[#17202B] border border-[#1E2A36] rounded p-1 text-[#E6EDF3]" aria-label="Termenul sarcinii noi" />
            </label>
          </div>
          <button type="submit" disabled={busy || !body.trim()} className={primary}>{busy ? 'Se salvează…' : 'Adaugă sarcina'}</button>
        </form>
      ) : <p className="text-[11px] text-[#7D8A9B]">Rolul dumneavoastră nu permite adăugarea de sarcini.</p>}
      <Status error={error} />
    </section>
  )
}

// --------------------------------------------------------------------------- package verify

export function VerifyPackageForm() {
  const [file, setFile] = useState<File | null>(null)
  const [digest, setDigest] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<PackageVerifyResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const digestOk = digest === '' || /^[0-9a-fA-F]{64}$/.test(digest.trim())
  const run = async () => {
    if (!file) return
    setResult(null); setError(null)
    if (file.size > MAX_VERIFY_BYTES) { setError('Pachetul depășește 60 MB. Verificați-l pe calculator cu: python -m app.cli verify-package <fișier>.'); return }
    setBusy(true)
    try { setResult(await verifyPackage(file, digest.trim() || undefined)) }
    catch (e) { setError(e instanceof ApiError && e.status === 429 ? 'Prea multe verificări; reîncercați peste câteva minute.' : errorMessage(e)) }
    finally { setBusy(false) }
  }
  return (
    <form onSubmit={(e) => { e.preventDefault(); void run() }} className="space-y-1.5 border-t border-[#1E2A36] pt-2 mt-2" aria-label="Verificare pachet" data-testid="verify-package">
      <div className={title}><FileCheck2 size={13} /> Verifică un pachet descărcat</div>
      <p className="text-[10px] text-[#536070]">Fișierul este verificat pe server și șters imediat; nu se păstrează.</p>
      <input type="file" accept=".zip,application/zip" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null) }}
        aria-label="Pachetul .zip de verificat" className="block w-full text-[11px] text-[#7D8A9B] file:mr-2 file:px-2 file:py-1 file:rounded file:border-0 file:bg-[#17202B] file:text-[#E6EDF3]" />
      <input value={digest} onChange={(e) => setDigest(e.target.value)} placeholder="Amprenta oficială a manifestului (opțional)" aria-label="Amprenta SHA-256 oficială a manifestului" aria-invalid={!digestOk} className={input} />
      <button type="submit" disabled={busy || !file || !digestOk} className={primary}>{busy ? <><Loader2 size={12} className="inline animate-spin mr-1" />Se verifică…</> : 'Verifică pachetul'}</button>
      {result && (
        <div role="status" className={`text-[11px] rounded border p-2 ${result.ok ? 'border-[#2ED47A]/40 text-[#2ED47A]' : 'border-[#FF3B3B]/40 text-[#FF3B3B]'}`} data-testid="verify-result" data-ok={String(result.ok)}>
          <div className="font-semibold">{result.ok ? `Integritate confirmată: ${result.files_checked} fișiere verificate.` : 'Verificarea a eșuat.'}</div>
          {result.manifest_sha256 && <div className="text-[#7D8A9B] break-all">Manifest SHA-256: <code>{result.manifest_sha256}</code></div>}
          {result.server_record && <div className="text-[#7D8A9B]">Corespunde exportului {result.server_record.export_id.slice(0, 8)} al cazului #{result.server_record.event_id}.</div>}
          {result.errors.length > 0 && <ul className="list-disc ml-4">{result.errors.map((e, i) => <li key={`${i}-${e}`} className="break-all">{verifyErrorRo(e)}</li>)}</ul>}
          <div className="text-[10px] text-[#536070] mt-1">{result.note}</div>
        </div>
      )}
      <Status error={error} />
    </form>
  )
}
