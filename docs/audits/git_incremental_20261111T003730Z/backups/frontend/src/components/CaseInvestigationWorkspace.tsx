import { useCallback, useEffect, useRef, useState } from 'react'
import { getCase, type CaseDossier } from '@/lib/cases'
import { EvidencePanel, BookmarksPanel, NotesPanel, ExportPanel, HistoryPanel } from '@/components/CaseWorkspace'
import { LegalHoldPanel, RelatedPanel, FollowupsPanel, ContextStrip } from '@/components/CasePanels'

export function CaseInvestigationWorkspace({ number }: { number: string }) {
  const [dossier, setDossier] = useState<CaseDossier | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<{ evidenceId: string; t: number } | null>(null)
  const refs = useRef<Record<string, HTMLVideoElement | null>>({})
  const reload = useCallback(async () => { try { setDossier(await getCase(number)); setError(null) } catch (e) { setError((e as Error).message) } }, [number])
  useEffect(() => { void reload() }, [reload])
  const seek = (id: string, t: number) => { const v=refs.current[id]; if (v) { v.currentTime=t; void v.play().catch(()=>{}) } }
  if (error) return <section className="card p-4" aria-label="Investigation workspace"><h2 className="font-semibold">Dosar și investigație</h2><p role="alert" className="text-sm text-red-400">{error}</p><button onClick={()=>void reload()} className="underline">Reîncearcă</button></section>
  if (!dossier) return <section role="status" className="card p-4">Se încarcă dosarul de investigație…</section>
  return <section className="card p-4 space-y-3" aria-label="Investigation workspace"><h2 className="font-semibold">Investigație și probe · eveniment #{number}</h2>
    {dossier.evidence.filter(e=>e.media_url && e.content_type.startsWith('video/')).map(e=><div key={e.id}><video ref={v=>{refs.current[e.id]=v}} controls preload="metadata" src={e.media_url ?? undefined} className="w-full max-h-96 bg-black"/><button className="underline text-sm mt-1" onClick={()=>{const v=refs.current[e.id];if(v)setPending({evidenceId:e.id,t:v.currentTime})}}>Marchează momentul curent</button></div>)}
    <ContextStrip dossier={dossier}/><RelatedPanel number={number} dossier={dossier} reload={reload}/><FollowupsPanel number={number} dossier={dossier} reload={reload}/><LegalHoldPanel number={number} dossier={dossier} reload={reload}/><EvidencePanel dossier={dossier}/><BookmarksPanel number={number} dossier={dossier} reload={reload} onSeek={seek} pendingBookmark={pending} clearPendingBookmark={()=>setPending(null)}/><NotesPanel number={number} dossier={dossier} reload={reload} onSeek={seek} pendingBookmark={pending} clearPendingBookmark={()=>setPending(null)}/><ExportPanel number={number} dossier={dossier}/><HistoryPanel dossier={dossier}/>
  </section>
}
