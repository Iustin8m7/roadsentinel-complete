import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'

interface LivePlayerProps {
  src: string
  className?: string
  controls?: boolean
  onStateChange?: (state: "connecting" | "playing" | "stalled" | "error") => void
}

// Plays a public HLS camera stream (muted, so browsers allow autoplay). Safari plays HLS
// natively; elsewhere hls.js feeds it through Media Source Extensions.
export function LivePlayer({ src, className = '', controls = false, onStateChange }: LivePlayerProps) {
  const ref = useRef<HTMLVideoElement>(null)
  const onStateChangeRef = useRef(onStateChange)
  const [failed, setFailed] = useState(false)
  onStateChangeRef.current = onStateChange

  useEffect(() => {
    const video = ref.current
    if (!video) return
    setFailed(false)
    onStateChangeRef.current?.("connecting")
    const onPlaying = () => onStateChangeRef.current?.("playing")
    const onWaiting = () => onStateChangeRef.current?.("stalled")
    const onError = () => { setFailed(true); onStateChangeRef.current?.("error") }
    video.addEventListener("playing", onPlaying)
    video.addEventListener("waiting", onWaiting)
    video.addEventListener("error", onError)
    const timeout = window.setTimeout(() => {
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        setFailed(true)
        onStateChangeRef.current?.("error")
      }
    }, 15000)
    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: false, liveSyncDurationCount: 2 })
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) { setFailed(true); onStateChangeRef.current?.("error") }
      })
      hls.loadSource(src)
      hls.attachMedia(video)
      return () => {
        window.clearTimeout(timeout)
        video.removeEventListener("playing", onPlaying)
        video.removeEventListener("waiting", onWaiting)
        video.removeEventListener("error", onError)
        hls.destroy()
        video.pause()
        video.removeAttribute("src")
        video.load()
      }
    }
    video.src = src
    return () => {
      window.clearTimeout(timeout)
      video.removeEventListener("playing", onPlaying)
      video.removeEventListener("waiting", onWaiting)
      video.removeEventListener("error", onError)
      video.pause()
      video.removeAttribute('src')
      video.load()
    }
  }, [src])

  if (failed) {
    return (
      <div className={`flex items-center justify-center bg-black/80 text-xs text-text-secondary ${className}`}>
        Fluxul live nu poate fi redat acum
      </div>
    )
  }
  return <video ref={ref} className={`bg-black object-cover ${className}`} autoPlay muted playsInline controls={controls} />
}

export function LiveBadge() {
  return (
    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-danger text-white text-xs font-mono font-bold tracking-wider">
      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
      LIVE
    </span>
  )
}
