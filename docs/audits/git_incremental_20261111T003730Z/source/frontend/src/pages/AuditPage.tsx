import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useAuditStore } from "@/store/audit";
import { actor } from "@/store/auth";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { BadgePanel } from "@/components/BadgePanel";
import type { AuditAction } from "@/types";
import { ShieldCheck, Download, Filter } from "lucide-react";
import { AuditVerificationPanel } from "@/components/AuditVerification";

export default function AuditPage() {
  const entries = useAuditStore((s) => s.entries);
  const log = useAuditStore((s) => s.log);
  const [user, setUser] = useState("");
  const [action, setAction] = useState<AuditAction | "">("");

  const users = useMemo(() => [...new Set(entries.map((e) => e.username))], [entries]);
  // The real API gives no role per entry; the column appears only when some entry has one.
  const showRole = entries.some((e) => e.role !== "anonim");
  const filtered = entries.filter((e) => (!user || e.username === user) && (!action || e.action === action));

  function exportCsv() {
    const rows = [
      ["data", "utilizator", "rol", "actiune", "tinta", "detalii"],
      ...filtered.map((e) => [e.at, e.username, e.role === "anonim" ? "" : e.role, e.action, e.target ?? "", e.details ?? ""]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), {
      href: url,
      download: `audit-roadsentinel-${new Date().toISOString().slice(0, 10)}.csv`,
    });
    a.click();
    URL.revokeObjectURL(url);
    log({ ...actor(), action: "export", details: `audit CSV, ${filtered.length} rânduri` });
  }

  return (
    <div className="h-full flex flex-col gap-3 p-6 bg-deep-void overflow-hidden">
      {/* Top Filter & Export Bar */}
      <div className="bg-panel border border-border p-3 rounded-md flex items-center justify-between gap-3 shrink-0 shadow-sm">
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-2 text-text-secondary">
            <Filter className="w-3.5 h-3.5" />
            <span className="font-semibold text-text-primary">Filtrează:</span>
          </div>

          <select
            value={user}
            onChange={(e) => setUser(e.target.value)}
            className="bg-deep-void border border-border text-text-primary text-xs px-3 py-1.5 rounded-md focus:outline-none focus:border-accent"
          >
            <option value="">Toți utilizatorii</option>
            {users.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>

          <select
            value={action}
            onChange={(e) => setAction(e.target.value as AuditAction | "")}
            className="bg-deep-void border border-border text-text-primary text-xs px-3 py-1.5 rounded-md focus:outline-none focus:border-accent"
          >
            <option value="">Toate acțiunile</option>
            {(Object.keys(AUDIT_ACTION_LABEL) as AuditAction[]).map((a) => (
              <option key={a} value={a}>{AUDIT_ACTION_LABEL[a]}</option>
            ))}
          </select>
        </div>

        <button
          onClick={exportCsv}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-elevation hover:bg-border text-xs text-text-primary rounded-md border border-border font-medium transition-colors"
        >
          <Download className="w-3.5 h-3.5 text-accent" />
          <span>Exportă CSV</span>
        </button>
      </div>

      <AuditVerificationPanel />

      {/* Main Audit Table */}
      <BadgePanel
        title={`Jurnal de audit — ${filtered.length} înregistrări`}
        icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
        className="flex-1 min-h-0"
        contentClassName="p-0 overflow-y-auto"
      >
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 bg-elevation border-b border-border z-10 font-mono text-text-secondary uppercase text-[11px]">
            <tr>
              <th className="py-2.5 px-4">DATA ȘI ORA</th>
              <th className="py-2.5 px-4">UTILIZATOR</th>
              {showRole && <th className="py-2.5 px-4">ROL</th>}
              <th className="py-2.5 px-4">ACȚIUNE EXECUTATĂ</th>
              <th className="py-2.5 px-4">ȚINTĂ / DOSAR</th>
              <th className="py-2.5 px-4">DETALII OPERAȚIUNE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {filtered.map((e) => (
              <tr key={e.id} className="hover:bg-elevation/60 transition-colors">
                <td className="py-3 px-4 font-mono text-text-secondary whitespace-nowrap">
                  {fmtDateTime(e.at)}
                </td>
                <td className="py-3 px-4 font-semibold text-text-primary">
                  {e.username}
                </td>
                {showRole && (
                  <td className="py-3 px-4 font-mono text-[11px] text-accent">
                    {e.role === "anonim" ? "—" : ROLE_LABEL[e.role].toUpperCase()}
                  </td>
                )}
                <td className="py-3 px-4 text-text-primary font-medium">
                  {AUDIT_ACTION_LABEL[e.action]}
                </td>
                <td className="py-3 px-4">
                  {e.target ? (
                    <Link
                      to={`/app/alerte/${e.target}`}
                      className="font-mono text-xs text-accent hover:underline"
                    >
                      {e.target}
                    </Link>
                  ) : (
                    <span className="text-text-secondary font-mono">—</span>
                  )}
                </td>
                <td className="py-3 px-4 text-text-secondary">
                  {e.details ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </BadgePanel>
    </div>
  );
}
