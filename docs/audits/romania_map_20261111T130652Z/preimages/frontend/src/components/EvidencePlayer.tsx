import type { KeyboardEvent as RKeyboardEvent, ReactNode } from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { getClip, cachedClip, unsubscribeClip, evictClip } from '@/lib/demo'
import { AlertTriangle, ChevronLeft, ChevronRight, Download, Loader2, Maximize2, Pause, Play, RotateCcw, RotateCw, Crosshair } from 'lucide-react'

const SPEEDS = [1, 0.5, 0.25, 2]
const DEFAULT_SPEED = 1 // Encoded media chronology is authoritative; slow motion is explicit.
const THUMBS = 6

/** Evidence clip as a blob URL from the shared cache (preloaded in the background). */
function useClipBlob(src?: string, attempt = 0) {
  const [state, setState] = useState<{ url?: string; status: 'idle' | 'loading' | 'ready' | 'error'; progress: number }>(() => {
    const url = cachedClip(src)
    return url ? { url, status: 'ready', progress: 1 } : { status: 'idle', progress: 0 }
  })
  useEffect(() => {
    if (!src) { setState({ status: 'error', progress: 0 }); return }
    const ready = cachedClip(src)
    if (ready) { setState({ url: ready, status: 'ready', progress: 1 }); return }
    let alive = true
    const onProgress = (progress: number) => { if (alive) setState((s) => (s.status === 'ready' ? s : { ...s, status: 'loading', progress })) }
    setState({ status: 'loading', progress: 0 })
    getClip(src, onProgress)
      .then((url) => { if (alive) setState({ url, status: 'ready', progress: 1 }) })
      .catch(() => { if (alive) setState({ status: 'error', progress: 0 }) })
    return () => { alive = false; unsubscribeClip(src, onProgress) }
  }, [src, attempt])
  return state
}

/** Real frames sampled across the clip, drawn from a hidden video element. */
function useThumbnails(url?: string) {
  const [thumbs, setThumbs] = useState<{ t: number; img: string }[]>([])
  useEffect(() => {
    setThumbs([])
    if (!url) return
    let cancelled = false
    const v = document.createElement('video')
    v.muted = true
    v.preload = 'auto'
    v.src = url
    const canvas = document.createElement('canvas')
    const grab = (t: number) => new Promise<string>((resolve, reject) => {
      v.onseeked = () => {
        canvas.width = 192
        canvas.height = Math.round(192 * (v.videoHeight / v.videoWidth || 9 / 16))
        canvas.getContext('2d')!.drawImage(v, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/jpeg', 0.7))
      }
      v.onerror = reject
      v.currentTime = t
    })
    v.onloadedmetadata = async () => {
      const d = v.duration
      const out: { t: number; img: string }[] = []
      for (let i = 0; i < THUMBS && !cancelled; i++) {
        const t = Math.min(d - 0.05, (d * (i + 0.5)) / THUMBS)
        try { out.push({ t, img: await grab(t) }) } catch { break }
        if (!cancelled) setThumbs([...out])
      }
    }
    return () => { cancelled = true; v.removeAttribute('src'); v.load() }
  }, [url])
  return thumbs
}

const fmt = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`

interface Props {
  src?: string
  poster?: string
  title: string
  eventLabel: string
  /** Offset/cadence from immutable evidence metadata; thumbnails use clip-relative time. */
  eventOffsetSec?: number
  fps?: number
  downloadName: string
  /** Redaction / provenance chip shown on the video (what the evidence really is). */
  chip?: ReactNode
}

export function EvidencePlayer({ src, poster, title, eventLabel, eventOffsetSec, fps, downloadName, chip }: Props) {
  const [attempt, setAttempt] = useState(0)
  const clip = useClipBlob(src, attempt)
  const thumbs = useThumbnails(clip.url)
  const videoRef = useRef<HTMLVideoElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeed] = useState(DEFAULT_SPEED)
  const [playError, setPlayError] = useState(false)

  const eventT = eventOffsetSec !== undefined && eventOffsetSec <= duration ? eventOffsetSec : undefined
  const frameStep = fps ? 1 / fps : undefined

  const seekTo = useCallback((t: number) => {
    const v = videoRef.current
    if (!v || !duration) return
    v.currentTime = Math.max(0, Math.min(duration - 0.01, t))
    setTime(v.currentTime)
  }, [duration])
  const toggle = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) v.play().catch(() => setPlayError(true))
    else v.pause()
  }, [])
  const step = useCallback((frames: number) => {
    videoRef.current?.pause()
    if (frameStep) seekTo((videoRef.current?.currentTime ?? 0) + frames * frameStep)
  }, [seekTo])

  // Smooth progress while playing (timeupdate fires only ~4×/s).
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => { if (videoRef.current) setTime(videoRef.current.currentTime); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  // Shortcuts act only while focus is inside the player (never page-wide), and never on controls that own the key.
  const onKey = (e: RKeyboardEvent) => {
    const t = e.target as HTMLElement
    const own = t instanceof HTMLButtonElement || t instanceof HTMLAnchorElement || t instanceof HTMLTextAreaElement
    const range = t instanceof HTMLInputElement
    if (e.key === ' ' && !own && !range) { e.preventDefault(); toggle() }
    else if (e.key === 'ArrowLeft' && !range) { e.preventDefault(); seekTo(time - 1) }
    else if (e.key === 'ArrowRight' && !range) { e.preventDefault(); seekTo(time + 1) }
    else if (e.key === ',') step(-1)
    else if (e.key === '.') step(1)
  }

  const rangeRef = useRef<HTMLInputElement>(null)
  useEffect(() => { rangeRef.current?.style.setProperty('--p', `${duration ? (time / duration) * 100 : 0}%`) }, [time, duration])
  const ready = clip.status === 'ready' && !playError
  const btn = 'press text-text-secondary hover:text-text-primary hover:bg-elevation disabled:opacity-40 flex items-center justify-center gap-0.5 cursor-pointer rounded-md min-h-[var(--target-min)] min-w-[var(--target-min)] px-1'

  return (
    <div role="group" aria-label="Player dovadă video. Spațiu: redă/pauză, săgeți: ±1 s, virgulă și punct: cadru cu cadru" tabIndex={0} onKeyDown={onKey} className="flex flex-col gap-3 min-h-0 h-full rounded-xl">
      <div ref={boxRef} className="relative bg-black border border-border rounded-xl overflow-hidden flex-1 min-h-0 flex flex-col shadow-[var(--shadow-2)]">
        <div className="cctv-hud-frame relative flex-1 min-h-0 flex items-center justify-center" onClick={ready ? toggle : undefined}>
          <div className="cctv-hud-bottom-left" aria-hidden="true" /><div className="cctv-hud-bottom-right" aria-hidden="true" />
          <video
            ref={videoRef}
            src={clip.url}
            poster={poster}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            className="w-full h-full object-contain"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onLoadedMetadata={(e) => { setDuration(e.currentTarget.duration || 0); e.currentTarget.playbackRate = speed }}
            onTimeUpdate={(e) => { if (!playing) setTime(e.currentTarget.currentTime) }}
            onError={() => { if (clip.url) setPlayError(true) }}
          />
          {clip.status === 'loading' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-void/60 text-xs text-text-secondary">
              <Loader2 size={22} className="animate-spin text-action" />
              <span>Se încarcă dovada video… {clip.progress ? `${Math.round(clip.progress * 100)}%` : ''}</span>
            </div>
          )}
          {(clip.status === 'error' || playError) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-void/90 text-center px-6">
              <AlertTriangle size={26} className="text-caution" />
              <div className="font-display text-lg font-bold text-text-primary">Clip video indisponibil</div>
              <div className="text-xs text-text-secondary max-w-sm">Clipul video nu este disponibil pentru această alertă. Cadrul cheie, regula și istoricul rămân valabile.</div>
              <button type="button" className="rounded border border-border px-3 py-2" onClick={(e) => { e.stopPropagation(); if (src) evictClip(src); setPlayError(false); setAttempt((n) => n + 1) }}>Reîncearcă dovada video</button>
            </div>
          )}
          {ready && !playing && duration > 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-16 h-16 rounded-full glass flex items-center justify-center shadow-[var(--glow-signal)]">
                <Play size={24} className="text-text-primary ml-1" />
              </div>
            </div>
          )}
          <div className="absolute top-3 left-8 right-8 flex items-center justify-between text-xs font-mono pointer-events-none drop-shadow">
            <span className="flex items-center gap-1.5">{chip}</span>
            <span className="text-white font-semibold truncate ml-3 bg-black/60 backdrop-blur rounded-md px-2 py-0.5">{title}</span>
          </div>
        </div>

        {/* Scrubber: event marker in the middle of the ±3 s clip */}
        <div className="px-4 pt-2 bg-panel border-t border-border">
          <div className="relative h-7 flex items-center rs-scrub">
            <input
              ref={rangeRef}
              type="range"
              min={0}
              max={duration || 0}
              step={frameStep ?? 0.01}
              value={time}
              disabled={!ready}
              onChange={(e) => seekTo(Number(e.target.value))}
              aria-label="Poziție în clip"
              aria-valuetext={`${fmt(time)} din ${fmt(duration)}`}
              className="rs-range w-full cursor-pointer"
            />
            <span className="rs-scrub-mark" aria-hidden="true" />
            <span className="rs-scrub-label" aria-hidden="true">Eveniment</span>
          </div>
        </div>

        <div className="px-3 py-1.5 bg-panel flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2.5">
            <button type="button" disabled={!ready} onClick={() => seekTo(time - 1)} className={btn} title="−1 s (←)" aria-label={`−1 s (←)`}><RotateCcw size={13} />1s</button>
            <button type="button" disabled={!ready || !frameStep} onClick={() => step(-1)} className={btn} title="Cadrul anterior (,)" aria-label={`Cadrul anterior (,)`}><ChevronLeft size={15} /></button>
            <button
              type="button"
              disabled={!ready}
              onClick={toggle}
              title="Redă / pauză (spațiu)" aria-label="Redă / pauză (spațiu)"
              className="press w-11 h-11 rounded-full btn-primary bg-accent text-on-accent hover:brightness-110 disabled:opacity-40 flex items-center justify-center cursor-pointer"
            >
              {playing ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
            </button>
            <button type="button" disabled={!ready || !frameStep} onClick={() => step(1)} className={btn} title="Cadrul următor (.)" aria-label={`Cadrul următor (.)`}><ChevronRight size={15} /></button>
            <button type="button" disabled={!ready} onClick={() => seekTo(time + 1)} className={btn} title="+1 s (→)" aria-label={`+1 s (→)`}>1s<RotateCw size={13} /></button>
            <span className="text-text-secondary tabular-nums ml-1">{fmt(time)} / {fmt(duration)}</span>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" disabled={!ready || eventT === undefined} onClick={() => { if (eventT !== undefined) { videoRef.current?.pause(); seekTo(eventT) } }} className={`${btn} text-warning`} title={eventT === undefined ? "Poziția evenimentului nu este înregistrată în metadate" : "Sari la momentul evenimentului"} aria-label={`Sari la momentul evenimentului: ${eventLabel}`}>
              <Crosshair size={13} /><span className="hidden xl:inline">Eveniment</span>
            </button>
            <button
              type="button"
              onClick={() => {
                const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]
                setSpeed(next)
                if (videoRef.current) videoRef.current.playbackRate = next
              }}
              className="press px-2.5 min-h-[var(--target-min)] rounded-md bg-elevation border border-border text-text-primary hover:border-action text-xs font-bold cursor-pointer"
              title="Viteza de redare"
            >
              {speed}×
            </button>
            <button type="button" disabled={!ready} onClick={() => boxRef.current?.requestFullscreen?.()} className={btn} title="Ecran complet" aria-label={`Ecran complet`}><Maximize2 size={13} /></button>
            {clip.url ? (
              <a href={clip.url} download={downloadName} className={btn} title="Descarcă clipul" aria-label="Descarcă clipul"><Download size={13} /></a>
            ) : (
              <span className={`${btn} opacity-40`}><Download size={13} /></span>
            )}
          </div>
        </div>
      </div>

      {/* Filmstrip: real frames sampled from the clip */}
      <div className={`grid grid-cols-3 sm:grid-cols-6 gap-1.5 shrink-0 ${clip.status === 'ready' ? '' : 'hidden'}`}>
        {Array.from({ length: THUMBS }).map((_, i) => {
          const th = thumbs[i]
          const t = th?.t ?? (duration * (i + 0.5)) / THUMBS
          const active = duration > 0 && Math.abs(time - t) < duration / THUMBS / 2
          const isEvent = eventT !== undefined && duration > 0 && Math.abs(eventT - t) < duration / THUMBS / 2
          return (
            <button
              key={i}
              type="button"
              disabled={!ready}
              onClick={() => { videoRef.current?.pause(); seekTo(t) }}
              className={`press relative rounded-lg overflow-hidden border text-left cursor-pointer ${
                active ? 'border-action shadow-[var(--glow-signal)]' : isEvent ? 'border-warning' : 'border-border hover:border-action/60'
              }`}
            >
              <div className="aspect-video bg-void">
                {th ? <img src={th.img} alt="" className="w-full h-full object-cover" /> : poster && clip.status !== 'ready' ? <img src={poster} alt="" className="w-full h-full object-cover opacity-40" /> : null}
              </div>
              <div className={`absolute bottom-0 inset-x-0 text-xs font-mono text-center py-0.5 ${isEvent ? 'bg-warning text-void font-bold' : 'bg-void/75 text-text-secondary'}`}>
                {isEvent ? 'Eveniment' : `+${fmt(t)}`}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
