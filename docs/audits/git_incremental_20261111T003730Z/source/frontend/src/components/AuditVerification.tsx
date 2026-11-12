// Auditor verification view: hash-chain check and per-evidence chain-of-custody status.
// Read-only; every state is what the server reported, including incomplete chains.
import { useState } from 'react'
import { Link } from 'react-router'
import { Loader2, ShieldAlert, ShieldCheck } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { useDataStore } from '@/store/data'
import { auditVerify, errorMessage, evidenceIntegrity, type AuditVerify, type IntegrityItem, type IntegrityState } from '@/lib/cases'

const INTEGRITY: Record<IntegrityState, { label: string; cls: string }> = {
  match: { label: 'Corespunde amprentei de la preluare', cls: 'text-emerald-400' },
  mismatch: { label: 'NU corespunde amprentei', cls: 'text-rose-400 font-semibold' },
  unreadable: { label: 'Nu poate fi decriptat (alterat sau cheie greșită)', cls: 'text-rose-400 font-semibold' },
  missing: { label: 'Fișier lipsă din stocare', cls: 'text-amber-400' },
  purged: { label: 'Purjat deliberat', cls: 'text-text-secondary' },
  unavailable: { label: 'Stocare indisponibilă (necunoscut)', cls: 'text-sky-400' },
  no_hash: { label: 'Fără amprentă digitală la preluare', cls: 'text-amber-400' },
  not_checked: { label: 'Neverificat încă', cls: 'text-text-secondary' },
}
const KIND: Record<string, string> = { keyframe: 'Cadru cheie', clip: 'Clip', camera_video: 'Înregistrare cameră' }
const fail = (e: unknown) => e instanceof ApiError && e.status === 403 ? 'Acces refuzat: verificarea este rezervată rolurilor de audit.' : errorMessage(e)

const CHAIN_REASON: Record<string, string> = {
  'prev_hash mismatch': 'legătura cu intrarea anterioară nu corespunde',
  'entry_hash mismatch': 'conținutul intrării a fost modificat',
}

function ChainResult({ r }: { r: AuditVerify }) {
  if (r.ok && r.checked === 0) return <p className="text-amber-400" data-testid="chain-state">Lanț gol: nu există încă intrări de audit pentru această unitate.</p>
  if (r.ok) return <p className="text-emerald-400" data-testid="chain-state">Lanț intact: {r.checked} intrări verificate.</p>
  return (
    <p className="text-rose-400 font-semibold" data-testid="chain-state">
      Lanț rupt la intrarea #{r.first_broken_seq} ({CHAIN_REASON[r.reason ?? ''] ?? r.reason}). Au fost parcurse {r.checked} intrări; ce urmează nu poate fi considerat intact.
    </p>
  )
}

export function AuditVerificationPanel() {
  const cameras = useDataStore((s) => s.cameras)
  const [chain, setChain] = useState<AuditVerify | null>(null)
  const [items, setItems] = useState<IntegrityItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [cursor, setCursor] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)
  const [busy, setBusy] = useState<'chain' | 'list' | 'verify' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')

  const runChain = async () => {
    setBusy('chain'); setError(null)
    try { setChain(await auditVerify()) } catch (e) { setError(fail(e)) } finally { setBusy(null) }
  }
  const load = async (verify: boolean, append = false) => {
    setBusy(verify ? 'verify' : 'list'); setError(null)
    try {
      const page = await evidenceIntegrity(verify, append ? cursor : null)
      setItems((prev) => append && prev ? [...prev, ...page.items] : page.items)
      setTotal(page.total); setCursor(page.next_cursor); setVerified(page.verified); setNote(page.note)
    } catch (e) { setError(fail(e)) } finally { setBusy(null) }
  }
  const problems = items?.filter((i) => ['mismatch', 'unreadable', 'missing', 'no_hash'].includes(i.integrity)).length ?? 0

  return (
    <section className="bg-panel border border-border rounded-md p-3 shrink-0 max-h-[45vh] overflow-y-auto text-xs" aria-labelledby="verify-title" data-testid="audit-verification">
      <h2 id="verify-title" className="font-bold text-text-primary flex items-center gap-2 mb-2">
        <ShieldCheck className="w-4 h-4 text-emerald-400" /> Verificare integritate (doar citire)
      </h2>
      <div className="flex flex-wrap gap-2 mb-2">
        <button type="button" onClick={() => void runChain()} disabled={busy !== null} className="px-3 py-1.5 rounded-md bg-accent text-white font-semibold disabled:opacity-50">
          {busy === 'chain' && <Loader2 className="w-3.5 h-3.5 inline animate-spin mr-1" />}Verifică lanțul de audit
        </button>
        <button type="button" onClick={() => void load(false)} disabled={busy !== null} className="px-3 py-1.5 rounded-md border border-border text-text-primary disabled:opacity-50">
          {busy === 'list' && <Loader2 className="w-3.5 h-3.5 inline animate-spin mr-1" />}Starea probelor
        </button>
        <button type="button" onClick={() => void load(true)} disabled={busy !== null} className="px-3 py-1.5 rounded-md border border-border text-text-primary disabled:opacity-50">
          {busy === 'verify' && <Loader2 className="w-3.5 h-3.5 inline animate-spin mr-1" />}Recalculează amprentele (cele mai noi 20)
        </button>
      </div>
      {error && <p role="alert" className="text-rose-400 mb-2">{error}</p>}
      {chain && (
        <div className="mb-2 space-y-0.5" role="status">
          <ChainResult r={chain} />
          {chain.head_hash && <p className="text-text-secondary break-all">Amprentă digitală curentă a jurnalului: <code className="text-[10px]" data-testid="chain-head">{chain.head_hash}</code></p>}
          <p className="text-[10px] text-text-secondary">Lanțul este verificat pe același sistem care îl scrie: dovadă de modificare, nu ancoră independentă.</p>
        </div>
      )}
      {items && (
        <div>
          <p className="text-text-secondary mb-1" data-testid="integrity-summary">
            {items.length} din {total} probe afișate{verified ? ` · amprente recalculate · ${problems} cu probleme` : ' · amprentele nu au fost recalculate'}
          </p>
          {items.length === 0 ? <p className="text-text-secondary">Nicio probă stocată.</p> : (
            <table className="w-full text-left border-collapse">
              <thead className="text-[10px] uppercase text-text-secondary"><tr><th className="py-1 pr-2">Probă</th><th className="py-1 pr-2">Caz / cameră</th><th className="py-1 pr-2">Amprentă digitală</th><th className="py-1">Stare</th></tr></thead>
              <tbody className="divide-y divide-border/60">
                {items.map((i) => (
                  <tr key={i.id} data-testid="integrity-row" data-integrity={i.integrity}>
                    <td className="py-1 pr-2 font-mono">{KIND[i.kind] ?? i.kind} <span className="text-[10px] text-text-secondary/70" title="Identificator intern al probei">{i.id.slice(0, 8)}</span></td>
                    <td className="py-1 pr-2">{i.event_id ? <Link to={`/app/alerte/${i.event_id}`} className="text-accent hover:underline">#{i.event_id}</Link> : '—'}{i.camera_id ? ` · ${cameras.find((c) => c.id === i.camera_id)?.name ?? i.camera_id}` : ''}</td>
                    <td className="py-1 pr-2">{i.sha256_recorded ? 'înregistrată' : 'lipsă'}{i.distinct_original ? ' · original separat' : ''}</td>
                    <td className={`py-1 ${INTEGRITY[i.integrity].cls}`}>{i.integrity === 'mismatch' || i.integrity === 'unreadable' ? <ShieldAlert className="w-3.5 h-3.5 inline mr-1" /> : null}{INTEGRITY[i.integrity].label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {cursor && !verified && (
            <button type="button" onClick={() => void load(false, true)} disabled={busy !== null} className="mt-2 px-3 py-1 rounded-md border border-border text-text-primary">Încarcă mai multe</button>
          )}
          {note && <p className="text-[10px] text-text-secondary mt-1">{note}</p>}
        </div>
      )}
    </section>
  )
}
