/** Decorative line illustrations (inline SVG, no external assets). Always aria-hidden. */
const common = { width: 132, height: 96, viewBox: '0 0 132 96', fill: 'none', 'aria-hidden': true as const }

export function RadarArt() {
  return (
    <svg {...common}>
      <ellipse cx="66" cy="84" rx="44" ry="6" fill="var(--border-subtle)" />
      <circle cx="66" cy="46" r="34" stroke="var(--border-line)" strokeWidth="1.5" />
      <circle cx="66" cy="46" r="22" stroke="var(--border-line)" strokeWidth="1.5" strokeDasharray="3 5" />
      <circle cx="66" cy="46" r="10" stroke="var(--action)" strokeWidth="1.5" />
      <path d="M66 46 L92 26" stroke="var(--action)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="66" cy="46" r="3" fill="var(--action)" />
      <circle cx="40" cy="62" r="2.5" fill="var(--text-muted)" />
    </svg>
  )
}

export function FolderArt() {
  return (
    <svg {...common}>
      <ellipse cx="66" cy="84" rx="46" ry="6" fill="var(--border-subtle)" />
      <path d="M24 30a6 6 0 0 1 6-6h22l8 9h42a6 6 0 0 1 6 6v34a6 6 0 0 1-6 6H30a6 6 0 0 1-6-6V30Z" stroke="var(--border-line)" strokeWidth="1.5" fill="var(--bg-elevation)" />
      <circle cx="78" cy="56" r="12" stroke="var(--action)" strokeWidth="2" />
      <path d="m87 65 9 9" stroke="var(--action)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M38 52h16M38 62h10" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function SignalLostArt() {
  return (
    <svg {...common}>
      <ellipse cx="66" cy="84" rx="40" ry="6" fill="var(--border-subtle)" />
      <path d="M30 40a52 52 0 0 1 72 0" stroke="var(--border-line)" strokeWidth="2" strokeLinecap="round" />
      <path d="M42 52a35 35 0 0 1 48 0" stroke="var(--border-line)" strokeWidth="2" strokeLinecap="round" />
      <path d="M54 64a18 18 0 0 1 24 0" stroke="var(--sev-critical)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="66" cy="74" r="3.5" fill="var(--sev-critical)" />
      <path d="M92 20 40 76" stroke="var(--sev-critical)" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
    </svg>
  )
}
