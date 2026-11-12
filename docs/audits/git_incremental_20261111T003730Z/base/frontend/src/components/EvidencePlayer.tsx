import { useCallback, useEffect, useRef, useState } from 'react'
import { getClip, cachedClip, unsubscribeClip } from '@/lib/demo'
import { AlertTriangle, BookmarkPlus, ChevronLeft, ChevronRight, Download, Loader2, Maximize2, Pause, Play, RotateCcw, RotateCw, Crosshair } from 'lucide-react'

const FPS = 30
const SPEEDS = [0.25, 0.5, 1]
const DEFAULT_SPEED = 0.25 // slow by default so the manoeuvre is visible
const THUMBS = 6

/** Evidence clip as a blob URL from the shared cache (preloaded in the background). */
function useClipBlob(src?: string) {
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
  }, [src])
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
  /** Wall-clock time of the event, shown under each thumbnail. */
  eventAt: number
  downloadName: string
  /** Case bookmarks on this clip (seconds from the clip start), shown on the scrubber. */
  bookmarks?: { id: string; t: number; label: string }[]
  /** Adds a bookmark at the current playback position (only when the user may annotate). */
  onAddBookmark?: (t: number) => void
  /** Seek request from outside (e.g. a bookmark or note clicked in the case panel). */
  seekRequest?: { t: number; n: number }
  /** Replaces the generic "clip unavailable" text (e.g. purged vs missing evidence). */
  unavailableText?: string
}

export function EvidencePlayer({ src, poster, title, eventLabel, eventAt, downloadName, bookmarks = [], onAddBookmark, seekRequest, unavailableText }: Props) {
  const clip = useClipBlob(src)
  const thumbs = useThumbnails(clip.url)
  const videoRef = useRef<HTMLVideoElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeed] = useState(DEFAULT_SPEED)
  const [playError, setPlayError] = useState(false)

  // The pipeline cuts ±3 s around the event, so the event sits in the middle of the clip.
  const eventT = duration / 2

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
  useEffect(() => {
    if (!seekRequest) return
    videoRef.current?.pause()
    seekTo(seekRequest.t)
  }, [seekRequest, seekTo])
  const step = useCallback((frames: number) => {
    videoRef.current?.pause()
    seekTo((videoRef.current?.currentTime ?? 0) + frames / FPS)
  }, [seekTo])

  // Smooth progress while playing (timeupdate fires only ~4×/s).
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => { if (videoRef.current) setTime(videoRef.current.currentTime); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === ' ') { e.preventDefault(); toggle() }
      else if (e.key === 'ArrowLeft') seekTo(time - 1)
      else if (e.key === 'ArrowRight') seekTo(time + 1)
      else if (e.key === ',') step(-1)
      else if (e.key === '.') step(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggle, seekTo, step, time])

  const ready = clip.status === 'ready' && !playError
  const btn = 'text-[#7D8A9B] hover:text-[#E6EDF3] disabled:opacity-40 transition-colors flex items-center gap-0.5 cursor-pointer'

  return (
    <div className="flex flex-col gap-2 min-h-0 h-full">
      <div ref={boxRef} className="relative bg-black border border-[#1E2A36] rounded-md overflow-hidden flex-1 min-h-0 flex flex-col">
        <div className="relative flex-1 min-h-0 flex items-center justify-center" onClick={ready ? toggle : undefined}>
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
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[#0A0E14]/60 text-xs text-[#7D8A9B]">
              <Loader2 size={22} className="animate-spin text-[#3DA5FF]" />
              <span>Se încarcă dovada video… {clip.progress ? `${Math.round(clip.progress * 100)}%` : ''}</span>
            </div>
          )}
          {(clip.status === 'error' || playError) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[#0A0E14]/90 text-center px-6">
              <AlertTriangle size={26} className="text-[#FFC23D]" />
              <div className="font-sans text-lg font-bold text-[#E6EDF3]">Clip video indisponibil</div>
              <div className="text-xs text-[#7D8A9B] max-w-sm">{unavailableText ?? 'Dovada video pentru această alertă nu mai este stocată pe server. Cadrul cheie, regula și istoricul rămân valabile.'}</div>
            </div>
          )}
          {ready && !playing && duration > 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-14 h-14 rounded-full bg-[#0A0E14]/70 border border-[#3DA5FF]/60 flex items-center justify-center">
                <Play size={24} className="text-[#E6EDF3] ml-1" />
              </div>
            </div>
          )}
          <div className="absolute top-2 left-3 right-3 flex items-center justify-between text-[11px] font-mono pointer-events-none drop-shadow">
            <span className="flex items-center gap-1.5 text-[#FF3B3B] font-bold"><span className="w-2 h-2 rounded-full bg-[#FF3B3B] animate-pulse" />DOVADĂ</span>
            <span className="text-[#E6EDF3] font-semibold truncate ml-3">{title}</span>
          </div>
        </div>

        {/* Scrubber: event marker in the middle of the ±3 s clip */}
        <div className="px-3 pt-2 bg-[#111821] border-t border-[#1E2A36]">
          <div className="relative h-4 flex items-center">
            <div className="absolute inset-x-0 h-1.5 rounded-full bg-[#17202B]" />
            <div className="absolute left-0 h-1.5 rounded-full bg-[#3DA5FF]" style={{ width: `${duration ? (time / duration) * 100 : 0}%` }} />
            {duration > 0 && (
              <button
                type="button"
                title={`${eventLabel} — sari la eveniment`}
                onClick={() => seekTo(eventT)}
                className="absolute z-10 -translate-x-1/2 w-3 h-3 rotate-45 bg-[#FF3B3B] shadow-[0_0_8px_rgba(255,59,59,0.9)] cursor-pointer"
                style={{ left: '50%' }}
              />
            )}
            {duration > 0 && bookmarks.map((b) => (
              <button
                key={b.id}
                type="button"
                title={`Marcaj: ${b.label} (${fmt(b.t)})`}
                aria-label={`Sari la marcajul „${b.label}” (${fmt(b.t)})`}
                data-testid="bookmark-marker"
                onClick={() => { videoRef.current?.pause(); seekTo(b.t) }}
                className="absolute z-20 -translate-x-1/2 w-1.5 h-4 rounded-sm bg-[#FFC23D] hover:bg-white focus:outline focus:outline-2 focus:outline-[#3DA5FF] cursor-pointer"
                style={{ left: `${Math.min(100, (b.t / duration) * 100)}%` }}
              />
            ))}
            <input
              type="range"
              min={0}
              max={duration || 0}
              step={1 / FPS}
              value={time}
              disabled={!ready}
              onChange={(e) => seekTo(Number(e.target.value))}
              aria-label="Poziție în clip"
              className="absolute inset-x-0 w-full opacity-0 cursor-pointer h-4"
            />
          </div>
        </div>

        <div className="px-3 py-1.5 bg-[#111821] flex items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2.5">
            <button type="button" disabled={!ready} onClick={() => seekTo(time - 1)} className={btn} title="−1 s (←)"><RotateCcw size={13} />1s</button>
            <button type="button" disabled={!ready} onClick={() => step(-1)} className={btn} title="Cadrul anterior (,)"><ChevronLeft size={15} /></button>
            <button
              type="button"
              disabled={!ready}
              onClick={toggle}
              title="Redă / pauză (spațiu)"
              className="w-7 h-7 rounded-md bg-[#17202B] border border-[#1E2A36] text-[#E6EDF3] hover:border-[#3DA5FF] hover:text-[#3DA5FF] disabled:opacity-40 flex items-center justify-center cursor-pointer"
            >
              {playing ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
            </button>
            <button type="button" disabled={!ready} onClick={() => step(1)} className={btn} title="Cadrul următor (.)"><ChevronRight size={15} /></button>
            <button type="button" disabled={!ready} onClick={() => seekTo(time + 1)} className={btn} title="+1 s (→)">1s<RotateCw size={13} /></button>
            <span className="text-[#7D8A9B] tabular-nums ml-1">{fmt(time)} / {fmt(duration)}</span>
          </div>
          <div className="flex items-center gap-2">
            {onAddBookmark && (
              <button
                type="button"
                disabled={!ready}
                onClick={() => { videoRef.current?.pause(); onAddBookmark(videoRef.current?.currentTime ?? time) }}
                className={`${btn} text-[#FFC23D]`}
                title="Adaugă marcaj la momentul curent"
                aria-label="Adaugă marcaj la momentul curent"
              >
                <BookmarkPlus size={13} /><span className="hidden xl:inline">Marcaj</span>
              </button>
            )}
            <button type="button" disabled={!ready} onClick={() => { videoRef.current?.pause(); seekTo(eventT) }} className={`${btn} text-[#FF8A1F]`} title="Sari la momentul evenimentului">
              <Crosshair size={13} /><span className="hidden xl:inline">Eveniment</span>
            </button>
            <button
              type="button"
              onClick={() => {
                const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]
                setSpeed(next)
                if (videoRef.current) videoRef.current.playbackRate = next
              }}
              className="px-2 py-0.5 rounded bg-[#17202B] border border-[#1E2A36] text-[#E6EDF3] hover:border-[#3DA5FF] text-[11px] font-bold cursor-pointer"
              title="Viteza de redare"
            >
              {speed}×
            </button>
            <button type="button" disabled={!ready} onClick={() => boxRef.current?.requestFullscreen?.()} className={btn} title="Ecran complet"><Maximize2 size={13} /></button>
            {clip.url ? (
              <a href={clip.url} download={downloadName} className={btn} title="Descarcă clipul"><Download size={13} /></a>
            ) : (
              <span className={`${btn} opacity-40`}><Download size={13} /></span>
            )}
          </div>
        </div>
      </div>

      {/* Filmstrip: real frames sampled from the clip */}
      <div className="grid grid-cols-6 gap-1.5 shrink-0">
        {Array.from({ length: THUMBS }).map((_, i) => {
          const th = thumbs[i]
          const t = th?.t ?? (duration * (i + 0.5)) / THUMBS
          const active = duration > 0 && Math.abs(time - t) < duration / THUMBS / 2
          const isEvent = duration > 0 && Math.abs(eventT - t) < duration / THUMBS / 2
          return (
            <button
              key={i}
              type="button"
              disabled={!ready}
              onClick={() => { videoRef.current?.pause(); seekTo(t) }}
              className={`relative rounded-md overflow-hidden border text-left cursor-pointer transition-colors ${
                active ? 'border-[#3DA5FF]' : isEvent ? 'border-[#FF8A1F]' : 'border-[#1E2A36] hover:border-[#3DA5FF]/60'
              }`}
            >
              <div className="aspect-video bg-[#0A0E14]">
                {th ? <img src={th.img} alt="" className="w-full h-full object-cover" /> : poster && clip.status !== 'ready' ? <img src={poster} alt="" className="w-full h-full object-cover opacity-40" /> : null}
              </div>
              <div className={`absolute bottom-0 inset-x-0 text-[9px] font-mono text-center py-0.5 ${isEvent ? 'bg-[#FF8A1F] text-[#0A0E14] font-bold' : 'bg-[#0A0E14]/75 text-[#7D8A9B]'}`}>
                {isEvent ? 'EVENIMENT' : new Date(eventAt + (t - eventT) * 1000).toTimeString().slice(0, 8)}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
