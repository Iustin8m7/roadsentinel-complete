import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router'
import { ArrowLeft, CheckCircle2, XCircle, Loader2, UserCheck } from 'lucide-react'
import { USE_MOCKS } from '@/lib/api'
import { useDataStore, decide, loadDetail, reportError, cameraById } from '@/store/data'
import { useCan } from '@/hooks'
import { useAuditStore } from '@/store/audit'
import { ALERT_TYPE, AUDIT_ACTION_LABEL } from '@/lib/constants'
import { fmtDateTime } from '@/lib/format'
import { SeverityBadge } from '@/components/SeverityBadge'
import { Button, Chip, RedactionChip, StatusBadge } from '@/components/ui'
import { ConfirmDialog } from '@/components/Dialog'
import { Field, TextArea } from '@/components/forms'
import { EvidencePlayer } from '@/components/EvidencePlayer'
import { CaseInvestigationWorkspace } from '@/components/CaseInvestigationWorkspace'
import { summarizeAlert } from '@/lib/alertSummary'
import { NotFoundPage } from './ErrorPages'

const TZ = 'Europa/București'
type Choice = 'confirm' | 'reject'

function trustedSourceUrl(value?: string) {
  if (!value) return undefined
  try {
    const url = new URL(value)
    return url.protocol === 'https:' ? url.toString() : undefined
  } catch {
    return undefined
  }
}

export default function AlertDetailPage() {
  const { id = '' } = useParams()
  const alert = useDataStore((s) => s.alerts.find((a) => a.id === id))
  const rule = useDataStore((s) => s.rules.find((r) => r.id === alert?.ruleId))
  const actions = useDataStore((s) => s.actions)
  const { markViewed, startReview, confirmAlert, rejectAlert } = useDataStore.getState()
  const canDecide = useCan('alerts.decide')
  const auditEntries = useAuditStore((s) => s.entries)

  const [loadState, setLoadState] = useState<'loading' | 'done' | 'missing'>(USE_MOCKS ? 'done' : 'loading')
  const [choice, setChoice] = useState<Choice | null>(null)
  const [action, setAction] = useState('')
  const [note, setNote] = useState('')
  const [asking, setAsking] = useState(false)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const actionKeys = Object.keys(actions)
  useEffect(() => { if (!action && actionKeys.length) setAction(actionKeys[0]) }, [actionKeys.length])

  useEffect(() => {
    if (!USE_MOCKS) {
      setLoadState('loading')
      loadDetail(id, true)
        .then(() => setLoadState('done'))
        .catch((e) => { setLoadState('missing'); reportError(e) })
      return
    }
    if (!alert) return
    markViewed(alert.id)
    if (canDecide) startReview(alert.id)
  }, [id, alert?.id])

  useEffect(() => {
    document.title = alert ? `Dosar #${alert.id} · RoadSentinel` : 'Dosar alertă · RoadSentinel'
  }, [alert])

  if (!alert) {
    if (loadState === 'loading') {
      return (
        <div role="status" className="h-full flex items-center justify-center gap-2 text-sm text-text-secondary p-6">
          <Loader2 size={18} className="animate-spin motion-reduce:animate-none text-action" aria-hidden="true" /> Se încarcă dosarul alertei…
        </div>
      )
    }
    return <NotFoundPage />
  }

  const cam = cameraById(alert.cameraId)
  const typeLabel = ALERT_TYPE[alert.type]?.label ?? alert.ruleSummary ?? alert.type
  const decided = alert.status === 'confirmed' || alert.status === 'rejected' || alert.status === 'closed'
  const noteRequired = choice === 'reject'
  const noteMissing = noteRequired && !note.trim()

  const history = auditEntries.filter((e) => e.target === alert.id).sort((x, y) => x.at.localeCompare(y.at))
  const timeline = [
    { at: alert.createdAt, label: 'Detecție automată' },
    ...history.map((e) => ({
      at: e.at,
      label: `${AUDIT_ACTION_LABEL[e.action as keyof typeof AUDIT_ACTION_LABEL] ?? e.action}${e.username ? ` · ${e.username}` : ''}${e.details ? `: ${e.details}` : ''}`,
    })),
  ]

  async function submit() {
    if (!choice) return
    setSaving(true)
    setErr(null)
    try {
      const n = note.trim() || undefined
      if (USE_MOCKS) {
        if (choice === 'confirm') confirmAlert(alert!.id, n)
        else rejectAlert(alert!.id, n ?? '')
      } else {
        await decide(id, choice, choice === 'confirm' ? action || undefined : undefined, n)
      }
      setAsking(false)
    } catch (e) {
      setErr((e as Error).message || 'Decizia nu a putut fi înregistrată.')
    } finally {
      setSaving(false)
    }
  }

  const summary = summarizeAlert({type: alert.type, typeLabel, cameraName: cam?.name, at: alert.createdAt, objectClass: alert.metrics?.vehicleClass, speedKmh: alert.metrics?.speedKmh, limitKmh: alert.metrics?.speedLimitKmh, rule: alert.ruleSummary, status: alert.status, decidedBy: alert.decidedBy, decidedAt: alert.decidedAt})
  const card = 'card p-4'
  const cardTitle = 'font-display text-base font-semibold text-text-primary mb-3'

  return (
    <div className="flex flex-col p-3 sm:p-5 gap-4 text-text-primary pb-28 lg:pb-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
          <Link to="/app" className="text-sm text-text-secondary hover:text-action flex items-center gap-1 shrink-0 min-h-[var(--target-min)]">
            <ArrowLeft size={14} aria-hidden="true" /> Alerte
          </Link>
          <span className="font-mono text-sm text-text-muted shrink-0">#{alert.id}</span>
          <h1 className="font-display text-2xl font-bold basis-full sm:basis-auto">{typeLabel}</h1>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SeverityBadge severity={alert.severity} />
          <StatusBadge status={alert.status} />
        </div>
      </div>
      <p className={`text-sm text-text-secondary -mt-2 pl-3 border-l-2 ${alert.severity === 'critical' && !decided ? 'border-critical' : 'border-border'}`}>
        {cam?.name ?? alert.cameraId} · <span className="font-mono">{fmtDateTime(alert.createdAt)}</span> ({TZ})
      </p>

      <section className="card p-4" aria-label="Pe scurt"><h2 className="font-semibold">Pe scurt</h2><p>{summary.what}</p><p className="text-sm text-text-secondary">{summary.why}</p><p className="text-sm">{summary.next}</p></section>
      <div className="grid grid-cols-12 gap-3">
        <section aria-label="Dovezi" className="col-span-12 lg:col-span-8 min-h-[22rem] lg:h-[34rem]">
          <EvidencePlayer
            src={alert.clip?.src}
            poster={alert.keyframeUrl}
            title={`${cam?.name || alert.cameraId} · ${fmtDateTime(alert.createdAt).slice(11)}`}
            eventLabel={typeLabel}
            eventOffsetSec={alert.clip.eventOffsetSec}
            fps={alert.clip.fps}
            downloadName={`alerta_${alert.id}.mp4`}
            chip={USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={alert.redaction} />}
          />
        </section>

        <div className="col-span-12 lg:col-span-4 flex flex-col gap-3">
          <section aria-labelledby="dec-h" className={`${card} ${!decided && canDecide ? 'glass lg:!bg-panel lg:!backdrop-blur-none lg:shadow-[var(--shadow-1)] fixed lg:static bottom-0 inset-x-0 z-30 rounded-b-none lg:rounded-[var(--radius-lg)] pb-[max(1rem,env(safe-area-inset-bottom))]' : ''}`}>
            <h2 id="dec-h" className={`${cardTitle} flex items-center gap-1.5`}><UserCheck size={15} aria-hidden="true" /> Decizia operatorului</h2>
            {decided ? (
              <div className="text-sm">
                <div className="flex items-center gap-2">
                  {alert.status === 'rejected' ? <XCircle size={18} className="text-text-secondary" aria-hidden="true" /> : <CheckCircle2 size={18} className="text-ok" aria-hidden="true" />}
                  <span className="font-semibold">{alert.status === 'rejected' ? 'Alertă respinsă' : 'Alertă confirmată'}</span>
                </div>
                {(alert.decidedBy || alert.decidedAt) && (
                  <div className="text-text-secondary mt-1">{alert.decidedBy}{alert.decidedAt ? ` · ${fmtDateTime(alert.decidedAt)}` : ''}</div>
                )}
                {alert.decisionNote && <div className="text-text-secondary mt-1">Notă: {alert.decisionNote}</div>}
              </div>
            ) : canDecide ? (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-text-secondary">Urmăriți dovada și decideți. Sistemul nu aplică sancțiuni automat.</p>
                <div className="grid grid-cols-2 gap-2 [&>button]:min-h-12 [&>button]:text-base">
                  <Button variant={choice === 'confirm' ? 'confirm' : 'secondary'} aria-pressed={choice === 'confirm'} onClick={() => setChoice('confirm')}>Confirmă</Button>
                  <Button variant={choice === 'reject' ? 'danger' : 'reject'} aria-pressed={choice === 'reject'} onClick={() => setChoice('reject')}>Respinge</Button>
                </div>
                {choice === 'confirm' && actionKeys.length > 0 && (
                  <Field label="Acțiune">
                    {(a) => (
                      <select {...a} value={action} onChange={(e) => setAction(e.target.value)} className="w-full bg-void/60 border border-border rounded-lg px-3 min-h-[max(40px,var(--target-min))] text-sm">
                        {actionKeys.map((k) => <option key={k} value={k}>{actions[k]}</option>)}
                      </select>
                    )}
                  </Field>
                )}
                {choice && (
                  <Field label={noteRequired ? 'Motiv (obligatoriu)' : 'Notă (opțional)'} hint="Se păstrează în jurnalul de audit.">
                    {(a) => <TextArea {...a} rows={3} value={note} onChange={(e) => setNote(e.target.value)} />}
                  </Field>
                )}
                {choice && (
                  <Button variant={choice === 'reject' ? 'danger' : 'primary'} disabled={noteMissing} onClick={() => { setErr(null); setAsking(true) }}>
                    {choice === 'confirm' ? 'Continuă: confirmă alerta' : 'Continuă: respinge alerta'}
                  </Button>
                )}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">Rolul dumneavoastră nu permite clasificarea alertelor.</p>
            )}
          </section>

          <section aria-labelledby="ctx-h" className={card}>
            <h2 id="ctx-h" className={cardTitle}>Context</h2>
            <dl className="grid grid-cols-3 gap-y-2 text-sm">
              <dt className="text-text-secondary">Cameră</dt>
              <dd className="col-span-2 font-medium">{cam?.name || alert.cameraId}</dd>
              <dt className="text-text-secondary">Locație</dt>
              <dd className="col-span-2">{cam?.road || '—'}</dd>
              <dt className="text-text-secondary">Regulă</dt>
              <dd className="col-span-2">{alert.ruleSummary || rule?.name || '—'}</dd>
              {alert.metrics.speedKmh !== undefined && (
                <>
                  <dt className="text-text-secondary">Viteză estimată</dt>
                  <dd className="col-span-2">
                    ~{Math.round(alert.metrics.speedKmh)} km/h{alert.metrics.speedLimitKmh ? ` (prag ${alert.metrics.speedLimitKmh})` : ''}
                    {alert.metrics.speedApprox && <span className="ml-2 text-xs text-caution" title="Calibrare nevalidată față de o viteză de referință">orientativ</span>}
                  </dd>
                </>
              )}
              {alert.metrics.lowConfidence && (
                <>
                  <dt className="text-text-secondary">Încredere</dt>
                  <dd className="col-span-2 text-caution">Redusă: calculată din cadre rare (flux lent)</dd>
                </>
              )}
              {alert.metrics.vehicleClass && (
                <>
                  <dt className="text-text-secondary">Obiect</dt>
                  <dd className="col-span-2 capitalize">{alert.metrics.vehicleClass}</dd>
                </>
              )}
            </dl>
          </section>

          {alert.detection && (
            <section aria-labelledby="detection-h" className={card}>
              <h2 id="detection-h" className={cardTitle}>Detecție automată</h2>
              <dl className="grid grid-cols-3 gap-y-2 text-sm">
                {alert.detection.trackId != null && <><dt className="text-text-secondary">Track ByteTrack</dt><dd className="col-span-2 font-mono">#{alert.detection.trackId}</dd></>}
                {alert.detection.sourceTimeSec != null && <><dt className="text-text-secondary">Timp în sursă</dt><dd className="col-span-2 font-mono">{alert.detection.sourceTimeSec.toFixed(3)} s</dd></>}
                {alert.detection.confidence != null && <><dt className="text-text-secondary">Încredere YOLO</dt><dd className="col-span-2">{(alert.detection.confidence * 100).toFixed(1)}%</dd></>}
                {alert.detection.modelId && <><dt className="text-text-secondary">Model</dt><dd className="col-span-2">{alert.detection.modelId}{alert.detection.modelSha256 ? ` · SHA-256 ${alert.detection.modelSha256}` : ''}</dd></>}
                {alert.detection.sourceProvenance && (
                  <>
                    <dt className="text-text-secondary">Sursă video</dt>
                    <dd className="col-span-2 break-words">
                      {alert.detection.sourceProvenance.title || 'Înregistrare autorizată'}
                      {alert.detection.sourceProvenance.author && <span> · {alert.detection.sourceProvenance.author}</span>}
                      {alert.detection.sourceProvenance.license && <span> · {alert.detection.sourceProvenance.license}</span>}
                      {trustedSourceUrl(alert.detection.sourceProvenance.url) && (
                        <a className="block text-action underline underline-offset-2" href={trustedSourceUrl(alert.detection.sourceProvenance.url)} target="_blank" rel="noopener noreferrer">Deschide atribuirea sursei</a>
                      )}
                      {alert.detection.sourceProvenance.sha256 && <span className="block mt-1 font-mono text-[0.68rem] text-text-muted break-all">SHA-256 {alert.detection.sourceProvenance.sha256}</span>}
                    </dd>
                  </>
                )}
              </dl>
            </section>
          )}

          <section aria-labelledby="hist-h" className={card}>
            <h2 id="hist-h" className={cardTitle}>Istoric ({TZ})</h2>
            <ol className="stagger relative border-l-2 border-border-subtle ml-1.5 space-y-4">
              {timeline.map((step, idx) => (
                <li key={idx} className="pl-4 relative">
                  <span className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-panel border-2 border-action shadow-[var(--glow-signal)]" aria-hidden="true" />
                  <div className="font-mono text-xs text-text-secondary tabular-nums">{fmtDateTime(step.at)}</div>
                  <div className="text-sm">{step.label}</div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>

      {!USE_MOCKS && <CaseInvestigationWorkspace number={id} />}

      <ConfirmDialog
        open={asking}
        title={choice === 'confirm' ? 'Confirmi alerta?' : 'Respingi alerta?'}
        description={
          <>
            <p>Alerta #{alert.id} ({typeLabel}) va fi marcată {choice === 'confirm' ? 'confirmată' : 'respinsă'} și decizia se înregistrează în jurnalul de audit. Decizia nu poate fi anulată din această interfață.</p>
            {choice === 'confirm' && action && actions[action] && <p className="mt-2">Acțiune: {actions[action]}</p>}
            {note.trim() && <p className="mt-2">Notă: {note.trim()}</p>}
          </>
        }
        confirmLabel={choice === 'confirm' ? 'Confirmă alerta' : 'Respinge alerta'}
        tone={choice === 'reject' ? 'danger' : 'primary'}
        busy={saving}
        error={err}
        onConfirm={() => void submit()}
        onCancel={() => setAsking(false)}
      />
    </div>
  )
}
