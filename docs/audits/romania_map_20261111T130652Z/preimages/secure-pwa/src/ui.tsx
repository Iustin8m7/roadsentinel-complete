import { Component, useEffect, useId, useRef } from "react";
import type { ComponentProps, ReactNode } from "react";

import type { Alert } from "./api/types";

export const TZ = "Europe/Bucharest";
const dt = new Intl.DateTimeFormat("ro-RO", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZone: TZ,
});
const tm = new Intl.DateTimeFormat("ro-RO", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
export const fmtDateTime = (iso: string) => dt.format(new Date(iso));
export const fmtTime = (iso: string) => tm.format(new Date(iso));

export const ROLE_LABEL: Record<string, string> = {
  system_admin: "Administrator de sistem",
  tenant_admin: "Administrator",
  operator: "Operator",
  patrol: "Patrulă",
  auditor: "Auditor",
};
export const STATUS_LABEL: Record<string, string> = {
  new: "Nouă",
  confirmed: "Confirmată",
  rejected: "Respinsă",
  pending: "În așteptare",
  approved: "Aprobată",
  denied: "Refuzată",
  revoked: "Revocată",
};
export const KIND_LABEL: Record<string, string> = {
  unblur: "Dezvăluire (unblur)",
  export: "Export original",
  account_reset: "Recuperare cont",
};

const PRIORITY: Record<Alert["priority"], { label: string; glyph: string }> = {
  critical: { label: "Critică", glyph: "▲" },
  high: { label: "Ridicată", glyph: "◆" },
  medium: { label: "Medie", glyph: "●" },
  info: { label: "Informativă", glyph: "○" },
};

/** Priority is never colour alone: glyph shape + Romanian label + colour. */
export function PriorityBadge({ priority }: { priority: Alert["priority"] }) {
  const p = PRIORITY[priority];
  return (
    <span className={`badge p-${priority}`}>
      <span aria-hidden="true">{p.glyph}</span>
      {p.label}
    </span>
  );
}

export function Banner({
  tone = "info",
  children,
}: {
  tone?: "info" | "ok" | "error" | "warn";
  children: ReactNode;
}) {
  return (
    <p className={`notice banner-${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: (id: string, describedBy?: string) => ReactNode;
}) {
  const id = useId();
  const hid = hint ? `${id}-h` : undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id, hid)}
      {hint && (
        <span id={hid} className="hint">
          {hint}
        </span>
      )}
    </div>
  );
}

/** Six-digit code input (paste and password-manager friendly). */
export function OtpInput(props: ComponentProps<"input">) {
  return (
    <input
      className="otp"
      inputMode="numeric"
      autoComplete="one-time-code"
      maxLength={6}
      pattern="[0-9]{6}"
      {...props}
    />
  );
}

/**
 * Modal on the native <dialog>: focus trap, inert background, Esc and focus restore come from the
 * browser. `onClose` fires for Esc and for the programmatic close.
 */
export function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const tid = useId();
  useEffect(() => {
    const el = ref.current;
    if (el && !el.open) el.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={tid}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="dialog-body">
        <h2 id={tid}>{title}</h2>
        {children}
      </div>
    </dialog>
  );
}

/** Explicit confirmation for decisions that cannot be undone (reject, deny, revoke, ...). */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  danger,
  busy,
  error,
  onConfirm,
  onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Dialog title={title} onClose={onCancel}>
      <div>{children}</div>
      {error && <Banner tone="error">{error}</Banner>}
      <div className="dialog-actions">
        <button type="button" className="secondary" autoFocus onClick={onCancel} disabled={busy}>
          Anulează
        </button>
        <button
          type="button"
          className={danger ? "danger" : ""}
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? "Se trimite…" : confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}

export function Chip({
  kind,
}: {
  kind: "redacted" | "redacted_heads" | "unredacted" | "warn";
  children?: never;
}) {
  const map = {
    redacted_heads: [
      "REDACTAT (euristic): doar capete",
      "Capetele sunt estompate euristic; numerele de înmatriculare pot rămâne vizibile",
    ],
    redacted: [
      "REDACTAT (euristic)",
      "Redactare euristică automată, fără garanție de completitudine",
    ],
    unredacted: ["FĂRĂ REDACTARE", "Dovada nu a fost redactată"],
    warn: ["REDACTARE NECONFIRMATĂ", "Sistemul nu raportează nivelul de redactare"],
  } as const;
  const [label, hint] = map[kind];
  return (
    <span className={`chip ${kind}`} title={hint}>
      {label}
    </span>
  );
}

/** Chip kind for what the API reports about an evidence file's redaction (never assumed). */
export function redactionChipKind(
  redaction: string | undefined,
): "redacted" | "redacted_heads" | "unredacted" | "warn" {
  if (redaction === "full") return "redacted";
  if (redaction === "heads_only") return "redacted_heads";
  if (redaction === "off") return "unredacted";
  return "warn";
}

/** Sets the document title; the shell moves focus to <main> on navigation. */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · RoadSentinel`;
  }, [title]);
}

interface BoundaryState {
  failed: boolean;
}
export class ErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { failed: false };
  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="stack">
        <h1>A apărut o eroare</h1>
        <p>Ecranul nu a putut fi afișat. Datele nu au fost modificate.</p>
        <button onClick={() => window.location.assign("/")}>Reîncarcă aplicația</button>
      </div>
    );
  }
}
