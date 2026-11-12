import { useState } from 'react'
import { Link } from 'react-router'
import { post } from '@/lib/api'
import { Button } from '@/components/ui'
export default function OfflinePromotion({ recording, run, index }: {recording: string; run: string; index: number}) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [synthetic, setSynthetic] = useState(false)
  const [error, setError] = useState('')
  const [id, setId] = useState<number | null>(null)
  async function submit() {
    setBusy(true); setError('')
    try { const result = await post<{id: number}>(`/api/recordings/${recording}/analyses/${run}/candidates/${index}/promote`, {reason, synthetic_test: synthetic}); setId(result.id) }
    catch (error) { setError((error as Error).message) }
    finally { setBusy(false) }
  }
  if (id) return <Link className="text-action underline" to={`/app/alerte/${id}`}>RECORDED · deschide alerta #{id}</Link>
  return <div className="mt-2 flex flex-col gap-2"><label className="text-xs">Motivul verificării (minimum 10 caractere)<input className="block w-full rounded border border-border bg-panel p-2" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={synthetic} onChange={e => setSynthetic(e.target.checked)} /> Material de test sintetic (marchează explicit alerta)</label><Button loading={busy} disabled={busy || reason.trim().length < 10} onClick={() => void submit()}>Trimite înregistrarea pentru verificare</Button>{error && <p role="alert" className="text-critical text-xs">{error}</p>}</div>
}
