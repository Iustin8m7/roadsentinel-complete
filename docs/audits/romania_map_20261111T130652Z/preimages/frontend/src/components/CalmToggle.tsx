import { useState } from 'react'
import { Waves, Wind } from 'lucide-react'

function read(): boolean {
  try { return localStorage.getItem('rs-calm') === 'on' } catch { return false }
}

/** Calm mode: removes decorative glow, aurora, grain and ambient motion (persisted as rs-calm). */
export function CalmToggle() {
  const [on, setOn] = useState(read)
  const Icon = on ? Wind : Waves
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label="Mod calm (fără efecte decorative)"
      title={on ? 'Mod calm: activ' : 'Mod calm: oprit'}
      onClick={() => {
        const next = !on
        setOn(next)
        const el = document.documentElement
        if (next) el.setAttribute('data-calm', 'on'); else el.removeAttribute('data-calm')
        try { if (next) localStorage.setItem('rs-calm', 'on'); else localStorage.removeItem('rs-calm') } catch { /* session only */ }
      }}
      className={`press inline-flex items-center justify-center w-9 h-9 min-h-[var(--target-min)] min-w-[var(--target-min)] rounded-lg hover:bg-elevation cursor-pointer ${on ? 'text-action bg-elevation' : 'text-text-secondary hover:text-text-primary'}`}
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  )
}
