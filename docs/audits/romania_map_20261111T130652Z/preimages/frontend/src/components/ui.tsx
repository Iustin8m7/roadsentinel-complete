import type { ReactNode, ButtonHTMLAttributes } from "react";
import type { AlertStatus } from "@/types";
import { RadarArt, SignalLostArt } from "@/components/Illustrations";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "confirm" | "reject";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  loading = false,
  disabled,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const baseStyle =
    "inline-flex items-center justify-center gap-2 font-semibold rounded-lg press disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer min-h-[var(--target-min)]";
  const sizeStyle = size === "sm" ? "px-2.5 py-1 text-xs" : size === "lg" ? "px-6 py-2.5 text-base" : "px-4 py-2 text-sm";
  const variants: Record<string, string> = {
    primary: "btn-primary bg-accent hover:brightness-110 text-on-accent",
    secondary: "bg-elevation hover:bg-border text-text-primary border border-border",
    confirm: "bg-ok hover:brightness-110 text-void",
    reject: "bg-transparent hover:bg-critical/10 text-critical border border-critical/60",
    danger: "bg-danger hover:brightness-110 text-white",
    ghost: "bg-transparent hover:bg-elevation text-text-secondary hover:text-text-primary",
  };
  return (
    <button
      type={type}
      className={`${baseStyle} ${sizeStyle} ${variants[variant] ?? variants.primary} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <span className="w-3.5 h-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

const STATUS: Record<string, { label: string; cls: string }> = {
  new: { label: "Nouă", cls: "text-action bg-action/10 border-action/40" },
  in_review: { label: "În verificare", cls: "text-caution bg-caution/10 border-caution/40" },
  confirmed: { label: "Confirmată", cls: "text-ok bg-ok/10 border-ok/40" },
  closed: { label: "Închisă", cls: "text-text-secondary bg-elevation border-border" },
  rejected: { label: "Respinsă", cls: "text-text-secondary bg-elevation border-border" },
};
const STATUS_ALIAS: Record<string, string> = { nou: "new", "în verificare": "in_review", confirmat: "confirmed", respins: "rejected" };

export function StatusBadge({ status }: { status: AlertStatus | string }) {
  const raw = (status || "").toLowerCase();
  const st = STATUS[STATUS_ALIAS[raw] ?? raw];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${st?.cls ?? "text-text-secondary bg-panel border-border"}`}>
      {st?.label ?? status}
    </span>
  );
}

export type ChipKind = "demo" | "synthetic" | "redacted" | "redacted_heads" | "unredacted" | "unknown";
const CHIPS: Record<ChipKind, { label: string; cls: string; hint: string }> = {
  demo: { label: "DEMO", cls: "text-caution border-caution bg-panel", hint: "Date demonstrative, nu provin din sistemul real" },
  synthetic: { label: "SINTETIC", cls: "text-caution border-caution bg-panel", hint: "Material generat sintetic" },
  redacted: { label: "REDACTAT (euristic)", cls: "text-ok border-ok bg-panel", hint: "Redactare euristică automată, fără garanție de completitudine" },
  redacted_heads: { label: "REDACTAT (euristic): doar capete", cls: "text-caution border-caution bg-panel", hint: "Capetele sunt estompate euristic; numerele de înmatriculare pot rămâne vizibile" },
  unknown: { label: "REDACTARE NECONFIRMATĂ", cls: "text-caution border-caution bg-panel", hint: "Sistemul nu raportează nivelul de redactare al acestei dovezi" },
  unredacted: { label: "FĂRĂ REDACTARE", cls: "text-critical border-critical bg-panel", hint: "Dovada nu a fost redactată" },
};
export function Chip({ kind }: { kind: ChipKind }) {
  const c = CHIPS[kind];
  return (
    <span title={c.hint} className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border tracking-wide ${c.cls}`}>
      {c.label}
    </span>
  );
}

export function Banner({ tone = "info", children }: { tone?: "info" | "warn" | "error"; children: ReactNode }) {
  const cls = tone === "error" ? "border-critical/60 bg-critical/10 text-text-primary" : tone === "warn" ? "border-caution/60 bg-caution/10 text-text-primary" : "border-border bg-elevation text-text-primary";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`px-4 py-2 text-sm border-b ${cls}`}>
      {children}
    </div>
  );
}

export function EmptyState({ title, hint, action, art }: { title: string; hint?: string; action?: ReactNode; art?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-12 px-6 rise">
      {art ?? <RadarArt />}
      <p className="font-display text-lg font-semibold text-text-primary mt-2">{title}</p>
      {hint && <p className="text-sm text-text-secondary max-w-md">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center text-center gap-3 py-12 px-6 rise">
      <SignalLostArt />
      <p className="font-display text-lg font-semibold text-critical">Nu s-au putut încărca datele</p>
      <p className="text-sm text-text-secondary max-w-md">{message}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>Reîncearcă</Button>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`shimmer rounded-md ${className}`} />;
}

/** Honest chip for an alert's evidence, from what the API reports (never assumed). */
export function RedactionChip({ redaction }: { redaction?: string | null }) {
  const kind: ChipKind = redaction === "synthetic" ? "synthetic" : redaction === "full" ? "redacted" : redaction === "heads_only" ? "redacted_heads" : (redaction === "off" || redaction === "none") ? "unredacted" : "unknown";
  return <Chip kind={kind} />;
}
