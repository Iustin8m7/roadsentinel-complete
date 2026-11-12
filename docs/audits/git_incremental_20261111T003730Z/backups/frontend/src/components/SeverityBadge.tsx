import { Triangle, Diamond, Circle, CircleDashed } from "lucide-react";
import type { Severity } from "@/types";

export interface SeverityBadgeProps {
  severity: Severity | string;
  className?: string;
  /** kept for call-site compatibility; the label is always Romanian only */
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
  dualLabel?: boolean;
}

type Level = "critical" | "high" | "medium" | "info";

const LEVELS: Record<Level, { label: string; cls: string; Icon: typeof Triangle; filled: boolean }> = {
  critical: { label: "Critică", cls: "text-critical bg-critical/10 border-critical/50", Icon: Triangle, filled: true },
  high: { label: "Ridicată", cls: "text-warning bg-warning/10 border-warning/50", Icon: Diamond, filled: true },
  medium: { label: "Medie", cls: "text-caution bg-caution/10 border-caution/50", Icon: Circle, filled: true },
  info: { label: "Informativă", cls: "text-info bg-info/10 border-info/50", Icon: CircleDashed, filled: false },
};

export function severityLevel(s: string): Level {
  const n = (s || "info").toLowerCase();
  if (n === "critical" || n === "critic") return "critical";
  if (n === "high" || n === "ridicat") return "high";
  if (n === "medium" || n === "mediu") return "medium";
  return "info";
}

/** Priority is never color alone: shape + Romanian label + colour. */
export function SeverityBadge({ severity, className = "", showDot = true }: SeverityBadgeProps) {
  const lv = LEVELS[severityLevel(String(severity))];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border ${lv.cls} ${className}`}>
      {showDot && <lv.Icon size={12} aria-hidden="true" fill={lv.filled ? "currentColor" : "none"} />}
      <span>{lv.label}</span>
    </span>
  );
}

export default SeverityBadge;
