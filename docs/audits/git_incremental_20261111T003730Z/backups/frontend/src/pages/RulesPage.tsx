import { Banner } from "@/components/ui";
import { useState } from "react";
import { useDataStore } from "@/store/data";
import { useCan } from "@/hooks";
import { ALERT_TYPE, ZONE_KIND_LABEL } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { cameraById } from "@/store/data";
import { BadgePanel } from "@/components/BadgePanel";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { Rule } from "@/types";
import { Sliders, CheckCircle2, XCircle, Edit3 } from "lucide-react";

const THRESHOLD_FIELDS: { key: keyof Rule["thresholds"]; label: string; unit: string }[] = [
  { key: "speedKmh", label: "Viteză", unit: "km/h" },
  { key: "dwellSec", label: "Timp staționare", unit: "s" },
  { key: "distanceM", label: "Distanță", unit: "m" },
  { key: "decelMs2", label: "Decelerare", unit: "m/s²" },
];

export default function RulesPage() {
  const rules = useDataStore((s) => s.rules);
  const toggleRule = useDataStore((s) => s.toggleRule);
  const canEdit = useCan("rules.edit");
  const [editing, setEditing] = useState<string | null>(null);

  return (
    <div className="flex flex-col p-3 sm:p-6 gap-3 bg-void">
      <Banner tone="warn">Demonstrativ: date fictive, fără efect asupra sistemului real.</Banner>
      <BadgePanel
        title={`Reguli și Zone de Monitorizare AI (${rules.length} Reguli)`}
        icon={<Sliders className="w-4 h-4 text-accent" />}
        
        contentClassName="p-3 overflow-y-auto space-y-3"
      >
        {rules.map((r) => (
          <div
            key={r.id}
            className="bg-panel border border-border rounded-md p-4 transition-all hover:border-accent/40 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-xs text-accent font-bold">[{r.id}]</span>
                  <span className="font-bold text-base text-text-primary tracking-wide">
                    {r.name}
                  </span>
                  <SeverityBadge severity={ALERT_TYPE[r.alertType]?.severity || "medium"} />
                </div>

                <div className="mt-1.5 text-xs text-text-secondary">
                  {ALERT_TYPE[r.alertType]?.label} · Zonă: <strong className="text-text-primary">{r.zone.name}</strong> ({ZONE_KIND_LABEL[r.zone.kind]})
                </div>

                <div className="mt-1.5 text-xs font-mono text-caution">
                  Praguri:{" "}
                  {THRESHOLD_FIELDS.filter((f) => r.thresholds[f.key] !== undefined)
                    .map((f) => `${f.label}: ${r.thresholds[f.key]} ${f.unit}`)
                    .join(" · ") || "Fără prag numeric"}
                </div>

                <div className="mt-1.5 text-xs text-text-secondary font-mono">
                  Camere: {r.cameraIds.map((id) => cameraById(id)?.road).filter(Boolean).join(", ") || "Toate"} · actualizat {fmtDateTime(r.updatedAt)} de {r.updatedBy}
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  disabled={!canEdit}
                  onClick={() => toggleRule(r.id)}
                  className={`px-3 py-1 rounded-md text-xs font-mono font-bold transition-all flex items-center gap-1.5 ${
                    r.enabled
                      ? "bg-panel text-ok border border-ok"
                      : "bg-elevation text-text-secondary border border-border"
                  }`}
                >
                  {r.enabled ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>ACTIVĂ</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3.5 h-3.5" />
                      <span>INACTIVĂ</span>
                    </>
                  )}
                </button>

                {canEdit && (
                  <button
                    onClick={() => setEditing(editing === r.id ? null : r.id)}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-elevation hover:bg-border text-text-primary text-xs font-medium border border-border transition-colors"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>{editing === r.id ? "Închide" : "Editează"}</span>
                  </button>
                )}
              </div>
            </div>

            {editing === r.id && <RuleEditor rule={r} onDone={() => setEditing(null)} />}
          </div>
        ))}
      </BadgePanel>
    </div>
  );
}

function RuleEditor({ rule, onDone }: { rule: Rule; onDone: () => void }) {
  const updateRule = useDataStore((s) => s.updateRule);
  const [name, setName] = useState(rule.name);
  const [t, setT] = useState(rule.thresholds);
  const fields = THRESHOLD_FIELDS.filter((f) => rule.thresholds[f.key] !== undefined);

  return (
    <form
      className="mt-4 pt-3 border-t border-border grid gap-3 md:grid-cols-3 text-xs bg-elevation/40 p-3 rounded-md"
      onSubmit={(e) => {
        e.preventDefault();
        updateRule(rule.id, { name, thresholds: t });
        onDone();
      }}
    >
      <div className="md:col-span-3">
        <label className="block text-xs font-mono text-text-secondary mb-1">
          Denumire regulă
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full bg-void border border-border rounded-md px-3 py-1.5 text-text-primary text-xs focus:outline-none focus:border-accent"
        />
      </div>

      {fields.map((f) => (
        <div key={f.key}>
          <label className="block text-xs font-mono text-text-secondary mb-1">
            {f.label} ({f.unit})
          </label>
          <input
            type="number"
            step="any"
            value={t[f.key] ?? ""}
            onChange={(e) => setT({ ...t, [f.key]: e.target.value === "" ? undefined : Number(e.target.value) })}
            className="w-full bg-void border border-border rounded-md px-3 py-1.5 text-text-primary text-xs focus:outline-none focus:border-accent"
          />
        </div>
      ))}

      <div className="md:col-span-3 flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onDone}
          className="px-3 py-1.5 rounded-md bg-elevation hover:bg-border text-text-primary text-xs font-medium border border-border"
        >
          Anulează
        </button>
        <button
          type="submit"
          className="px-4 py-1.5 rounded-md bg-accent hover:bg-accent/90 text-on-accent text-xs font-medium"
        >
          Salvează modificările
        </button>
      </div>
    </form>
  );
}
