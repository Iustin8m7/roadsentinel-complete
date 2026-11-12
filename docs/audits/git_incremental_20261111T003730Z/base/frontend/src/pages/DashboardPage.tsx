import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ChevronLeft, ChevronRight, Inbox, Play } from 'lucide-react'
import { useQueue, useStats } from '@/hooks'
import { useDataStore, cameraById } from '@/store/data'
import { demoAgo } from '@/lib/demo'
import { useNow } from '@/hooks'
import { ALERT_TYPE } from '@/lib/constants'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusBadge } from '@/components/ui'
import { TacticalMap } from '@/components/TacticalMap'
import { ClipModal } from '@/components/ClipModal'

// MOCK: the backend has no patrols yet.
const PATROLS = [
  { callsign: 'IS-21-POL', status: 'Disponibilă', color: '#2ED47A', area: 'Copou' },
  { callsign: 'IS-14-POL', status: 'În misiune', color: '#FF8A1F', area: 'Podu Roș' },
  { callsign: 'IS-07-POL', status: 'Disponibilă', color: '#2ED47A', area: 'Tătărași' },
  { callsign: 'IS-33-POL', status: 'Pauză', color: '#7D8A9B', area: 'Nicolina' },
]
const ROW_H = 68 // px per queue row incl. gap; the queue shows as many rows as fit, no scrolling

const ACCENT: Record<string, string> = { critical: '#FF3B3B', high: '#FF8A1F', medium: '#FFC23D', info: '#3DA5FF' }

export default function DashboardPage() {
  const cameras = useDataStore((s) => s.cameras)
  const queue = useQueue()
  const openCount = queue.filter((a) => a.status === 'new' || a.status === 'in_review').length
  useNow(1000)
  const stats = useStats()
  const listRef = useRef<HTMLDivElement>(null)
  const [perPage, setPerPage] = useState(6)
  const [page, setPage] = useState(0)
  const [playing, setPlaying] = useState<number | null>(null)

  useLayoutEffect(() => {
    const el = listRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setPerPage(Math.max(1, Math.floor((el.clientHeight + 8) / ROW_H))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const pages = Math.max(1, Math.ceil(queue.length / perPage))
  useEffect(() => { if (page > pages - 1) setPage(pages - 1) }, [page, pages])
  const visible = queue.slice(page * perPage, page * perPage + perPage)

  const camerasOnline = cameras.filter((c) => c.status !== 'offline').length
  const availablePatrols = PATROLS.filter((p) => p.status === 'Disponibilă').length
  const kpi = 'bg-[#111821] border border-[#1E2A36] rounded-md px-3.5 py-2.5'

  return (
    <div className="h-full flex flex-col p-4 gap-3 overflow-hidden bg-[#0A0E14] select-none">
      <div className="grid grid-cols-4 gap-3 shrink-0">
        <div className={kpi}>
          <div className="text-xs text-[#7D8A9B] font-medium">Alerte de verificat</div>
          <div className="font-sans text-3xl font-bold text-[#E6EDF3] leading-none mt-1">{openCount}</div>
        </div>
        <div className={kpi}>
          <div className="text-xs text-[#7D8A9B] font-medium">Camere online</div>
          <div className="font-sans text-3xl font-bold text-[#E6EDF3] leading-none mt-1">{camerasOnline}/{cameras.length}</div>
        </div>
        <div className={kpi}>
          <div className="text-xs text-[#7D8A9B] font-medium">Patrule disponibile</div>
          <div className="font-sans text-3xl font-bold text-[#E6EDF3] leading-none mt-1">{availablePatrols}/{PATROLS.length}</div>
        </div>
        <div className={kpi}>
          <div className="text-xs text-[#7D8A9B] font-medium">Rată alarme false</div>
          <div className="font-sans text-3xl font-bold text-[#E6EDF3] leading-none mt-1">
            {stats.falseAlarmRate ? `${Math.round(stats.falseAlarmRate * 100)}%` : '—'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Alert queue: paged to fit the viewport */}
        <div className="col-span-12 md:col-span-7 flex flex-col min-h-0 bg-[#111821] border border-[#1E2A36] rounded-md">
          <div className="px-3.5 py-2.5 border-b border-[#1E2A36] flex items-center justify-between shrink-0">
            <h2 className="font-sans text-base font-bold uppercase tracking-wider text-[#E6EDF3]">Coada de alerte</h2>
            <div className="flex items-center gap-2 text-xs text-[#7D8A9B] font-mono">
              <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="p-1 rounded hover:text-[#E6EDF3] disabled:opacity-30 cursor-pointer"><ChevronLeft size={15} /></button>
              <span className="tabular-nums">{queue.length ? `${page * perPage + 1}–${Math.min(queue.length, (page + 1) * perPage)} din ${queue.length}` : '0'}</span>
              <button type="button" disabled={page >= pages - 1} onClick={() => setPage(page + 1)} className="p-1 rounded hover:text-[#E6EDF3] disabled:opacity-30 cursor-pointer"><ChevronRight size={15} /></button>
            </div>
          </div>

          <div ref={listRef} className="p-2.5 flex-1 min-h-0 overflow-hidden flex flex-col gap-2">
            {queue.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center gap-2 text-[#7D8A9B] text-sm">
                <Inbox size={26} /> Nicio alertă de verificat.
              </div>
            )}
            {visible.map((alert, i) => {
              const cam = cameraById(alert.cameraId)
              return (
                <div
                  key={alert.id}
                  className="h-[60px] shrink-0 flex items-center gap-3 rounded-md border border-[#1E2A36] bg-[#0F151D] hover:bg-[#17202B] pr-2 overflow-hidden transition-colors"
                  style={{ borderLeft: `4px solid ${ACCENT[alert.severity]}` }}
                >
                  <button
                    type="button"
                    title="Redă clipul"
                    onClick={() => setPlaying(page * perPage + i)}
                    className="relative w-[88px] h-full shrink-0 bg-black group cursor-pointer"
                  >
                    {alert.keyframeUrl && <img src={alert.keyframeUrl} alt="" loading="lazy" className="w-full h-full object-cover" />}
                    <span className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/10">
                      <Play size={16} className="text-white fill-white" />
                    </span>
                  </button>
                  <Link to={`/app/alerte/${alert.id}`} className="flex-1 min-w-0 flex items-center gap-3 h-full">
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-sm text-[#E6EDF3] uppercase tracking-wide truncate">{ALERT_TYPE[alert.type]?.label ?? alert.ruleSummary}</div>
                      <div className="text-[11px] text-[#7D8A9B] truncate">
                        {cam?.name ?? alert.cameraId}
                        {alert.metrics.speedKmh !== undefined && ` · ~${Math.round(alert.metrics.speedKmh)} km/h`}
                      </div>
                    </div>
                    {alert.status === 'confirmed' || alert.status === 'rejected' || alert.status === 'closed' ? <StatusBadge status={alert.status} /> : <SeverityBadge severity={alert.severity} />}
                    <span className="w-16 text-right font-mono text-[11px] text-[#7D8A9B] shrink-0">{demoAgo(alert)}</span>
                    <span className="px-2.5 py-1 rounded-md bg-[#3DA5FF]/15 border border-[#3DA5FF]/40 text-[#3DA5FF] text-[11px] font-bold shrink-0">Verifică</span>
                  </Link>
                </div>
              )
            })}
          </div>
        </div>

        <div className="col-span-12 md:col-span-5 flex flex-col gap-3 min-h-0">
          <div className="flex-1 min-h-0">
            <TacticalMap className="w-full h-full" />
          </div>
          <div className="bg-[#111821] border border-[#1E2A36] rounded-md px-3.5 py-2.5 shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <h3 className="font-sans text-sm font-bold uppercase tracking-wider text-[#E6EDF3]">Patrule pe teren</h3>
              <span className="text-[10px] text-[#536070] font-mono">DEMO</span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {PATROLS.map((p) => (
                <div key={p.callsign} className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                  <span className="font-mono font-bold text-[#E6EDF3]">{p.callsign}</span>
                  <span className="text-[11px] truncate" style={{ color: p.color }}>{p.status}</span>
                  <span className="text-[11px] text-[#7D8A9B] ml-auto">{p.area}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {playing !== null && (
        <ClipModal
          clips={queue.map((a) => ({
            id: a.id,
            title: `${ALERT_TYPE[a.type]?.label ?? a.type} · ${cameraById(a.cameraId)?.name ?? a.cameraId}`,
            subtitle: new Date(a.createdAt).toLocaleString('ro-RO'),
            src: a.clip?.src,
            poster: a.keyframeUrl,
            at: a.createdAt,
          }))}
          start={playing}
          onClose={() => setPlaying(null)}
        />
      )}
    </div>
  )
}
