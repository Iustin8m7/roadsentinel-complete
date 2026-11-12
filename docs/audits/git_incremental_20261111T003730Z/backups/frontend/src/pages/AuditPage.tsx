import { useMemo, useState } from "react";
import { USE_MOCKS } from "@/lib/api";
import { Link } from "react-router";
import { useAuditStore } from "@/store/audit";
import { actor } from "@/store/auth";
import { AUDIT_ACTION_LABEL, ROLE_LABEL } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { BadgePanel } from "@/components/BadgePanel";
import type { AuditAction } from "@/types";
import { AuditVerificationPanel } from "@/components/AuditVerification";
import { ShieldCheck, Download, Filter } from "lucide-react";

export default function AuditPage() {
  const entries = useAuditStore((s) => s.entries);
  const log = useAuditStore((s) => s.log);
  const [user, setUser] = useState("");
  const [action, setAction] = useState<AuditAction | "">("");

  const users = useMemo(() => [...new Set(entries.map((e) => e.username))], [entries]);
  const filtered = entries.filter((e) => (!user || e.username === user) && (!action || e.action === action));

  function exportCsv() {
    const rows = [
      ["data", "utilizator", "rol", "actiune", "tinta", "detalii"],
      ...filtered.map((e) => [e.at, e.username, e.role, e.action, e.target ?? "", e.details ?? ""]),
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
    <div className="flex flex-col gap-4 p-3 sm:p-6">
      {!USE_MOCKS && <AuditVerificationPanel />}
      {/* Top Filter & Export Bar */}
      <div className="card p-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-2 text-text-secondary">
            <Filter className="w-4 h-4" aria-hidden="true" />
            <span className="font-semibold text-text-primary">Filtrează:</span>
          </div>

          <select
            aria-label="Filtru utilizator"
            value={user}
            onChange={(e) => setUser(e.target.value)}
            className="bg-void border border-border text-text-primary text-sm px-3 min-h-[var(--target-min)] rounded-lg"
          >
            <option value="">Toți utilizatorii</option>
            {users.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>

          <select
            aria-label="Filtru acțiune"
            value={action}
            onChange={(e) => setAction(e.target.value as AuditAction | "")}
            className="bg-void border border-border text-text-primary text-sm px-3 min-h-[var(--target-min)] rounded-lg"
          >
            <option value="">Toate acțiunile</option>
            {(Object.keys(AUDIT_ACTION_LABEL) as AuditAction[]).map((a) => (
              <option key={a} value={a}>{AUDIT_ACTION_LABEL[a]}</option>
            ))}
          </select>
        </div>

        <button
          onClick={exportCsv}
          className="press flex items-center gap-2 px-4 min-h-[var(--target-min)] bg-elevation hover:border-action/60 text-sm text-text-primary rounded-lg border border-border font-medium cursor-pointer"
        >
          <Download className="w-4 h-4 text-accent" aria-hidden="true" />
          <span>Exportă CSV</span>
        </button>
      </div>

      {/* Main Audit Table */}
      <BadgePanel
        title={`Jurnal de audit — ${filtered.length} înregistrări`}
        icon={<ShieldCheck className="w-5 h-5 text-ok" aria-hidden="true" />}
        className=""
        contentClassName="p-0 overflow-x-auto"
      >
        <table className="w-full text-left text-sm border-collapse"><caption className="sr-only">Jurnal de audit</caption>
          <thead className="sticky top-0 bg-elevation border-b border-border z-10 text-text-secondary text-xs">
            <tr>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Data și ora (Europa/București)</th>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Utilizator</th>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Rol</th>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Acțiune</th>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Alertă</th>
              <th scope="col" className="py-3 px-4 font-medium eyebrow !text-text-secondary">Detalii</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {filtered.map((e) => (
              <tr key={e.id} className="hover:bg-elevation/60">
                <td className="py-3 px-4 font-mono text-text-secondary whitespace-nowrap">
                  {fmtDateTime(e.at)}
                </td>
                <td className="py-3 px-4 font-semibold text-text-primary">
                  {e.username}
                </td>
                <td className="py-3 px-4 text-text-secondary">
                  {e.role === "anonim" ? "—" : ROLE_LABEL[e.role]}
                </td>
                <td className="py-3 px-4 text-text-primary font-medium">
                  {AUDIT_ACTION_LABEL[e.action]}
                </td>
                <td className="py-3 px-4">
                  {e.target ? (
                    <Link
                      to={`/app/alerte/${e.target}`}
                      className="text-accent hover:underline"
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
