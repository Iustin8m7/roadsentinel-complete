import { useEffect, useRef, useState } from 'react'

/** True when the user (or calm mode) asked for no decorative motion. */
export function motionOff(): boolean {
  if (typeof window === 'undefined') return true
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches || document.documentElement.getAttribute('data-calm') === 'on'
}

/** Tweens between integer values (400 ms ease-out). Renders the final value at once when motion is off. */
export function AnimatedNumber({ value, className = '' }: { value: number; className?: string }) {
  const [shown, setShown] = useState(value)
  const from = useRef(value)
  useEffect(() => {
    if (motionOff() || from.current === value) {
      from.current = value
      setShown(value)
      return
    }
    const start = performance.now()
    const a = from.current
    let raf = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 400)
      const e = 1 - Math.pow(1 - t, 3)
      setShown(Math.round(a + (value - a) * e))
      if (t < 1) raf = requestAnimationFrame(tick)
      else from.current = value
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); from.current = value }
  }, [value])
  return <span className={`num ${className}`}>{shown}</span>
}
