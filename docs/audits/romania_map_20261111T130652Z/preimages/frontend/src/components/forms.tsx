import { useId, type ComponentProps, type ReactNode } from 'react'

interface FieldProps {
  label: string
  hint?: string
  error?: string | null
  children: (p: { id: string; 'aria-describedby'?: string; 'aria-invalid'?: boolean }) => ReactNode
}

/** Label + control + hint/error wired with ids; every form control goes through this. */
export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId()
  const descId = error || hint ? `${id}-d` : undefined
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-text-primary">{label}</label>
      {children({ id, 'aria-describedby': descId, 'aria-invalid': error ? true : undefined })}
      {(error || hint) && (
        <p id={descId} role={error ? 'alert' : undefined} className={`text-xs ${error ? 'text-critical' : 'text-text-secondary'}`}>{error || hint}</p>
      )}
    </div>
  )
}

export const inputCls =
  'w-full bg-void/60 border border-border rounded-lg px-3 min-h-[max(40px,var(--target-min))] text-sm text-text-primary placeholder:text-text-muted disabled:opacity-50 hover:border-text-muted focus-visible:border-action focus-visible:shadow-[var(--glow-signal)]'

export function TextInput(p: ComponentProps<'input'>) {
  return <input {...p} className={`${inputCls} ${p.className ?? ''}`} />
}

export function TextArea(p: ComponentProps<'textarea'>) {
  return <textarea {...p} className={`${inputCls} py-2 ${p.className ?? ''}`} />
}

/** Six-digit one-time code: a single numeric field (paste- and password-manager-friendly). */
export function OtpInput(p: Omit<ComponentProps<'input'>, 'type' | 'inputMode' | 'maxLength'>) {
  return (
    <input
      {...p}
      type="text"
      inputMode="numeric"
      autoComplete="one-time-code"
      maxLength={6}
      pattern="[0-9]{6}"
      className={`${inputCls} text-center text-2xl tracking-[0.5em] tabular-nums font-mono min-h-[56px] ${p.className ?? ''}`}
    />
  )
}
