import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { Inbox, Play, ArrowUpRight, Siren, ListChecks, TriangleAlert, ClipboardCheck } from 'lucide-react'
import { useQueue, useNow } from '@/hooks'
import { useDataStore, cameraById } from '@/store/data'
import { USE_MOCKS } from '@/lib/api'
import { demoAgo } from '@/lib/demo'
import { ALERT_TYPE } from '@/lib/constants'
import { fmtDateTime } from '@/lib/format'
import { SeverityBadge, severityLevel } from '@/components/SeverityBadge'
import { Button, Chip, EmptyState, RedactionChip, Skeleton, StatusBadge } from '@/components/ui'
import { ClipModal } from '@/components/ClipModal'
import { AnimatedNumber } from '@/components/AnimatedNumber'
import TacticalMap from '@/components/TacticalMap'
import type { Alert } from '@/types'

const isOpen = (a: Alert) => a.status === 'new' || a.status === 'in_review'
type Filter = 'open' | 'all'

type Tone = 'critical' | 'high' | 'neutral' | 'ok'
const TONE: Record<Tone, string> = {
  critical: 'text-critical', high: 'text-warning', neutral: 'text-action', ok: 'text-ok',
}

function Kpi({ label, value, hint, icon: Icon, tone = 'neutral', hot = false }: { label: string; value: number; hint?: string; icon: typeof Siren; tone?: Tone; hot?: boolean }) {
  return (
    <div className={`card relative overflow-hidden px-4 py-3.5 ${hot ? 'sev-edge sev-edge-critical crit-pulse !border-critical/50' : ''}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-text-secondary">{label}</span>
        <Icon size={16} aria-hidden="true" className={hot || value > 0 ? TONE[tone] : 'text-text-muted'} />
      </div>
      <div className={`text-[2.5rem] leading-none font-bold mt-2 ${hot ? 'text-critical' : ''}`}><AnimatedNumber value={value} /></div>
      <div className="text-xs text-text-muted mt-1.5 min-h-4">{hint}</div>
    </div>
  )
}

export default function DashboardPage() {
  const cameras = useDataStore((s) => s.cameras)
  const loaded = useDataStore((s) => s.loaded)
  const queue = useQueue()
  useNow(1000)
  const [filter, setFilter] = useState<Filter>('open')
  const [playing, setPlaying] = useState<string | null>(null)

  // The list does not move under the pointer: alerts that arrive later wait behind a "N alerte noi" chip.
  const seen = useRef<Set<string> | null>(null)
  const [, bump] = useState(0)
  if (seen.current === null && queue.length) seen.current = new Set(queue.map((a) => a.id))
  const pending = queue.filter((a) => seen.current && !seen.current.has(a.id))
  const shownAll = queue.filter((a) => !seen.current || seen.current.has(a.id))
  const shown = filter === 'open' ? shownAll.filter(isOpen) : shownAll
  const selectedId = useRef<string | null>(null)
  const [, setSel] = useState(0)
  useEffect(() => { if (!shown.some((a) => a.id === selectedId.current)) selectedId.current = shown[0]?.id ?? null }, [shown])
  const selected = shown.find((a) => a.id === selectedId.current) ?? shown[0]

  const counts = useMemo(() => {
    const open = queue.filter(isOpen)
    const today = new Date().toDateString()
    return {
      open: open.length,
      critical: open.filter((a) => a.severity === 'critical').length,
      high: open.filter((a) => a.severity === 'high').length,
      decidedToday: queue.filter((a) => a.decidedAt && new Date(a.decidedAt).toDateString() === today).length,
    }
  }, [queue])
  const camerasLive = cameras.filter((c) => c.status !== 'offline').length

  return (
    <div className="p-3 sm:p-4 flex flex-col gap-4">
      <div className="flex flex-col gap-1 px-1 pt-1 rise">
        <p className="eyebrow">Dispecerat · coada curentă</p>
        <p className={`font-display text-2xl sm:text-[1.75rem] font-semibold leading-tight ${counts.critical > 0 ? 'text-critical' : 'text-text-primary'}`}>
          {!loaded ? 'Se încarcă…' : counts.critical > 0
            ? `${counts.critical} ${counts.critical === 1 ? 'alertă critică așteaptă' : 'alerte critice așteaptă'} o decizie`
            : counts.open > 0 ? `${counts.open} ${counts.open === 1 ? 'alertă de verificat' : 'alerte de verificat'}` : 'Nicio alertă de verificat'}
        </p>
      </div>

      <div className="stagger grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi label="Critice" value={counts.critical} hint="dintre cele de verificat" icon={Siren} tone="critical" hot={counts.critical > 0} />
        <Kpi label="Ridicate" value={counts.high} hint="dintre cele de verificat" icon={TriangleAlert} tone="high" />
        <Kpi label="De verificat" value={counts.open} hint="nouă sau în verificare" icon={ListChecks} />
        <Kpi label="Decise azi" value={counts.decidedToday} hint={`${camerasLive}/${cameras.length} camere active`} icon={ClipboardCheck} tone="ok" />
      </div>

      <div className="grid grid-cols-12 gap-4">
        <section aria-labelledby="queue-h" className="col-span-12 xl:col-span-7 card min-w-0 self-start">
          <div className="px-4 py-3 border-b border-border-subtle flex flex-wrap items-center justify-between gap-2">
            <h2 id="queue-h" className="font-display text-lg font-semibold">Coada de alerte</h2>
            <div role="group" aria-label="Filtru listă" className="inline-flex rounded-lg border border-border overflow-hidden bg-void/50">
              {(['open', 'all'] as const).map((f) => (
                <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}
                  className={`press px-3 min-h-[var(--target-min)] text-sm cursor-pointer ${filter === f ? 'bg-elevation text-action font-semibold' : 'text-text-secondary hover:text-text-primary'}`}>
                  {f === 'open' ? 'De verificat' : 'Toate'}
                </button>
              ))}
            </div>
          </div>

          {pending.length > 0 && (
            <div className="px-4 py-2 border-b border-border-subtle bg-action/10 rise">
              <Button size="sm" onClick={() => { seen.current = new Set(queue.map((a) => a.id)); bump((n) => n + 1) }}>
                {pending.length} {pending.length === 1 ? 'alertă nouă' : 'alerte noi'}: arată
              </Button>
            </div>
          )}

          {!loaded ? (
            <div className="p-4 flex flex-col gap-2" aria-busy="true" aria-label="Se încarcă alertele">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : shown.length === 0 ? (
            <EmptyState title={filter === 'open' ? 'Nicio alertă de verificat' : 'Nicio alertă'} hint="Alertele noi apar aici în timp real." />
          ) : (
            <ul className="stagger flex flex-col gap-2 p-3">
              {shown.map((alert) => {
                const cam = cameraById(alert.cameraId)
                const isSel = selected?.id === alert.id
                const decided = !isOpen(alert)
                const lv = severityLevel(alert.severity)
                return (
                  <li key={alert.id} className={`group sev-edge ${decided ? '' : `sev-edge-${lv}`} ${lv === 'critical' && !decided ? 'crit-pulse' : ''} flex items-stretch rounded-lg overflow-hidden border ${isSel ? 'border-action/70 bg-elevation' : 'border-border-subtle bg-panel hover:bg-elevation/70'}`}>
                    <button type="button" aria-label={`Previzualizează alerta ${alert.id}`} onClick={() => { selectedId.current = alert.id; setSel((n) => n + 1) }}
                      className="relative w-24 sm:w-28 shrink-0 bg-black cursor-pointer hidden sm:block ml-1">
                      {alert.keyframeUrl && <img src={alert.keyframeUrl} alt="" loading="lazy" className="w-full h-full object-cover min-h-16" />}
                    </button>
                    <Link to={`/app/alerte/${alert.id}`} className="flex-1 min-w-0 flex flex-wrap items-center gap-x-3 gap-y-1 pl-4 pr-3 py-3">
                      <div className="flex-1 min-w-[10rem]">
                        <div className="font-display text-[0.95rem] font-semibold truncate">{ALERT_TYPE[alert.type]?.label ?? alert.ruleSummary}</div>
                        <div className="text-xs text-text-secondary truncate">
                          {cam?.name ?? alert.cameraId}
                          {alert.metrics.speedKmh !== undefined && ` · ~${Math.round(alert.metrics.speedKmh)} km/h`}
                        </div>
                      </div>
                      {decided ? <StatusBadge status={alert.status} /> : <SeverityBadge severity={alert.severity} />}
                      <time dateTime={alert.createdAt} title={fmtDateTime(alert.createdAt)} className="sm:w-28 text-right text-xs text-text-secondary font-mono tabular-nums whitespace-nowrap">
                        {demoAgo(alert)}
                      </time>
                    </Link>
                    <button type="button" aria-label={`Redă clipul alertei ${alert.id}`} onClick={() => setPlaying(alert.id)}
                      className="press px-3 text-text-secondary hover:text-action hover:bg-action/10 cursor-pointer min-w-[var(--target-min)]">
                      <Play size={16} aria-hidden="true" />
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <div className="col-span-12 xl:col-span-5 flex flex-col gap-4 min-w-0">
        <section aria-labelledby="prev-h" className="hidden xl:flex flex-col card min-w-0">
          <div className="px-4 py-3 border-b border-border-subtle"><h2 id="prev-h" className="font-display text-lg font-semibold">Previzualizare</h2></div>
          {selected ? (
            <div className="p-4 flex flex-col gap-3">
              <div className="cctv-hud-frame relative bg-black rounded-lg overflow-hidden aspect-video ring-1 ring-border">
                {selected.keyframeUrl
                  ? <img src={selected.keyframeUrl} alt={`Cadru cheie, alerta ${selected.id}`} className="w-full h-full object-contain" />
                  : <div className="w-full h-full flex items-center justify-center text-sm text-white/70">Fără cadru cheie</div>}
                <div className="cctv-hud-bottom-left" aria-hidden="true" /><div className="cctv-hud-bottom-right" aria-hidden="true" />
                <div className="absolute top-3 left-8">{USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={selected.redaction} />}</div>
              </div>
              <dl className="grid grid-cols-3 gap-y-1.5 text-sm">
                <dt className="text-text-secondary">Tip</dt><dd className="col-span-2 font-medium">{ALERT_TYPE[selected.type]?.label ?? selected.ruleSummary}</dd>
                <dt className="text-text-secondary">Cameră</dt><dd className="col-span-2">{cameraById(selected.cameraId)?.name ?? selected.cameraId}</dd>
                <dt className="text-text-secondary">Ora</dt><dd className="col-span-2 font-mono text-xs leading-5">{fmtDateTime(selected.createdAt)} (Europa/București)</dd>
                <dt className="text-text-secondary">Prioritate</dt><dd className="col-span-2"><SeverityBadge severity={selected.severity} /></dd>
              </dl>
              <div className="flex gap-2">
                <Link to={`/app/alerte/${selected.id}`} className="btn-primary press inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-on-accent text-sm font-semibold min-h-[var(--target-min)]">Deschide dosarul <ArrowUpRight size={15} aria-hidden="true" /></Link>
                <Button variant="secondary" onClick={() => setPlaying(selected.id)}>Redă clipul</Button>
              </div>
            </div>
          ) : (
            <EmptyState title="Selectați o alertă" hint="Previzualizarea apare aici." action={<Inbox size={22} className="text-text-muted" aria-hidden="true" />} />
          )}
        </section>
        <section aria-labelledby="map-h" className="card overflow-hidden min-w-0">
          <div className="px-4 py-3 border-b border-border-subtle flex items-center justify-between gap-2">
            <h2 id="map-h" className="font-display text-lg font-semibold">Hartă schematică</h2>
            <Link to="/app/camere" className="text-xs text-action hover:underline min-h-[var(--target-min)] inline-flex items-center">Camere</Link>
          </div>
          <div className="h-72 xl:h-64"><TacticalMap bare /></div>
        </section>
        </div>
      </div>

      {playing !== null && (
        <ClipModal
          clips={shown.map((a) => ({
            id: a.id,
            title: `${ALERT_TYPE[a.type]?.label ?? a.type} · ${cameraById(a.cameraId)?.name ?? a.cameraId}`,
            subtitle: fmtDateTime(a.createdAt),
            src: a.clip?.src,
            poster: a.keyframeUrl,
            at: a.createdAt,
            chip: USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={a.redaction} />,
          }))}
          start={Math.max(0, shown.findIndex((a) => a.id === playing))}
          onClose={() => setPlaying(null)}
        />
      )}
    </div>
  )
}
