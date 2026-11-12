import { useEffect, useRef } from 'react'
import { motionOff } from '@/components/AnimatedNumber'

/** Decorative abstract road graph (cameras = nodes, roads = edges). No data, no labels: aria-hidden. */
const NODES: [number, number][] = [
  [90, 430], [220, 300], [380, 360], [300, 140], [520, 200], [640, 330], [700, 120], [560, 480], [170, 545], [430, 60], [90, 190],
]
const EDGES: [number, number, number][] = [
  [0, 1, 18], [1, 2, -26], [1, 3, 22], [2, 4, 30], [3, 4, -20], [4, 5, 24], [4, 6, -30], [2, 7, 20], [5, 7, -22],
  [0, 8, -24], [8, 2, 28], [5, 6, 16], [3, 9, 14], [10, 3, -18], [10, 1, 20], [9, 4, 26],
]

function edgePath(a: [number, number], b: [number, number], bend: number) {
  const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2
  const dx = b[0] - a[0], dy = b[1] - a[1]
  const len = Math.hypot(dx, dy) || 1
  const cx = mx + (-dy / len) * bend, cy = my + (dx / len) * bend
  return `M${a[0]} ${a[1]} Q${cx.toFixed(1)} ${cy.toFixed(1)} ${b[0]} ${b[1]}`
}

export function HeroGraph() {
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = wrap.current
    if (!el || motionOff()) return
    let raf = 0
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        el.style.setProperty('--px', ((e.clientX / window.innerWidth) * 2 - 1).toFixed(3))
        el.style.setProperty('--py', ((e.clientY / window.innerHeight) * 2 - 1).toFixed(3))
      })
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => { window.removeEventListener('pointermove', onMove); cancelAnimationFrame(raf) }
  }, [])

  return (
    <div ref={wrap} className="hero-par absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <svg className="hero-layer absolute inset-0 w-full h-full" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid slice" fill="none">
        <defs>
          <linearGradient id="hg-edge" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="var(--action)" />
            <stop offset="1" stopColor="var(--accent-2)" />
          </linearGradient>
          <radialGradient id="hg-halo">
            <stop offset="0" stopColor="var(--action)" stopOpacity="0.45" />
            <stop offset="1" stopColor="var(--action)" stopOpacity="0" />
          </radialGradient>
        </defs>
        {EDGES.map(([a, b, bend], i) => (
          <g key={i}>
            <path d={edgePath(NODES[a], NODES[b], bend)} stroke="var(--border-line)" strokeWidth="6" strokeLinecap="round" opacity="0.35" />
            <path d={edgePath(NODES[a], NODES[b], bend)} stroke="var(--border-subtle)" strokeWidth="1.5" strokeDasharray="2 8" />
            <path d={edgePath(NODES[a], NODES[b], bend)} className="hero-edge" stroke="url(#hg-edge)" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
          </g>
        ))}
        {NODES.map(([x, y], i) => (
          <g key={i}>
            <circle cx={x} cy={y} r="26" fill="url(#hg-halo)" opacity="0.55" />
            <circle cx={x} cy={y} r="9" className="hero-node" stroke="var(--action)" strokeWidth="1.5" />
            <circle cx={x} cy={y} r="4" fill={i % 3 === 0 ? 'var(--accent-2)' : 'var(--action)'} />
          </g>
        ))}
      </svg>
      <div className="hero-scan absolute left-0 right-0 h-24 bg-gradient-to-b from-transparent via-[var(--aurora-a)] to-transparent" />
    </div>
  )
}
