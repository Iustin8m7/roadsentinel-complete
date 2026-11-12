import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ShieldCheck } from 'lucide-react'
import { onReauthPrompt, type ReauthPrompt } from '@/lib/api'
import { useModalFocus } from '@/hooks'
import { Button } from '@/components/ui'

/** MFA step-up asked by lib/api.ts when the server answers 403 reauth_required. */
export function ReauthDialog() {
  const [prompt, setPrompt] = useState<ReauthPrompt | null>(null)
  useEffect(() => onReauthPrompt(setPrompt), [])
  return prompt && <ReauthForm prompt={prompt} />
}

function ReauthForm({ prompt }: { prompt: ReauthPrompt }) {
  const panel = useRef<HTMLDivElement>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  useModalFocus(panel, () => prompt.cancel())

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!code.trim() || busy) return
    setBusy(true); setError(null)
    try { await prompt.submit(code) }
    catch (err) { setError((err as Error).message); setCode(''); setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div ref={panel} role="dialog" aria-modal="true" aria-labelledby="reauth-title" aria-describedby="reauth-help" tabIndex={-1}
        className="w-full max-w-sm bg-panel border border-border rounded-md p-5 flex flex-col gap-3 outline-none">
        <h2 id="reauth-title" className="font-heading text-lg font-bold text-text-primary flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-accent" aria-hidden />Confirmați identitatea</h2>
        <p id="reauth-help" className="text-xs text-text-secondary">Această acțiune cere o verificare recentă. Introduceți codul din aplicația de autentificare.</p>
        <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
          <label className="text-xs text-text-secondary flex flex-col gap-1">Cod de autentificare
            <input data-autofocus data-testid="reauth-code" value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" maxLength={10} required
              className="bg-elevation border border-border rounded px-2 py-1.5 text-sm font-mono text-text-primary" />
          </label>
          {error && <p role="alert" className="text-xs text-rose-400">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => prompt.cancel()}>Anulează</Button>
            <Button type="submit" size="sm" disabled={busy || !code.trim()}>{busy ? 'Se verifică…' : 'Confirmă'}</Button>
          </div>
        </form>
      </div>
    </div>
  )
}
