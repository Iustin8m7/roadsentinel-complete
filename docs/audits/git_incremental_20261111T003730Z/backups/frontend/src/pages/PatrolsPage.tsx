import { Banner } from "@/components/ui";
import { Link } from "react-router";
import { useDataStore } from "@/store/data";
import { useCan } from "@/hooks";
import { PATROL_STATUS_LABEL } from "@/lib/constants";
import { BadgePanel } from "@/components/BadgePanel";
import type { PatrolStatus } from "@/types";
import { Car, Radio } from "lucide-react";

export default function PatrolsPage() {
  const patrols = useDataStore((s) => s.patrols);
  const setStatus = useDataStore((s) => s.setPatrolStatus);
  const canEdit = useCan("alerts.dispatch");

  const getStatusColor = (st: PatrolStatus) => {
    switch (st) {
      case "available":
        return "bg-panel text-ok border-ok";
      case "en_route":
      case "on_scene":
        return "bg-panel text-caution border-caution";
      case "off_duty":
      default:
        return "bg-text-secondary/20 text-text-secondary border-border";
    }
  };

  return (
    <div className="flex flex-col p-3 sm:p-6 gap-3 bg-void">
      <Banner tone="warn">Demonstrativ: date fictive, fără efect asupra sistemului real.</Banner>
      <BadgePanel
        title={`Echipaje Patrulă Rutieră (${patrols.length} Unități în Tură)`}
        icon={<Radio className="w-4 h-4 text-accent" />}
        
        contentClassName="p-0"
      >
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 bg-elevation border-b border-border z-10 font-mono text-text-secondary text-xs">
            <tr>
              <th className="py-2.5 px-4">INDICATIV UNITATE</th>
              <th className="py-2.5 px-4">VEHICUL SERVICIU</th>
              <th className="py-2.5 px-4">ZONĂ DE PATRULARE</th>
              <th className="py-2.5 px-4">STARE OPERATIVĂ</th>
              <th className="py-2.5 px-4">ALERTĂ CURENTĂ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {patrols.map((p) => (
              <tr key={p.id} className="hover:bg-elevation/60 transition-colors">
                <td className="py-3 px-4 font-mono font-bold text-accent">
                  [{p.callsign}]
                </td>
                <td className="py-3 px-4 text-text-primary font-medium flex items-center gap-2">
                  <Car className="w-3.5 h-3.5 text-text-secondary" />
                  <span>{p.vehicle}</span>
                </td>
                <td className="py-3 px-4 text-text-secondary">{p.area}</td>
                <td className="py-3 px-4">
                  {canEdit ? (
                    <select
                      aria-label={`Stare ${p.callsign}`}
                      value={p.status}
                      onChange={(e) => setStatus(p.id, e.target.value as PatrolStatus)}
                      className="bg-void border border-border text-xs font-semibold py-1 px-2.5 rounded-md text-text-primary focus:outline-none focus:border-accent"
                    >
                      {(Object.keys(PATROL_STATUS_LABEL) as PatrolStatus[]).map((s) => (
                        <option key={s} value={s}>
                          {PATROL_STATUS_LABEL[s]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className={`px-2 py-0.5 rounded text-xs font-mono border ${getStatusColor(p.status)}`}>
                      {PATROL_STATUS_LABEL[p.status]}
                    </span>
                  )}
                </td>
                <td className="py-3 px-4">
                  {p.currentAlertId ? (
                    <Link
                      to={`/app/alerte/${p.currentAlertId}`}
                      className="font-mono text-xs text-accent font-bold hover:underline"
                    >
                      {p.currentAlertId}
                    </Link>
                  ) : (
                    <span className="text-text-secondary font-mono">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </BadgePanel>
    </div>
  );
}
