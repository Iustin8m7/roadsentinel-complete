import { useMemo } from "react";
import { Download, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import { useDataStore, cameraById } from "@/store/data";
import { ALERT_TYPE } from "@/lib/constants";

const DAYS = ["Lun", "Mar", "Mie", "Joi", "Vin", "Sâm", "Dum"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function StatsPage() {

  const alerts = useDataStore((st) => st.alerts);
  const data = useMemo(() => {
    const total = alerts.length;
    const confirmed = alerts.filter((a) => a.status === "confirmed" || a.status === "closed").length;
    const rejected = alerts.filter((a) => a.status === "rejected").length;
    const decided = confirmed + rejected;
    const reaction = alerts.filter((a) => a.decidedAt).map((a) => (new Date(a.decidedAt!).getTime() - new Date(a.createdAt).getTime()) / 1000).filter((x) => x >= 0);
    const avg = reaction.length ? reaction.reduce((x, y) => x + y, 0) / reaction.length : null;
    const sev = { critical: 0, high: 0, medium: 0, info: 0 } as Record<string, number>;
    const byType: Record<string, number> = {};
    const byCam: Record<string, { count: number; worst: number }> = {};
    const heat = Array.from({ length: 7 }, () => Array(24).fill(0) as number[]);
    const rank: Record<string, number> = { critical: 3, high: 2, medium: 1, info: 0 };
    for (const a of alerts) {
      sev[a.severity] = (sev[a.severity] ?? 0) + 1;
      byType[a.type] = (byType[a.type] ?? 0) + 1;
      const c = (byCam[a.cameraId] ??= { count: 0, worst: 0 });
      c.count++; c.worst = Math.max(c.worst, rank[a.severity] ?? 0);
      const d = new Date(a.createdAt);
      heat[(d.getDay() + 6) % 7][d.getHours()]++;
    }
    const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0);
    const gravity = [
      { name: "Critic", value: sev.critical, color: "#FF3B3B", label: `Critic (${pct(sev.critical)}%)` },
      { name: "Ridicat", value: sev.high, color: "#FF8A1F", label: `Ridicat (${pct(sev.high)}%)` },
      { name: "Mediu", value: sev.medium, color: "#FFC23D", label: `Mediu (${pct(sev.medium)}%)` },
      { name: "Info", value: sev.info, color: "#3DA5FF", label: `Info (${pct(sev.info)}%)` },
    ].filter((g) => g.value > 0);
    const sevColor: Record<string, string> = { critical: "#FF3B3B", high: "#FF8A1F", medium: "#FFC23D", info: "#3DA5FF" };
    const maxType = Math.max(1, ...Object.values(byType));
    const types = Object.entries(byType).sort((x, y) => y[1] - x[1]).slice(0, 6).map(([t, n]) => ({
      label: ALERT_TYPE[t as keyof typeof ALERT_TYPE]?.label ?? t, count: n, percentage: Math.round((n / maxType) * 100),
      color: sevColor[ALERT_TYPE[t as keyof typeof ALERT_TYPE]?.severity ?? "info"],
    }));
    const camColors = ["#3DA5FF", "#FFC23D", "#FF8A1F", "#FF3B3B"];
    const cams = Object.entries(byCam).sort((x, y) => y[1].count - x[1].count).map(([id, v]) => ({
      camera: cameraById(id)?.name?.split(" – ")[0] ?? id, count: v.count, color: camColors[v.worst],
    }));
    const maxHeat = Math.max(1, ...heat.flat());
    return { total, confirmedPct: decided ? Math.round((confirmed / decided) * 100) : null, falsePct: decided ? Math.round((rejected / decided) * 100) : null, avg, gravity, types, cams, heat, maxHeat, decided };
  }, [alerts]);
  const fmtAvg = (sec: number | null) => sec === null ? "—" : sec < 60 ? `${Math.round(sec)} s` : `${Math.floor(sec / 60)} min ${Math.round(sec % 60)} s`;
  const GRAVITY_DATA = data.gravity;
  const ALERT_TYPES_DATA = data.types;
  const CAMERAS_BAR_DATA = data.cams;

  // CSV export function
  const handleExportCSV = () => {
    const rows = [
      ["Indicator", "Valoare"],
      ["Total alerte", String(data.total)],
      ["Alerte confirmate", data.confirmedPct === null ? "—" : `${data.confirmedPct}%`],
      ["Timp mediu reactie", fmtAvg(data.avg)],
      ["Alarme false", data.falsePct === null ? "—" : `${data.falsePct}%`],
      ...data.types.map((t) => [t.label, String(t.count)]),
      ...data.cams.map((c) => [`Camera ${c.camera}`, String(c.count)]),
    ];
    const csvContent = "data:text/csv;charset=utf-8," + rows.map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `roadsentinel_raport_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getHeatmapColor = (dayIndex: number, hour: number) => {
    const v = data.heat[dayIndex][hour] / data.maxHeat;
    if (v === 0) return "bg-[#111821]";
    if (v > 0.75) return "bg-[#FF3B3B]";
    if (v > 0.5) return "bg-[#FF8A1F]";
    if (v > 0.25) return "bg-[#FFC23D]";
    return "bg-[#3DA5FF]/50";
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 gap-4 bg-deep-void">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-3">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight text-text-primary uppercase">
            Statistici / Analiză și performanță
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Export Report button */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-elevation hover:bg-border text-xs text-text-primary border border-border transition-colors font-medium"
          >
            <span>Exportă raport</span>
            <Download className="w-3.5 h-3.5 text-text-secondary" />
          </button>
        </div>
      </div>

      {/* Row 1: 4 Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* KPI 1: TOTAL ALERTE */}
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-mono text-text-secondary uppercase">
            <span>TOTAL ALERTE</span>
            <ArrowUpRight className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-heading text-4xl font-bold text-text-primary tracking-tight">
              {data.total.toLocaleString("ro-RO")}
            </span>
            <span className="text-[11px] font-mono text-text-secondary">
              din {data.cams.length} camere
            </span>
          </div>
        </div>

        {/* KPI 2: ALERTĂ CONFIRMATE */}
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-mono text-text-secondary uppercase">
            <span>ALERTĂ CONFIRMATE</span>
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="font-heading text-4xl font-bold text-text-primary tracking-tight">
              {data.confirmedPct === null ? "—" : `${data.confirmedPct}%`}
            </span>
            <span className="text-[11px] font-mono text-text-secondary">
              din {data.decided} decise
            </span>
          </div>
        </div>

        {/* KPI 3: TIMP MEDIU REACȚIE */}
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-mono text-text-secondary uppercase">
            <span>TIMP MEDIU REACȚIE</span>
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <span className="font-heading text-4xl font-bold text-text-primary tracking-tight">
              {fmtAvg(data.avg)}
            </span>
          </div>
        </div>

        {/* KPI 4: ALARME FALSE */}
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-mono text-text-secondary uppercase">
            <span>ALARME FALSE</span>
            <ArrowDownRight className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <span className="font-heading text-4xl font-bold text-text-primary tracking-tight">
              {data.falsePct === null ? "—" : `${data.falsePct}%`}
            </span>
          </div>
        </div>
      </div>

      {/* Row 2: Middle Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 flex-1 min-h-0">
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col min-h-0">
          <div className="text-xs font-mono uppercase text-text-secondary font-semibold mb-2">
            ALERTE PE GRAVITATE
          </div>

          <div className="flex-1 min-h-0 flex items-center justify-between gap-4">
            <div className="flex-1 h-44 relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={GRAVITY_DATA}
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {GRAVITY_DATA.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="#111821" strokeWidth={2} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="w-44 space-y-2.5 text-xs font-mono">
              {GRAVITY_DATA.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-sm flex-shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-text-primary">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
          <div className="text-xs font-mono uppercase text-text-secondary font-semibold mb-2">
            ALERTE PE TIP
          </div>

          <div className="space-y-3 my-auto">
            {ALERT_TYPES_DATA.map((row) => (
              <div key={row.label} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-text-primary">{row.label}</span>
                  <span className="font-mono text-text-secondary">{row.count}</span>
                </div>
                <div className="w-full h-2.5 bg-deep-void rounded-full overflow-hidden border border-border/40">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${row.percentage}%`,
                      backgroundColor: row.color,
                      boxShadow: `0 0 10px ${row.color}66`
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 3: Bottom Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 flex-1 min-h-0">
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col min-h-0">
          <div className="text-xs font-mono uppercase text-text-secondary font-semibold mb-2">
            ALERTE PE CAMERĂ
          </div>

          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={CAMERAS_BAR_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="camera"
                  tick={{ fill: "#7D8A9B", fontSize: 10, fontFamily: "Geist Mono" }}
                  axisLine={{ stroke: "#1E2A36" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#7D8A9B", fontSize: 10, fontFamily: "Geist Mono" }}
                  axisLine={{ stroke: "#1E2A36" }}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#17202B",
                    borderColor: "#1E2A36",
                    borderRadius: "8px",
                    color: "#E6EDF3",
                    fontSize: "12px",
                    fontFamily: "Geist Mono"
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {CAMERAS_BAR_DATA.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between overflow-x-auto">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-text-secondary font-semibold mb-2">
            <span>Distribuție oră × zi</span>
            <span className="text-[10px] text-text-secondary">Inter 00–23</span>
          </div>

          <div className="min-w-[500px]">
            <div className="flex items-center pl-8 mb-1 gap-1">
              {HOURS.map((h) => {
                const isHighlight = h === 17 || h === 18;
                return (
                  <div
                    key={h}
                    className={`flex-1 text-center text-[9px] font-mono ${
                      isHighlight ? "text-amber-400 font-bold" : "text-text-secondary"
                    }`}
                  >
                    {h < 10 ? `0${h}` : h}
                  </div>
                );
              })}
            </div>

            <div className="space-y-1">
              {DAYS.map((day, dayIdx) => (
                <div key={day} className="flex items-center gap-1">
                  <span className="w-7 text-[10px] font-mono text-text-secondary text-right pr-1">
                    {day}
                  </span>
                  {HOURS.map((h) => (
                    <div
                      key={`${day}-${h}`}
                      title={`${day} ${h}:00 – ${data.heat[dayIdx][h]} alerte`}
                      className={`flex-1 h-3.5 rounded-xs transition-colors hover:scale-110 cursor-pointer ${getHeatmapColor(
                        dayIdx,
                        h
                      )}`}
                    />
                  ))}
                </div>
              ))}
            </div>

            <div className="flex items-center pl-8 mt-1.5 gap-1">
              {HOURS.map((h) => (
                <div key={`b-${h}`} className="flex-1 text-center text-[8px] font-mono text-text-secondary/60">
                  {h % 2 === 0 ? (h < 10 ? `0${h}` : h) : ""}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
