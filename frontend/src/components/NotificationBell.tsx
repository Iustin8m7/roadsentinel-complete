import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Bell, X } from 'lucide-react'
import { useNavigate } from 'react-router'
import { api, apiUrl, USE_MOCKS } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import { useDataStore } from '@/store/data'

type Notice = { id:string; sequence:number; incident_id:string; alert_number:number; kind:string; priority:string; provenance:string; status:string; created_at:string; read_at:string|null; acknowledged_at:string|null; dismissed_at:string|null }
type Inbox = { items:Notice[]; unread:number; latest_sequence:number; next_cursor:number|null }

function label(n:Notice) {
  const origin = n.provenance === 'recorded_upload' ? 'Înregistrare analizată' : n.provenance === 'local_replay' ? 'Replay local' : n.provenance === 'manual_entry' ? 'Introdus manual' : 'Cameră autorizată'
  const action = n.kind === 'candidate_created' ? 'Incident posibil, necesită verificare' : n.kind === 'confirmed' ? 'Incident confirmat' : n.kind === 'location_revised' ? 'Locația incidentului a fost actualizată' : n.kind === 'assigned' ? 'Patrulă alocată' : n.kind.startsWith('patrol_') ? 'Starea patrulei s-a schimbat' : 'Candidat respins'
  return `${action} · ${origin} · #${n.alert_number}`
}

export default function NotificationBell() {
  const navigate = useNavigate()
  const allowed = useAuthStore(s => s.user?.backendPermissions?.includes('alerts:read') ?? false)
  const soundEnabled = useDataStore(s => s.settings.soundOnCritical)
  const [items, setItems] = useState<Notice[]>([])
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)
  const [toast, setToast] = useState<Notice|null>(null)
  const [error, setError] = useState('')
  const [next, setNext] = useState<number|null>(null)
  const seen = useRef(new Set<string>())
  const soundRef = useRef(soundEnabled)
  const gesture = useRef(false)
  soundRef.current = soundEnabled
  useEffect(() => { const enable = () => { gesture.current = true }; window.addEventListener('pointerdown', enable); window.addEventListener('keydown', enable); return () => { window.removeEventListener('pointerdown', enable); window.removeEventListener('keydown', enable) } }, [])
  const ring = () => {
    if (!gesture.current || !soundRef.current) return
    try {
      const audio = new AudioContext()
      const tone = audio.createOscillator()
      tone.frequency.value = 740
      tone.connect(audio.destination)
      void audio.resume().then(() => { tone.start(); tone.stop(audio.currentTime + .12); window.setTimeout(() => { void audio.close().catch(() => {}) }, 350) }).catch(() => { void audio.close().catch(() => {}) })
    } catch { /* browser blocked audio; in-app notification still works */ }
  }
  useEffect(() => {
    if (USE_MOCKS || !allowed) return
    let active = true
    let stream:EventSource|null = null
    const sync = async () => {
      const page = await api<Inbox>('/api/notifications')
      if (!active) return
      setItems(page.items); setUnread(page.unread); setNext(page.next_cursor)
      return page.latest_sequence
    }
    void api<{sound_on_critical:boolean}>('/api/notifications/preferences').then(p => { if(active) useDataStore.getState().updateSettings({soundOnCritical:p.sound_on_critical}) }).catch(() => {})
    void sync().then(cursor => {
      if (!active || cursor === undefined) return
      stream = new EventSource(apiUrl(`/api/notifications/stream?after=${cursor}`), { withCredentials:true })
      stream.addEventListener('notification', event => {
        try {
          const notice = JSON.parse((event as MessageEvent).data) as Notice
          if (seen.current.has(notice.id)) return
          seen.current.add(notice.id)
          if (seen.current.size > 500) seen.current.clear()
          setToast(notice)
          if (notice.kind === 'candidate_created' && notice.priority === 'critical') ring()
          window.dispatchEvent(new Event('roadsentinel:incident-changed'))
          void sync().catch(() => setError('Notificările nu pot fi actualizate.'))
        } catch { setError('Notificare invalidă primită de la server.') }
      })
      stream.onerror = () => { if (active) setError('Conexiunea notificărilor se restabilește…') }
      stream.onopen = () => { if (active) { setError(''); void sync().catch(() => {}) } }
    }).catch(() => { if (active) setError('Notificările nu pot fi încărcate.') })
    const onFocus = () => { void sync().catch(() => {}) }
    window.addEventListener('focus', onFocus)
    return () => { active = false; stream?.close(); window.removeEventListener('focus', onFocus); seen.current.clear(); setItems([]); setUnread(0) }
  }, [allowed])
  if (USE_MOCKS || !allowed) return null
  const update = async (n:Notice, action:'read'|'acknowledge'|'dismiss') => {
    try { await api(`/api/notifications/${n.id}/${action}`, {method:'POST'}); const page = await api<Inbox>('/api/notifications'); setItems(page.items); setUnread(page.unread) }
    catch { setError('Starea notificării nu a putut fi salvată.') }
  }
  const openIncident = (n:Notice) => { void update(n, 'read'); setOpen(false); setToast(null); navigate(`/app/alerte/${n.alert_number}`) }
  const more = async () => { if (!next) return; try { const page=await api<Inbox>(`/api/notifications?before=${next}`); setItems(old=>[...old,...page.items.filter(n=>!old.some(p=>p.id===n.id))]); setNext(page.next_cursor) } catch { setError('Pagina următoare nu poate fi încărcată.') } }
  const saveSound = async (value:boolean) => { try { const saved=await api<{sound_on_critical:boolean}>('/api/notifications/preferences',{method:'PUT',body:JSON.stringify({sound_on_critical:value})});useDataStore.getState().updateSettings({soundOnCritical:saved.sound_on_critical}) } catch { setError('Preferința audio nu a putut fi salvată.') } }
  return <>
    <div className="relative">
      <button type="button" aria-label={`Notificări, ${unread} necitite`} aria-expanded={open} onClick={()=>setOpen(v=>!v)} className="relative min-h-10 min-w-10 rounded-md border border-border bg-panel p-2"><Bell size={20}/>{unread>0&&<span className="absolute -top-1 -right-1 rounded-full bg-danger px-1.5 text-xs text-white">{unread>99?'99+':unread}</span>}</button>
      {open&&<section aria-label="Centrul notificărilor" className="absolute right-0 top-12 z-50 max-h-[70vh] w-[min(90vw,26rem)] overflow-y-auto rounded-xl border border-border bg-panel p-3 shadow-xl"><h2 className="font-semibold">Notificări</h2><label className="block text-xs"><input type="checkbox" checked={soundEnabled} onChange={e=>void saveSound(e.target.checked)}/> Sunet pentru candidați critici (după interacțiune)</label>{items.length===0&&<p className="text-sm">Nicio notificare.</p>}<ul className="space-y-2">{items.filter(n=>!n.dismissed_at).map(n=><li key={n.id} className="rounded border border-border p-2 text-sm"><button className="text-left font-medium underline" onClick={()=>openIncident(n)}>{label(n)}</button><p className="text-xs text-text-secondary">{new Date(n.created_at).toLocaleString('ro-RO')} · {n.read_at?'citită':'necitită'}</p><div className="flex gap-2"><button onClick={()=>void update(n,'acknowledge')} disabled={!!n.acknowledged_at}>Confirmă primirea</button><button onClick={()=>void update(n,'dismiss')}>Ascunde</button></div></li>)}</ul>{next&&<button onClick={()=>void more()}>Mai multe</button>}</section>}
    </div>
    {error&&<span role="status" className="text-xs text-caution">{error}</span>}
    {toast&&createPortal(<div role="status" aria-live="polite" className="fixed bottom-20 right-3 z-[60] max-w-sm rounded-xl border border-action bg-panel p-4 shadow-xl"><button aria-label="Închide notificarea" onClick={()=>setToast(null)} className="float-right"><X size={16}/></button><p className="font-semibold">{label(toast)}</p><p className="text-xs">Prioritate: {toast.priority}. Verificarea umană este necesară.</p><button className="mt-2 underline" onClick={()=>openIncident(toast)}>Deschide incidentul</button></div>, document.body)}
  </>
}
