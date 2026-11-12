import { useEffect, useRef, type ReactNode } from 'react'
import { Button } from './ui'

interface DialogProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** Labelled-by id for the description, optional */
  describedBy?: string
  wide?: boolean
}

/**
 * Modal built on the native <dialog>: the browser traps focus, makes the rest of the
 * page inert, closes on Esc and restores focus to the opener.
 */
export function Dialog({ open, title, onClose, children, describedBy, wide }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      aria-labelledby="dlg-title"
      aria-describedby={describedBy}
      onClose={onClose}
      onCancel={(e) => { e.preventDefault(); onClose() }}
      className={`m-auto ${wide ? "w-[min(72rem,calc(100%-1rem))]" : "w-[min(32rem,calc(100%-2rem))]"} max-h-[calc(100dvh-1rem)] rounded-xl glass text-text-primary p-0 rise backdrop:bg-black/60 backdrop:backdrop-blur-sm`}
    >
      {open && (
        <div className="p-5 flex flex-col gap-4">
          <h2 id="dlg-title" className="font-display text-xl font-semibold">{title}</h2>
          {children}
        </div>
      )}
    </dialog>
  )
}

interface ConfirmProps {
  open: boolean
  title: string
  description: ReactNode
  confirmLabel: string
  /** danger for irreversible/negative actions (reject, revoke, deny) */
  tone?: 'primary' | 'danger'
  busy?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

/** Explicit confirmation step for decisions that cannot be undone. Cancel is the initial focus. */
export function ConfirmDialog({ open, title, description, confirmLabel, tone = 'primary', busy, error, onConfirm, onCancel }: ConfirmProps) {
  return (
    <Dialog open={open} title={title} onClose={onCancel} describedBy="dlg-desc">
      <div id="dlg-desc" className="text-sm text-text-secondary">{description}</div>
      {error && <p role="alert" className="text-sm text-critical">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" autoFocus onClick={onCancel} disabled={busy}>Anulează</Button>
        <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={onConfirm} loading={busy}>{confirmLabel}</Button>
      </div>
    </Dialog>
  )
}
