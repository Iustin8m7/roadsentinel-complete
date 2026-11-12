import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react'
import { AlertTriangle, CheckCircle2, MousePointer2, Plus, Redo2, RotateCcw, Trash2, Undo2, X } from 'lucide-react'
import { Button } from '@/components/ui'
import { createDraft, validateDraft, versionAction, type ConfigError } from '@/lib/cameraControl'
import {
  ACQUISITION_INFO, centroid, clamp, clientToFrame, defaultConfig, errorTarget, GATE_TEXT, getCatalog, History, localProblems,
  RULE_LABEL, ruleGates, THRESHOLD_INFO, unitDirection, ZONE_KIND_LABEL, zoneId,
  type CameraConfig, type Catalog, type Frame, type Pt, type Zone,
} from '@/lib/cameraConfig'

/** The picture the shapes are drawn on. `note` says where it comes from; it is shown as it is. */
export interface Backdrop { kind: 'video' | 'image'; src: string; note: string }
type Selection = { type: 'zone'; index: number; vertex?: number } | { type: 'calibration'; vertex?: number } | { type: 'limit' } | null
type Drag =
  | { kind: 'zone-vertex'; zone: number; vertex: number } | { kind: 'zone-move'; zone: number; from: Pt; polygon: Pt[] }
  | { kind: 'zone-direction'; zone: number } | { kind: 'cal-vertex'; vertex: number } | { kind: 'limit' }
type Tab = 'zones' | 'calibration' | 'rules' | 'thresholds'
const TABS: [Tab, string][] = [['zones', 'Zone'], ['calibration', 'Calibrare'], ['rules', 'Reguli'], ['thresholds', 'Praguri']]
const ZONE_COLOR: Record<string, string> = { carriageway: '#3DA5FF', emergency_lane: '#FF5C7A' }
const input = 'bg-elevation border border-border rounded px-1.5 py-1 text-xs text-text-primary font-mono w-full disabled:opacity-50'
const num = (text: string) => (text.trim() === '' || Number.isNaN(Number(text)) ? null : Number(text))

interface Props {
  cameraId: string
  cameraName: string
  /** Config to start from (the active or the newest version); null for a camera that has none. */
  base: CameraConfig | null
  /** Frame size the worker reports for the source, when it has reported one. */
  workerFrame: Frame | null
  backdrop: Backdrop | null
  modelId: string
  onClose: () => void
  onSaved: (message: string) => void
}

/** Visual editor for a camera's zones, directions, calibration, rules and thresholds. It produces a
 *  schema v1 config and saves it as a new draft version; approval and activation stay in the panel. */
export function ConfigEditor({ cameraId, cameraName, base, workerFrame, backdrop, modelId, onClose, onSaved }: Props) {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [config, setConfig] = useState<CameraConfig | null>(null)
  const history = useRef<History<CameraConfig> | null>(null)
  const [, bump] = useState(0) // re-render after undo / redo availability changes
  const [selection, setSelection] = useState<Selection>(null)
  const [drawing, setDrawing] = useState<Pt[] | null>(null)
  const [tab, setTab] = useState<Tab>('zones')
  const [serverErrors, setServerErrors] = useState<ConfigError[] | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const [unit, setUnit] = useState(2) // reference-frame pixels per CSS pixel, for handle sizes
  const [mediaSize, setMediaSize] = useState<Frame | null>(null)
  const [typedFrame, setTypedFrame] = useState<Frame | null>(null)
  const [typing, setTyping] = useState({ width: '', height: '' })
  const svgRef = useRef<SVGSVGElement>(null)
  const drag = useRef<Drag | null>(null)
  const dragEnded = useRef(false) // the click that ends a drag lands on the stage and must not deselect

  useEffect(() => {
    getCatalog().then(setCatalog).catch((e: Error) => setLoadError(e.message))
  }, [])
  // The starting config needs the catalogue and, for a camera without one, a real frame size.
  const startFrame = base?.reference_frame ?? workerFrame ?? mediaSize ?? typedFrame
  useEffect(() => {
    if (config || !catalog || !startFrame) return
    const start = base ? structuredClone(base) : defaultConfig(startFrame, catalog, modelId)
    history.current = new History(start)
    setConfig(start)
  }, [base, catalog, config, modelId, startFrame])

  const frame: Frame | null = config?.reference_frame ?? null
  useEffect(() => {
    const svg = svgRef.current
    if (!svg || !frame) return
    const measure = () => { const w = svg.getBoundingClientRect().width; if (w > 0) setUnit(frame.width / w) }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(svg)
    return () => observer.disconnect()
  }, [frame?.width, frame?.height]) // size only: a new config object with the same frame must not re-attach the observer

  const local = useMemo(() => (config && catalog ? localProblems(config, catalog) : []), [config, catalog])
  const problems = useMemo(() => {
    const seen = new Set(local.map((e) => `${e.path}|${e.code}`))
    return [...local, ...(serverErrors ?? []).filter((e) => !seen.has(`${e.path}|${e.code}`))]
  }, [local, serverErrors])
  const gates = useMemo(() => (config && catalog ? ruleGates(config, catalog) : {}), [config, catalog])
  const badZones = useMemo(() => new Set(problems.map((e) => errorTarget(e.path)).flatMap((t) => (t.kind === 'zone' ? [t.index] : []))), [problems])

  /** One finished edit: goes on the undo stack and clears the last server verdict. */
  function commit(next: CameraConfig) {
    history.current?.push(next)
    setConfig(next); setServerErrors(null); setNotice(null); bump((n) => n + 1)
  }
  const edit = (change: (draft: CameraConfig) => void) => { if (!config) return; const next = structuredClone(config); change(next); commit(next) }
  function step(direction: 'undo' | 'redo') {
    const value = direction === 'undo' ? history.current?.undo() : history.current?.redo()
    if (value) { setConfig(value); setServerErrors(null); setSelection(null); bump((n) => n + 1) }
  }
  function reset() {
    if (!catalog || !startFrame) return
    commit(base ? structuredClone(base) : defaultConfig(startFrame, catalog, modelId))
    setSelection(null); setDrawing(null)
  }

  // ------------------------------------------------------------------------- pointer work
  const pointAt = (e: { clientX: number; clientY: number }): Pt | null =>
    svgRef.current && frame ? clientToFrame(svgRef.current.getBoundingClientRect(), frame, e.clientX, e.clientY) : null
  function startDrag(e: ReactPointerEvent, d: Drag) {
    if (drawing) return
    e.stopPropagation(); e.preventDefault()
    svgRef.current?.setPointerCapture(e.pointerId)
    drag.current = d
  }
  function onPointerMove(e: ReactPointerEvent) {
    const d = drag.current, p = pointAt(e)
    if (!d || !p || !config || !frame) return
    const next = structuredClone(config)
    if (d.kind === 'zone-vertex') next.zones[d.zone].polygon[d.vertex] = p
    else if (d.kind === 'zone-move') {
      // Keep the whole shape inside the frame: clamp the shift, never the single points.
      const xs = d.polygon.map((q) => q[0]), ys = d.polygon.map((q) => q[1])
      const dx = clamp(p[0] - d.from[0], -Math.min(...xs), frame.width - Math.max(...xs))
      const dy = clamp(p[1] - d.from[1], -Math.min(...ys), frame.height - Math.max(...ys))
      next.zones[d.zone].polygon = d.polygon.map((q) => [q[0] + dx, q[1] + dy])
    } else if (d.kind === 'zone-direction') {
      const c = centroid(next.zones[d.zone].polygon)
      next.zones[d.zone].direction = unitDirection([p[0] - c[0], p[1] - c[1]]) ?? next.zones[d.zone].direction
    } else if (d.kind === 'cal-vertex' && next.calibration) next.calibration.source[d.vertex] = p
    else if (d.kind === 'limit') next.min_y = p[1]
    setConfig(next) // live preview; the undo stack gets one entry when the pointer is released
  }
  function onPointerUp(e: ReactPointerEvent) {
    if (!drag.current) return
    drag.current = null
    dragEnded.current = true
    window.setTimeout(() => { dragEnded.current = false }, 0)
    svgRef.current?.releasePointerCapture(e.pointerId)
    if (config && history.current && JSON.stringify(config) !== JSON.stringify(history.current.current)) commit(config)
  }
  function onStageClick(e: React.MouseEvent) {
    if (dragEnded.current) { dragEnded.current = false; return }
    if (!drawing) { setSelection(null); return }
    const p = pointAt(e)
    if (p) setDrawing([...drawing, p])
  }
  function finishDrawing() {
    if (!drawing || drawing.length < 3 || !config) return
    const name = `Zonă ${config.zones.length + 1}`
    const zone: Zone = { id: zoneId(name, config.zones.map((z) => z.id)), name, kind: 'carriageway', direction: [0, 1], polygon: drawing }
    edit((c) => { c.zones.push(zone) })
    setSelection({ type: 'zone', index: config.zones.length }); setDrawing(null); setTab('zones')
  }
  function addRectangle() {
    if (!config || !frame) return
    const w = Math.round(frame.width / 4), h = Math.round(frame.height / 4), x = Math.round(frame.width / 2 - w / 2), y = Math.round(frame.height / 2 - h / 2)
    const name = `Zonă ${config.zones.length + 1}`
    edit((c) => { c.zones.push({ id: zoneId(name, c.zones.map((z) => z.id)), name, kind: 'carriageway', direction: [0, 1], polygon: [[x, y], [x + w, y], [x + w, y + h], [x, y + h]] }) })
    setSelection({ type: 'zone', index: config.zones.length })
  }
  function vertexKey(e: ReactKeyboardEvent, move: (dx: number, dy: number) => void, remove?: () => void) {
    const stepSize = e.shiftKey ? 10 : 1
    const delta: Record<string, Pt> = { ArrowLeft: [-stepSize, 0], ArrowRight: [stepSize, 0], ArrowUp: [0, -stepSize], ArrowDown: [0, stepSize] }
    if (delta[e.key]) { e.preventDefault(); move(...delta[e.key]) }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && remove) { e.preventDefault(); remove() }
  }
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)
      if (e.key === 'Escape') { if (drawing) setDrawing(null); else onClose() }
      else if (e.key === 'Enter' && drawing && !typing) finishDrawing()
      else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z' && !typing) { e.preventDefault(); step(e.shiftKey ? 'redo' : 'undo') }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  // ------------------------------------------------------------------------- saving
  async function check() {
    if (!config) return null
    setBusy(true)
    try {
      const result = await validateDraft(cameraId, config)
      setServerErrors(result.errors)
      setNotice(result.errors.length ? { tone: 'bad', text: `Serverul a găsit ${result.errors.length} probleme.` } : { tone: 'ok', text: 'Serverul acceptă configurația.' })
      return result.errors
    } catch (error) {
      setNotice({ tone: 'bad', text: `Verificare: ${(error as Error).message}` })
      return null
    } finally { setBusy(false) }
  }
  async function save(submit: boolean) {
    if (!config) return
    const errors = await check()
    if (!errors || errors.length) return
    setBusy(true)
    try {
      const draft = await createDraft(cameraId, config, reason.trim())
      if (submit) {
        await versionAction(cameraId, draft.id, 'validate')
        await versionAction(cameraId, draft.id, 'submit')
      }
      onSaved(submit ? `Versiunea ${draft.revision} a fost trimisă spre aprobare. Un alt administrator trebuie să o aprobe.` : `Ciorna (versiunea ${draft.revision}) a fost salvată.`)
    } catch (error) {
      setNotice({ tone: 'bad', text: `Salvare: ${(error as Error).message}` })
    } finally { setBusy(false) }
  }
  function goTo(e: ConfigError) {
    const t = errorTarget(e.path)
    if (t.kind === 'zone') { setTab('zones'); setSelection({ type: 'zone', index: t.index, vertex: t.vertex }) }
    else if (t.kind === 'calibration') { setTab('calibration'); setSelection({ type: 'calibration', vertex: t.vertex }) }
    else if (t.kind === 'limit') { setTab('calibration'); setSelection({ type: 'limit' }) }
    else if (t.kind === 'rule') setTab('rules')
    else setTab('thresholds')
  }

  const selectedZone = selection?.type === 'zone' ? config?.zones[selection.index] : undefined
  const r = 7 * unit // handle radius in frame pixels
  const aspectOff = !!(frame && mediaSize && Math.abs(mediaSize.width / mediaSize.height - frame.width / frame.height) > 0.01)
  const hasShapes = !!config && (config.zones.length > 0 || !!config.calibration)
  const saveBlocked = busy || !config || problems.length > 0 || reason.trim().length < 3 || !!drawing

  return (
    <div className="fixed inset-0 z-[60] bg-void flex flex-col" role="dialog" aria-modal="true" aria-label={`Editor configurație ${cameraName}`} data-testid="config-editor">
      <header className="flex items-center justify-between gap-3 px-4 py-2 border-b border-border">
        <div className="min-w-0">
          <h2 className="font-heading text-lg font-bold text-text-primary truncate">Configurație: {cameraName}</h2>
          <p className="text-[11px] text-text-secondary">
            {frame ? `Cadru de referință ${frame.width}×${frame.height} px. Coordonatele se salvează în pixelii acestui cadru.` : 'Se încarcă…'}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Button size="sm" variant="ghost" disabled={!history.current?.canUndo} onClick={() => step('undo')} aria-label="Anulează ultima modificare"><Undo2 className="w-4 h-4" /></Button>
          <Button size="sm" variant="ghost" disabled={!history.current?.canRedo} onClick={() => step('redo')} aria-label="Refă modificarea"><Redo2 className="w-4 h-4" /></Button>
          <Button size="sm" variant="ghost" onClick={reset} aria-label="Revino la configurația de pornire"><RotateCcw className="w-4 h-4" /></Button>
          <button type="button" onClick={onClose} className="p-1.5 rounded hover:bg-elevation" aria-label="Închide editorul"><X className="w-5 h-5" /></button>
        </div>
      </header>

      {loadError && <div role="alert" className="m-4 rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">Editorul nu a putut porni: {loadError}</div>}
      {!loadError && !config && (
        <div className="m-4 text-sm text-text-secondary" data-testid="editor-waiting">
          {catalog && !startFrame ? (
            <form className="flex flex-col gap-2 max-w-md" data-testid="frame-form" onSubmit={(e) => {
              e.preventDefault()
              setTypedFrame({ width: Number(typing.width), height: Number(typing.height) })
            }}>
              <p>Camera nu are încă nici configurație, nici un cadru real (de la un worker sau dintr-o înregistrare). Zonele se desenează în pixelii imaginii, deci introduceți rezoluția reală a camerei.</p>
              <div className="flex items-end gap-2">
                <label className="flex flex-col gap-1 text-xs">Lățime (px)
                  <input className={input} type="number" min={catalog.limits.frame_min} max={catalog.limits.frame_max} required value={typing.width} onChange={(e) => setTyping({ ...typing, width: e.target.value })} data-testid="frame-width" />
                </label>
                <label className="flex flex-col gap-1 text-xs">Înălțime (px)
                  <input className={input} type="number" min={catalog.limits.frame_min} max={catalog.limits.frame_max} required value={typing.height} onChange={(e) => setTyping({ ...typing, height: e.target.value })} data-testid="frame-height" />
                </label>
                <Button size="sm" type="submit" variant="secondary" data-testid="frame-start">Începe</Button>
              </div>
              <p className="text-xs text-amber-300">Dacă rezoluția nu este cea reală, worker-ul va refuza configurația (cadru diferit) și nimic nu va rula.</p>
            </form>
          ) : 'Se încarcă…'}
        </div>
      )}

      {config && catalog && frame && (
        <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
          <div className="flex-1 min-w-0 min-h-0 p-3 flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {drawing ? (
                <>
                  <span className="text-amber-300" role="status">Desenați zona: clic pentru fiecare colț ({drawing.length} puncte). Enter sau clic pe primul punct închide zona.</span>
                  <Button size="sm" disabled={drawing.length < 3} onClick={finishDrawing}>Închide zona</Button>
                  <Button size="sm" variant="ghost" onClick={() => setDrawing(null)}>Renunță</Button>
                </>
              ) : (
                <>
                  <Button size="sm" variant="secondary" onClick={() => { setDrawing([]); setSelection(null) }} data-testid="draw-zone"><MousePointer2 className="w-3.5 h-3.5" />Desenează o zonă</Button>
                  <Button size="sm" variant="ghost" onClick={addRectangle} data-testid="add-rectangle"><Plus className="w-3.5 h-3.5" />Zonă dreptunghi (fără mouse)</Button>
                  <span className="text-text-secondary">Trageți de colțuri; săgețile mută punctul selectat cu 1 px (Shift: 10 px).</span>
                </>
              )}
            </div>
            <div className="flex-1 min-h-0 flex items-start justify-center overflow-hidden">
              <div className="relative bg-black border border-border rounded" style={{ aspectRatio: `${frame.width} / ${frame.height}`, width: `min(100%, calc((100vh - 190px) * ${frame.width / frame.height}))` }}>
                {backdrop?.kind === 'video' && (
                  <video src={`${backdrop.src}#t=3`} muted playsInline preload="metadata" className="absolute inset-0 w-full h-full object-fill"
                    onLoadedMetadata={(e) => setMediaSize({ width: e.currentTarget.videoWidth, height: e.currentTarget.videoHeight })} />
                )}
                {backdrop?.kind === 'image' && (
                  <img src={backdrop.src} alt="" className="absolute inset-0 w-full h-full object-fill"
                    onLoad={(e) => setMediaSize({ width: e.currentTarget.naturalWidth, height: e.currentTarget.naturalHeight })} />
                )}
                {!backdrop && <div className="absolute inset-0 flex items-center justify-center text-xs text-text-secondary p-6 text-center">Niciun cadru real disponibil pentru această cameră. Punctele pot fi introduse numeric, dar verificați-le pe o imagine reală înainte de aprobare.</div>}
                <svg ref={svgRef} viewBox={`0 0 ${frame.width} ${frame.height}`} preserveAspectRatio="none" data-testid="editor-stage"
                  className={`absolute inset-0 w-full h-full touch-none ${drawing ? 'cursor-crosshair' : ''}`}
                  onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} onClick={onStageClick}>
                  {config.min_y != null && (
                    <g>
                      <rect x={0} y={0} width={frame.width} height={config.min_y} fill="#000" opacity={0.35} pointerEvents="none" />
                      <line x1={0} x2={frame.width} y1={config.min_y} y2={config.min_y} stroke="#FFD400" strokeWidth={2} strokeDasharray="8 6" vectorEffect="non-scaling-stroke" pointerEvents="none" />
                      <line x1={0} x2={frame.width} y1={config.min_y} y2={config.min_y} stroke="transparent" strokeWidth={14 * unit} className="cursor-row-resize"
                        onPointerDown={(e) => { setSelection({ type: 'limit' }); startDrag(e, { kind: 'limit' }) }} onClick={(e) => e.stopPropagation()} />
                    </g>
                  )}
                  {config.zones.map((zone, i) => {
                    const color = badZones.has(i) ? '#FF4D4D' : ZONE_COLOR[zone.kind] ?? '#3DA5FF'
                    const selected = selection?.type === 'zone' && selection.index === i
                    const c = centroid(zone.polygon)
                    const tip: Pt | null = zone.direction ? [c[0] + zone.direction[0] * 70 * unit, c[1] + zone.direction[1] * 70 * unit] : null
                    return (
                      <g key={i} data-testid={`zone-shape-${i}`}>
                        <polygon points={zone.polygon.map((p) => p.join(',')).join(' ')} fill={color} fillOpacity={selected ? 0.28 : 0.14} stroke={color} strokeWidth={selected ? 3 : 2}
                          strokeDasharray={badZones.has(i) ? '6 4' : undefined} vectorEffect="non-scaling-stroke" className={drawing ? '' : 'cursor-move'}
                          onPointerDown={(e) => { const p = pointAt(e); if (!p) return; setSelection({ type: 'zone', index: i }); setTab('zones'); startDrag(e, { kind: 'zone-move', zone: i, from: p, polygon: zone.polygon }) }}
                          onClick={(e) => { if (!drawing) e.stopPropagation() }} />
                        <text x={c[0]} y={c[1] - 12 * unit} fontSize={13 * unit} fill="#fff" stroke="#000" strokeWidth={3 * unit} paintOrder="stroke" textAnchor="middle" pointerEvents="none">{zone.name}</text>
                        {tip && (
                          <g>
                            <line x1={c[0]} y1={c[1]} x2={tip[0]} y2={tip[1]} stroke="#fff" strokeWidth={3} vectorEffect="non-scaling-stroke" pointerEvents="none" />
                            <circle cx={tip[0]} cy={tip[1]} r={r} fill="#fff" stroke="#000" strokeWidth={1.5} vectorEffect="non-scaling-stroke" className="cursor-grab"
                              role="img" aria-label={`Sensul de mers al zonei ${zone.name}`}
                              onPointerDown={(e) => { setSelection({ type: 'zone', index: i }); startDrag(e, { kind: 'zone-direction', zone: i }) }} onClick={(e) => e.stopPropagation()} />
                          </g>
                        )}
                        {selected && zone.polygon.map((p, j) => {
                          const q = zone.polygon[(j + 1) % zone.polygon.length]
                          return (
                            <rect key={`m${j}`} x={(p[0] + q[0]) / 2 - r * 0.6} y={(p[1] + q[1]) / 2 - r * 0.6} width={r * 1.2} height={r * 1.2} fill="#0A0E14" stroke={color} strokeWidth={1.5}
                              vectorEffect="non-scaling-stroke" className="cursor-copy" role="button" aria-label={`Adaugă un punct după punctul ${j + 1}`}
                              onPointerDown={(e) => e.stopPropagation()}
                              onClick={(e) => { e.stopPropagation(); edit((d) => { d.zones[i].polygon.splice(j + 1, 0, [Math.round((p[0] + q[0]) / 2), Math.round((p[1] + q[1]) / 2)]) }); setSelection({ type: 'zone', index: i, vertex: j + 1 }) }} />
                          )
                        })}
                        {selected && zone.polygon.map((p, j) => (
                          <circle key={`v${j}`} cx={p[0]} cy={p[1]} r={selection.vertex === j ? r * 1.25 : r} fill={selection.vertex === j ? '#fff' : color} stroke="#000" strokeWidth={1.5} vectorEffect="non-scaling-stroke"
                            className="cursor-grab outline-none" tabIndex={0} role="button" data-testid={`zone-${i}-vertex-${j}`}
                            aria-label={`${zone.name}, punctul ${j + 1}: x ${p[0]}, y ${p[1]}. Săgețile îl mută, Delete îl șterge.`}
                            onFocus={() => setSelection({ type: 'zone', index: i, vertex: j })}
                            onPointerDown={(e) => { setSelection({ type: 'zone', index: i, vertex: j }); startDrag(e, { kind: 'zone-vertex', zone: i, vertex: j }) }}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => vertexKey(e,
                              (dx, dy) => edit((d) => { d.zones[i].polygon[j] = [clamp(p[0] + dx, 0, frame.width), clamp(p[1] + dy, 0, frame.height)] }),
                              zone.polygon.length > 3 ? () => { edit((d) => { d.zones[i].polygon.splice(j, 1) }); setSelection({ type: 'zone', index: i }) } : undefined)} />
                        ))}
                      </g>
                    )
                  })}
                  {config.calibration && (
                    <g data-testid="calibration-shape">
                      <polygon points={config.calibration.source.map((p) => p.join(',')).join(' ')} fill="#FFD400" fillOpacity={0.08} stroke="#FFD400" strokeWidth={2} strokeDasharray="4 4" vectorEffect="non-scaling-stroke" pointerEvents="none" />
                      {config.calibration.source.map((p, j) => (
                        <g key={j}>
                          <circle cx={p[0]} cy={p[1]} r={r} fill="#FFD400" stroke="#000" strokeWidth={1.5} vectorEffect="non-scaling-stroke" className="cursor-grab outline-none" tabIndex={0} role="button"
                            data-testid={`calibration-vertex-${j}`} aria-label={`Calibrare, punctul ${j + 1}: x ${p[0]}, y ${p[1]}. Săgețile îl mută.`}
                            onFocus={() => { setSelection({ type: 'calibration', vertex: j }); setTab('calibration') }}
                            onPointerDown={(e) => { setSelection({ type: 'calibration', vertex: j }); setTab('calibration'); startDrag(e, { kind: 'cal-vertex', vertex: j }) }}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => vertexKey(e, (dx, dy) => edit((d) => { if (d.calibration) d.calibration.source[j] = [clamp(p[0] + dx, 0, frame.width), clamp(p[1] + dy, 0, frame.height)] }))} />
                          <text x={p[0] + r * 1.4} y={p[1] - r * 1.1} fontSize={14 * unit} fill="#FFD400" stroke="#000" strokeWidth={3 * unit} paintOrder="stroke" pointerEvents="none">{j + 1}</text>
                        </g>
                      ))}
                    </g>
                  )}
                  {drawing && drawing.length > 0 && (
                    <g>
                      <polyline points={drawing.map((p) => p.join(',')).join(' ')} fill="none" stroke="#FFD400" strokeWidth={2} vectorEffect="non-scaling-stroke" pointerEvents="none" />
                      {drawing.map((p, j) => (
                        <circle key={j} cx={p[0]} cy={p[1]} r={j === 0 ? r * 1.3 : r * 0.8} fill={j === 0 ? '#FFD400' : '#fff'} stroke="#000" strokeWidth={1.5} vectorEffect="non-scaling-stroke"
                          className={j === 0 ? 'cursor-pointer' : ''} pointerEvents={j === 0 ? 'auto' : 'none'}
                          onClick={(e) => { if (j === 0 && drawing.length >= 3) { e.stopPropagation(); finishDrawing() } }} />
                      ))}
                    </g>
                  )}
                </svg>
              </div>
            </div>
            <p className="text-[11px] text-text-secondary" data-testid="backdrop-note">
              {backdrop ? backdrop.note : 'Fără imagine de fundal.'}
              {aspectOff && <span className="text-amber-300"> Atenție: imaginea afișată are alt raport de aspect decât cadrul de referință, deci formele pot părea deplasate.</span>}
            </p>
          </div>

          <aside className="w-full lg:w-[400px] shrink-0 border-t lg:border-t-0 lg:border-l border-border flex flex-col min-h-0">
            <div className="flex border-b border-border" role="tablist">
              {TABS.map(([id, label]) => (
                <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} data-testid={`tab-${id}`}
                  className={`flex-1 px-2 py-2 text-xs font-semibold ${tab === id ? 'text-text-primary border-b-2 border-accent' : 'text-text-secondary hover:text-text-primary'}`}>{label}</button>
              ))}
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3 flex flex-col gap-3 text-xs text-text-primary">
              {tab === 'zones' && (
                <>
                  {config.zones.length === 0 && <p className="text-text-secondary">Nicio zonă încă. Desenați zona de carosabil pe imagine: regulile se aplică doar în zone.</p>}
                  <ul className="flex flex-col gap-1">
                    {config.zones.map((zone, i) => (
                      <li key={i}>
                        <button type="button" onClick={() => setSelection({ type: 'zone', index: i })} data-testid={`zone-row-${i}`}
                          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded border text-left ${selection?.type === 'zone' && selection.index === i ? 'border-accent bg-elevation' : 'border-border'}`}>
                          <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: ZONE_COLOR[zone.kind] ?? '#3DA5FF' }} />
                          <span className="truncate flex-1">{zone.name || '(fără nume)'}</span>
                          <span className="text-text-secondary">{ZONE_KIND_LABEL[zone.kind] ?? zone.kind} · {zone.polygon.length} puncte</span>
                          {badZones.has(i) && <AlertTriangle className="w-3.5 h-3.5 text-rose-400" aria-label="are probleme" />}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {selectedZone && selection?.type === 'zone' && (() => {
                    const i = selection.index
                    return (
                      <div className="flex flex-col gap-2 border-t border-border pt-2" data-testid="zone-form">
                        <label className="flex flex-col gap-1">Nume
                          <input className={input} value={selectedZone.name} onChange={(e) => edit((d) => { d.zones[i].name = e.target.value })} />
                        </label>
                        <label className="flex flex-col gap-1">Identificator (litere mici, cifre, „_”)
                          <input className={input} value={selectedZone.id} onChange={(e) => edit((d) => { d.zones[i].id = e.target.value })} />
                        </label>
                        <label className="flex flex-col gap-1">Tip
                          <select className={input} value={selectedZone.kind} onChange={(e) => edit((d) => { d.zones[i].kind = e.target.value })}>
                            {catalog.zone_kinds.map((k) => <option key={k} value={k}>{ZONE_KIND_LABEL[k] ?? k}</option>)}
                          </select>
                        </label>
                        <fieldset className="flex flex-col gap-1">
                          <legend>Sens de mers (în imagine: x spre dreapta, y în jos)</legend>
                          <div className="flex items-center gap-1.5">
                            {([['↑', [0, -1]], ['↓', [0, 1]], ['←', [-1, 0]], ['→', [1, 0]]] as [string, Pt][]).map(([label, v]) => (
                              <button key={label} type="button" className="px-2 py-1 rounded border border-border hover:border-accent" aria-label={`Sens ${label}`} onClick={() => edit((d) => { d.zones[i].direction = v })}>{label}</button>
                            ))}
                            <input className={input} aria-label="Sens, componenta x" type="number" step="0.01" value={selectedZone.direction?.[0] ?? ''} placeholder="x"
                              onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.zones[i].direction = [v, d.zones[i].direction?.[1] ?? 0] }) }} />
                            <input className={input} aria-label="Sens, componenta y" type="number" step="0.01" value={selectedZone.direction?.[1] ?? ''} placeholder="y"
                              onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.zones[i].direction = [d.zones[i].direction?.[0] ?? 0, v] }) }} />
                          </div>
                          {selectedZone.kind !== 'carriageway' && selectedZone.direction != null && (
                            <button type="button" className="self-start text-text-secondary underline" onClick={() => edit((d) => { d.zones[i].direction = null })}>Fără sens de mers</button>
                          )}
                        </fieldset>
                        <div>
                          <div className="mb-1">Puncte (pixeli în cadrul de referință)</div>
                          <ol className="flex flex-col gap-1">
                            {selectedZone.polygon.map((p, j) => (
                              <li key={j} className={`flex items-center gap-1.5 ${selection.vertex === j ? 'text-accent' : ''}`}>
                                <span className="w-5 text-right text-text-secondary">{j + 1}</span>
                                <input className={input} type="number" aria-label={`Punctul ${j + 1}, x`} value={p[0]} min={0} max={frame.width}
                                  onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.zones[i].polygon[j][0] = Math.round(v) }) }} />
                                <input className={input} type="number" aria-label={`Punctul ${j + 1}, y`} value={p[1]} min={0} max={frame.height}
                                  onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.zones[i].polygon[j][1] = Math.round(v) }) }} />
                                <button type="button" disabled={selectedZone.polygon.length <= 3} className="p-1 rounded hover:bg-elevation disabled:opacity-30" aria-label={`Șterge punctul ${j + 1}`}
                                  onClick={() => { edit((d) => { d.zones[i].polygon.splice(j, 1) }); setSelection({ type: 'zone', index: i }) }}><Trash2 className="w-3.5 h-3.5" /></button>
                              </li>
                            ))}
                          </ol>
                        </div>
                        <Button size="sm" variant="reject" onClick={() => { edit((d) => { d.zones.splice(i, 1) }); setSelection(null) }} data-testid="delete-zone">Șterge zona</Button>
                      </div>
                    )
                  })()}
                </>
              )}

              {tab === 'calibration' && (
                <>
                  <label className="flex items-start gap-2">
                    <input type="checkbox" checked={!!config.calibration} data-testid="calibration-toggle" onChange={(e) => edit((d) => {
                      const w = frame.width, h = frame.height
                      d.calibration = e.target.checked ? { source: [[Math.round(w * 0.35), Math.round(h * 0.45)], [Math.round(w * 0.65), Math.round(h * 0.45)], [Math.round(w * 0.8), Math.round(h * 0.85)], [Math.round(w * 0.2), Math.round(h * 0.85)]], target_width_m: 7, target_length_m: 20 } : null
                    })} />
                    <span>Calibrare pixel–metru. Fără ea, regulile care au nevoie de viteză sau distanță rămân oprite.</span>
                  </label>
                  {config.calibration && (
                    <>
                      <p className="text-text-secondary">Așezați cele patru puncte pe colțurile unui dreptunghi de pe asfalt pe care îl puteți măsura. De la punctul 1 la 2 este lățimea, de la 2 la 3 lungimea. Valorile de mai jos sunt doar un punct de pornire: măsurați-le.</p>
                      <ol className="flex flex-col gap-1">
                        {config.calibration.source.map((p, j) => (
                          <li key={j} className="flex items-center gap-1.5">
                            <span className="w-5 text-right text-text-secondary">{j + 1}</span>
                            <input className={input} type="number" aria-label={`Calibrare, punctul ${j + 1}, x`} value={p[0]} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { if (d.calibration) d.calibration.source[j][0] = Math.round(v) }) }} />
                            <input className={input} type="number" aria-label={`Calibrare, punctul ${j + 1}, y`} value={p[1]} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { if (d.calibration) d.calibration.source[j][1] = Math.round(v) }) }} />
                          </li>
                        ))}
                      </ol>
                      <label className="flex flex-col gap-1">Lățime reală între punctele 1 și 2 (m)
                        <input className={input} type="number" step="0.1" value={config.calibration.target_width_m} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { if (d.calibration) d.calibration.target_width_m = v }) }} />
                      </label>
                      <label className="flex flex-col gap-1">Lungime reală între punctele 2 și 3 (m)
                        <input className={input} type="number" step="0.1" value={config.calibration.target_length_m} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { if (d.calibration) d.calibration.target_length_m = v }) }} />
                      </label>
                      <p className="text-amber-300">Vitezele rezultate sunt estimări pentru triere, nu măsurători.</p>
                    </>
                  )}
                  <div className="border-t border-border pt-2 flex flex-col gap-2">
                    <label className="flex items-start gap-2">
                      <input type="checkbox" checked={config.min_y != null} onChange={(e) => edit((d) => { d.min_y = e.target.checked ? Math.round(frame.height / 3) : null })} />
                      <span>Ignoră tot ce este deasupra unei linii (prea departe de cameră pentru o măsurare corectă).</span>
                    </label>
                    {config.min_y != null && (
                      <label className="flex flex-col gap-1">Poziția liniei, y (px)
                        <input className={input} type="number" min={0} max={frame.height} value={config.min_y} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.min_y = Math.round(v) }) }} />
                      </label>
                    )}
                  </div>
                </>
              )}

              {tab === 'rules' && (
                <ul className="flex flex-col gap-2">
                  {catalog.rules.map((spec) => {
                    const on = config.rules.includes(spec.id), missing = gates[spec.id] ?? []
                    const needs = [spec.needs_calibration && 'calibrare', spec.zone_kinds.length > 0 && `zonă: ${spec.zone_kinds.map((k) => ZONE_KIND_LABEL[k] ?? k).join(' sau ')}`, spec.needs_direction && 'sens de mers', `cel puțin ${spec.min_fps} cadre/s`].filter(Boolean).join(' · ')
                    return (
                      <li key={spec.id} className="rounded border border-border p-2" data-testid={`rule-${spec.id}`}>
                        <label className="flex items-start gap-2">
                          <input type="checkbox" checked={on} disabled={!on && missing.length > 0} aria-describedby={`rule-${spec.id}-needs`}
                            onChange={(e) => edit((d) => { d.rules = e.target.checked ? [...d.rules, spec.id] : d.rules.filter((x) => x !== spec.id) })} />
                          <span className="flex-1">
                            <span className="font-semibold">{RULE_LABEL[spec.id] ?? spec.id}</span>
                            <span id={`rule-${spec.id}-needs`} className="block text-text-secondary">Are nevoie de: {needs}</span>
                            {missing.length > 0 && <span className="block text-amber-300" data-testid={`rule-${spec.id}-blocked`}>{on ? 'Nu poate rula' : 'Indisponibilă'}: {missing.map((m) => GATE_TEXT[m] ?? m).join('; ')}.</span>}
                          </span>
                        </label>
                      </li>
                    )
                  })}
                </ul>
              )}

              {tab === 'thresholds' && (
                <>
                  {catalog.thresholds.map((b) => {
                    const info = THRESHOLD_INFO[b.id] ?? { label: b.id, unit: '' }, value = config.thresholds[b.id]
                    const bad = problems.some((e) => e.path === `thresholds.${b.id}`)
                    return (
                      <label key={b.id} className="flex flex-col gap-1">
                        <span className="flex items-center gap-2">
                          {!b.required && <input type="checkbox" checked={value !== undefined} aria-label={`Folosește: ${info.label}`} onChange={(e) => edit((d) => { if (e.target.checked) d.thresholds[b.id] = b.min; else delete d.thresholds[b.id] })} />}
                          {info.label}{info.unit && ` (${info.unit})`} <span className="text-text-secondary">{b.min}–{b.max}</span>
                        </span>
                        <input className={`${input} ${bad ? 'border-rose-500' : ''}`} type="number" step={b.integer ? 1 : 0.1} min={b.min} max={b.max} disabled={value === undefined} data-testid={`threshold-${b.id}`}
                          value={typeof value === 'number' ? value : ''} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.thresholds[b.id] = v }) }} />
                      </label>
                    )
                  })}
                  <fieldset className="flex flex-col gap-1">
                    <legend>Clase ignorate la „accident probabil” (de exemplu autobuzele, care opresc brusc în stații)</legend>
                    <div className="flex flex-wrap gap-3">
                      {catalog.vehicle_classes.map((cls) => {
                        const list = Array.isArray(config.thresholds.crash_ignore_classes) ? config.thresholds.crash_ignore_classes : []
                        return (
                          <label key={cls} className="flex items-center gap-1">
                            <input type="checkbox" checked={list.includes(cls)} onChange={(e) => edit((d) => {
                              const next = e.target.checked ? [...list, cls] : list.filter((x) => x !== cls)
                              if (next.length) d.thresholds.crash_ignore_classes = next; else delete d.thresholds.crash_ignore_classes
                            })} />{cls}
                          </label>
                        )
                      })}
                    </div>
                  </fieldset>
                  <div className="border-t border-border pt-2 flex flex-col gap-2">
                    {catalog.acquisition.map((b) => {
                      const info = ACQUISITION_INFO[b.id] ?? { label: b.id, unit: '' }
                      return (
                        <label key={b.id} className="flex flex-col gap-1">{info.label}{info.unit && ` (${info.unit})`} <span className="text-text-secondary">{b.min}–{b.max}</span>
                          <input className={input} type="number" step={b.integer ? 1 : 0.5} min={b.min} max={b.max} value={config.acquisition[b.id] ?? ''} data-testid={`acquisition-${b.id}`}
                            onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.acquisition[b.id] = v }) }} />
                        </label>
                      )
                    })}
                    <label className="flex flex-col gap-1">Model de detecție (referință pe mașina de procesare)
                      <input className={input} value={config.model.id} onChange={(e) => edit((d) => { d.model = { id: e.target.value } })} />
                    </label>
                    <div className="flex items-end gap-1.5">
                      <label className="flex flex-col gap-1 flex-1">Cadru de referință, lățime (px)
                        <input className={input} type="number" disabled={hasShapes} value={frame.width} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.reference_frame.width = Math.round(v) }) }} />
                      </label>
                      <label className="flex flex-col gap-1 flex-1">înălțime (px)
                        <input className={input} type="number" disabled={hasShapes} value={frame.height} onChange={(e) => { const v = num(e.target.value); if (v != null) edit((d) => { d.reference_frame.height = Math.round(v) }) }} />
                      </label>
                    </div>
                    <p className="text-text-secondary">{hasShapes ? 'Cadrul de referință nu se poate schimba cât timp există zone sau calibrare: coordonatele lor s-ar referi la altă imagine.' : 'Trebuie să fie rezoluția reală a camerei.'}</p>
                  </div>
                </>
              )}
            </div>

            <div className="border-t border-border p-3 flex flex-col gap-2 text-xs">
              {problems.length === 0
                ? <p className="text-emerald-300 flex items-center gap-1" data-testid="editor-ok"><CheckCircle2 className="w-3.5 h-3.5" />Nicio problemă găsită{serverErrors ? ' (verificat și pe server)' : ' local; serverul verifică la salvare'}.</p>
                : (
                  <div data-testid="editor-problems">
                    <p className="text-amber-300 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" />{problems.length} {problems.length === 1 ? 'problemă' : 'probleme'} de rezolvat înainte de salvare:</p>
                    <ul className="max-h-28 overflow-y-auto mt-1 flex flex-col gap-0.5">
                      {problems.map((e, i) => (
                        <li key={i}><button type="button" className="text-left text-amber-200 hover:underline" onClick={() => goTo(e)}><span className="font-mono text-text-secondary">{e.path || 'configurație'}</span>: {e.message}</button></li>
                      ))}
                    </ul>
                  </div>
                )}
              {notice && <p role="status" className={notice.tone === 'ok' ? 'text-emerald-300' : 'text-rose-300'} data-testid="editor-notice">{notice.text}</p>}
              <label className="flex flex-col gap-1">Motivul modificării (intră în jurnalul de audit)
                <input className={input} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} data-testid="editor-reason" />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" disabled={busy || !!drawing} onClick={() => void check()} data-testid="editor-check">Verifică pe server</Button>
                <Button size="sm" variant="secondary" disabled={saveBlocked} onClick={() => void save(false)} data-testid="editor-save">Salvează ciorna</Button>
                <Button size="sm" variant="confirm" disabled={saveBlocked} onClick={() => void save(true)} data-testid="editor-submit">Salvează și trimite spre aprobare</Button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
