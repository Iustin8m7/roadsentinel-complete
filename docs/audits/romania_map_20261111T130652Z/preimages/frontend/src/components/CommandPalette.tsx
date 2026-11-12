import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { CornerDownLeft, Search } from 'lucide-react'

export interface Command { id: string; label: string; hint?: string; icon?: ReactNode; run: () => void }

/** Ctrl/Cmd+K palette on the native <dialog> (focus trap, Esc, restore). Combobox + listbox semantics. */
export function CommandPalette({ open, onClose, commands, onFreeText }: {
  open: boolean
  onClose: () => void
  commands: Command[]
  /** Free text becomes a last "search the archive" command */
  onFreeText?: (q: string) => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [q, setQ] = useState('')
  const [i, setI] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) { setQ(''); setI(0); el.showModal() }
    if (!open && el.open) el.close()
  }, [open])

  const list = useMemo(() => {
    const n = q.trim().toLowerCase()
    const base = n ? commands.filter((c) => (c.label + ' ' + (c.hint ?? '')).toLowerCase().includes(n)) : commands
    const extra: Command[] = n && onFreeText ? [{ id: '__search', label: `Caută în arhivă: „${q.trim()}”`, hint: 'Căutare', icon: <Search size={16} aria-hidden="true" />, run: () => onFreeText(q.trim()) }] : []
    return [...base, ...extra]
  }, [q, commands, onFreeText])

  const run = (c?: Command) => { if (!c) return; onClose(); c.run() }
  const idx = Math.min(i, Math.max(0, list.length - 1))

  return (
    <dialog
      ref={ref}
      aria-label="Paletă de comenzi"
      onClose={onClose}
      onCancel={(e) => { e.preventDefault(); onClose() }}
      className="m-auto mt-[12vh] w-[min(36rem,calc(100%-1rem))] rounded-2xl glass p-0 text-text-primary backdrop:bg-black/55 backdrop:backdrop-blur-sm"
    >
      {open && (
        <div className="flex flex-col">
          <div className="flex items-center gap-3 px-4 border-b border-[var(--glass-line)]">
            <Search size={18} aria-hidden="true" className="text-text-muted shrink-0" />
            <input
              autoFocus
              role="combobox"
              aria-expanded="true"
              aria-controls="cmd-list"
              aria-activedescendant={list[idx] ? `cmd-${list[idx].id}` : undefined}
              aria-label="Caută o pagină sau o comandă"
              placeholder="Mergi la… sau caută în arhivă"
              value={q}
              onChange={(e) => { setQ(e.target.value); setI(0) }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown') { e.preventDefault(); setI(Math.min(list.length - 1, idx + 1)) }
                else if (e.key === 'ArrowUp') { e.preventDefault(); setI(Math.max(0, idx - 1)) }
                else if (e.key === 'Enter') { e.preventDefault(); run(list[idx]) }
              }}
              className="flex-1 min-h-[52px] bg-transparent outline-none text-base placeholder:text-text-muted focus-visible:outline-none"
            />
            <kbd className="hidden sm:inline text-xs font-mono text-text-muted border border-border rounded px-1.5 py-0.5">Esc</kbd>
          </div>
          <ul id="cmd-list" role="listbox" aria-label="Rezultate" className="max-h-[50vh] overflow-y-auto p-2">
            {list.length === 0 && <li className="px-3 py-6 text-sm text-text-secondary text-center">Nimic găsit.</li>}
            {list.map((c, n) => (
              <li
                key={c.id}
                id={`cmd-${c.id}`}
                role="option"
                aria-selected={n === idx}
                onMouseMove={() => setI(n)}
                onClick={() => run(c)}
                className={`flex items-center gap-3 px-3 min-h-[44px] rounded-lg cursor-pointer text-sm ${n === idx ? 'bg-elevation text-text-primary ring-1 ring-[var(--glass-line)]' : 'text-text-secondary'}`}
              >
                <span className="text-action shrink-0">{c.icon}</span>
                <span className="flex-1 truncate">{c.label}</span>
                {c.hint && <span className="text-xs text-text-muted">{c.hint}</span>}
                {n === idx && <CornerDownLeft size={14} aria-hidden="true" className="text-text-muted" />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </dialog>
  )
}
