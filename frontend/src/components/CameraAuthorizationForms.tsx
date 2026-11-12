import { useState } from 'react'
import { Button } from '@/components/ui'
import { createCamera, createGrant, registerSource, SOURCE_LABEL, type GrantInput, type SourceKind } from '@/lib/cameraControl'

const field = 'bg-elevation border border-border rounded px-2 py-1 text-xs text-text-primary w-full'
const KINDS = Object.keys(SOURCE_LABEL) as SourceKind[]
const URL_HINT: Record<SourceKind, string> = {
  recorded_replay: 'replay://cale/relativă/clip.mp4 (doar o referință: fișierul rămâne pe mașina de procesare)',
  owned_optical_live: 'rtsp://… , https://… sau device://0',
  authorized_network_live: 'rtsp://… sau https://…',
}
const BASIS_LABEL: Record<GrantInput['basis'], string> = {
  written_agreement: 'Acord scris', licence: 'Licență', own_infrastructure: 'Infrastructură proprie', statutory_mandate: 'Mandat legal',
}
/** A datetime-local value in the browser's zone, as an ISO instant with offset. */
const toIso = (local: string) => new Date(local).toISOString()
const localNow = (addDays = 0) => {
  const d = new Date(Date.now() + addDays * 86_400_000)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

/** Register (or replace) the camera's source. The server shows back only a short display form of
 *  the address (scheme and host; for a recording, its reference), never credentials. */
export function SourceForm({ cameraId, revision, reason, current, run }: {
  cameraId: string; revision: number; reason: string; current: SourceKind | null
  run: (label: string, fn: () => Promise<unknown>) => Promise<boolean>
}) {
  const [kind, setKind] = useState<SourceKind>(current ?? 'recorded_replay')
  const [url, setUrl] = useState('')
  return (
    <form className="flex flex-col gap-1.5 text-xs" data-testid="source-form" onSubmit={(e) => {
      e.preventDefault()
      void run('Sursă înregistrată', () => registerSource(cameraId, kind, url, revision, reason)).then((ok) => { if (ok) setUrl('') })
    }}>
      <label className="flex flex-col gap-1">Tipul sursei
        <select className={field} value={kind} onChange={(e) => setKind(e.target.value as SourceKind)} data-testid="source-kind-input">
          {KINDS.map((k) => <option key={k} value={k}>{SOURCE_LABEL[k]}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1">Adresa sursei
        <input className={`${field} font-mono`} value={url} onChange={(e) => setUrl(e.target.value)} autoComplete="off" spellCheck={false} required minLength={3} maxLength={2048} data-testid="source-url-input" />
        <span className="text-text-secondary">{URL_HINT[kind]}. După salvare se afișează doar o formă scurtă a adresei, fără utilizator, parolă sau cale.</span>
      </label>
      <div><Button size="sm" variant="secondary" type="submit" disabled={url.trim().length < 3 || reason.trim().length < 3} data-testid="source-save">{current ? 'Înlocuiește sursa' : 'Înregistrează sursa'}</Button></div>
      {current && <p className="text-amber-300">O sursă nouă trebuie verificată din nou: configurația activă nu mai rulează până la o nouă aprobare.</p>}
    </form>
  )
}

/** Record the owner's permission to process this camera. Who granted it and on what basis are
 *  typed by the administrator; the app stores the statement, it cannot verify it. */
export function GrantForm({ cameraId, sourceKind, run }: {
  cameraId: string; sourceKind: SourceKind | null; run: (label: string, fn: () => Promise<unknown>) => Promise<boolean>
}) {
  const [g, setG] = useState({
    granting_party: '', basis: 'written_agreement' as GrantInput['basis'], basis_reference: '', purpose: '',
    valid_from: localNow(), valid_until: localNow(30), capture_method: sourceKind ?? ('recorded_replay' as SourceKind),
    max_analysis_fps: 30, max_frame_height: 1080, retention_days: 30, export_allowed: false, media_scope: 'events_only' as GrantInput['media_scope'],
  })
  const set = <K extends keyof typeof g>(key: K, value: (typeof g)[K]) => setG((prev) => ({ ...prev, [key]: value }))
  const ordered = g.valid_from && g.valid_until && new Date(g.valid_until) > new Date(g.valid_from)
  const complete = g.granting_party.trim().length >= 2 && g.basis_reference.trim().length >= 2 && g.purpose.trim().length >= 3 && ordered
  return (
    <form className="flex flex-col gap-1.5 text-xs" data-testid="grant-form" onSubmit={(e) => {
      e.preventDefault()
      void run('Autorizare înregistrată', () => createGrant(cameraId, { ...g, valid_from: toIso(g.valid_from), valid_until: toIso(g.valid_until) }))
    }}>
      <label className="flex flex-col gap-1">Cine a dat acordul (proprietarul camerei sau al fluxului)
        <input className={field} value={g.granting_party} onChange={(e) => set('granting_party', e.target.value)} maxLength={200} data-testid="grant-party" />
      </label>
      <div className="grid grid-cols-2 gap-1.5">
        <label className="flex flex-col gap-1">Temei
          <select aria-label="Temei" className={field} value={g.basis} onChange={(e) => set('basis', e.target.value as GrantInput['basis'])}>
            {(Object.keys(BASIS_LABEL) as GrantInput['basis'][]).map((b) => <option key={b} value={b}>{BASIS_LABEL[b]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">Referința documentului
          <input className={field} value={g.basis_reference} onChange={(e) => set('basis_reference', e.target.value)} maxLength={200} data-testid="grant-reference" />
        </label>
      </div>
      <label className="flex flex-col gap-1">Scopul prelucrării
        <input className={field} value={g.purpose} onChange={(e) => set('purpose', e.target.value)} maxLength={500} data-testid="grant-purpose" />
      </label>
      <div className="grid grid-cols-2 gap-1.5">
        <label className="flex flex-col gap-1">Valabilă de la
          <input className={field} type="datetime-local" value={g.valid_from} onChange={(e) => set('valid_from', e.target.value)} />
        </label>
        <label className="flex flex-col gap-1">până la
          <input className={field} type="datetime-local" value={g.valid_until} onChange={(e) => set('valid_until', e.target.value)} data-testid="grant-until" />
        </label>
      </div>
      {!ordered && <p className="text-amber-300" role="alert">Data de sfârșit trebuie să fie după cea de început.</p>}
      <div className="grid grid-cols-2 gap-1.5">
        <label className="flex flex-col gap-1">Metoda de captură acoperită
          <select className={field} value={g.capture_method} onChange={(e) => set('capture_method', e.target.value as SourceKind)}>
            {KINDS.map((k) => <option key={k} value={k}>{SOURCE_LABEL[k]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">Ce se poate păstra
          <select className={field} value={g.media_scope} onChange={(e) => set('media_scope', e.target.value as GrantInput['media_scope'])} data-testid="grant-scope">
            <option value="events_only">Doar clipurile alertelor</option>
            <option value="events_and_recordings">Alerte și înregistrări</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        <label className="flex flex-col gap-1">Cadre/s cel mult
          <input className={field} type="number" min={0.5} max={60} step={0.5} value={g.max_analysis_fps} onChange={(e) => set('max_analysis_fps', Number(e.target.value))} />
        </label>
        <label className="flex flex-col gap-1">Înălțime cadru cel mult
          <input className={field} type="number" min={64} max={8192} value={g.max_frame_height} onChange={(e) => set('max_frame_height', Number(e.target.value))} />
        </label>
        <label className="flex flex-col gap-1">Păstrare (zile)
          <input className={field} type="number" min={1} max={3650} value={g.retention_days} onChange={(e) => set('retention_days', Number(e.target.value))} />
        </label>
      </div>
      <label className="flex items-center gap-2"><input type="checkbox" checked={g.export_allowed} onChange={(e) => set('export_allowed', e.target.checked)} />Exportul dovezilor este permis de acord</label>
      <div><Button size="sm" variant="secondary" type="submit" disabled={!complete} data-testid="grant-save">Înregistrează autorizarea</Button></div>
      <p className="text-text-secondary">Aplicația păstrează declarația dumneavoastră și cine a introdus-o; nu poate verifica documentul.</p>
    </form>
  )
}

/** Register a camera. It starts "in configuration": nothing is processed until it has a source,
 *  a recorded permission and a configuration approved by a second administrator. */
export function AddCameraDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const [slug, setSlug] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const slugOk = slug === '' || /^[A-Za-z0-9_-]{1,64}$/.test(slug)
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <form role="dialog" aria-modal="true" aria-label="Adaugă cameră" data-testid="add-camera" className="w-full max-w-md bg-void border border-border rounded-md p-4 flex flex-col gap-2 text-xs text-text-primary"
        onClick={(e) => e.stopPropagation()} onSubmit={(e) => {
          e.preventDefault()
          setBusy(true); setError(null)
          createCamera({ name: name.trim(), location: location.trim(), ...(slug ? { slug } : {}) })
            .then((camera) => onCreated(camera.id))
            .catch((err: Error) => setError(err.message))
            .finally(() => setBusy(false))
        }}>
        <h2 className="font-heading text-lg font-bold">Adaugă cameră</h2>
        <p className="text-text-secondary">Camera este doar înregistrată. Nu se procesează nimic până când are o sursă, o autorizare și o configurație aprobată de un al doilea administrator.</p>
        <label className="flex flex-col gap-1">Nume
          <input className={field} value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={200} required data-testid="add-camera-name" />
        </label>
        <label className="flex flex-col gap-1">Amplasare
          <input className={field} value={location} onChange={(e) => setLocation(e.target.value)} minLength={2} maxLength={300} required data-testid="add-camera-location" />
        </label>
        <label className="flex flex-col gap-1">Identificator stabil (opțional; litere, cifre, „-” și „_”)
          <input className={`${field} font-mono`} value={slug} onChange={(e) => setSlug(e.target.value)} maxLength={64} data-testid="add-camera-slug" />
        </label>
        {!slugOk && <p className="text-amber-300" role="alert">Identificatorul poate avea doar litere, cifre, „-” și „_”.</p>}
        {error && <p className="text-rose-300" role="alert" data-testid="add-camera-error">Camera nu a fost adăugată: {error}</p>}
        <div className="flex gap-2 pt-1">
          <Button size="sm" variant="confirm" type="submit" disabled={busy || name.trim().length < 2 || location.trim().length < 2 || !slugOk} data-testid="add-camera-save">Adaugă</Button>
          <Button size="sm" variant="ghost" type="button" onClick={onClose}>Renunță</Button>
        </div>
      </form>
    </div>
  )
}
