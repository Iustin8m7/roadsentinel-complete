<<<<<<< INTEGRATION
import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { useDataStore, cameraById } from "@/store/data";
import { ALERT_TYPE } from "@/lib/constants";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { EmptyState } from "@/components/ui";
import { api, USE_MOCKS } from "@/lib/api";
=======
import { useMemo } from "react";
import { Download, Printer } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import { useDataStore, cameraById } from "@/store/data";
import { ALERT_TYPE } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { ActivityReport } from "@/components/ActivityReport";
>>>>>>> GITHUB_TARGET

const DAYS = ["Lun", "Mar", "Mie", "Joi", "Vin", "Sâm", "Dum"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

interface Dist { n: number; median_s: number | null; p90_s: number | null }
interface ResponseStats { alerts: number; never_viewed: number; time_to_first_view: Dist; time_to_decision: Dist; rejection_rate: number | null; rejection_rate_n: number }
const fmtSec = (v: number | null) => (v === null ? "—" : v < 90 ? `${Math.round(v)} s` : v < 5400 ? `${Math.round(v / 60)} min` : `${(v / 3600).toFixed(1)} h`);

/** Measured from timestamps the server stored (alert creation -> first operator view / decision),
 *  last 24 h, with the sample size next to every figure. Nothing here is estimated. */
function ResponseTimes() {
  const [data, setData] = useState<ResponseStats | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (USE_MOCKS) return;
    api<ResponseStats>("/api/stats/response?since_hours=24").then(setData).catch(() => setFailed(true));
  }, []);
  if (USE_MOCKS) return <p className="text-xs text-text-muted" role="note">Timpii de răspuns măsurați nu sunt disponibili în modul demonstrativ.</p>;
  if (failed) return <p className="text-xs text-caution" role="note">Timpii de răspuns nu au putut fi încărcați.</p>;
  if (!data) return null;
  const row = (label: string, d: Dist) => (
    <div className="card px-4 py-3 flex flex-col gap-1">
      <span className="eyebrow">{label}</span>
      <div className="num text-3xl font-bold">{fmtSec(d.median_s)}</div>
      <span className="text-xs text-text-muted">mediană · p90 {fmtSec(d.p90_s)} · n = {d.n}</span>
    </div>
  );
  return (
    <section aria-label="Timpi de răspuns măsurați (24 h)" className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {row("De la crearea alertei până la prima vizualizare", data.time_to_first_view)}
      {row("De la crearea alertei până la decizie", data.time_to_decision)}
      <div className="card px-4 py-3 flex flex-col gap-1">
        <span className="eyebrow">Nevăzute încă</span>
        <div className="num text-3xl font-bold">{data.never_viewed}</div>
        <span className="text-xs text-text-muted">din {data.alerts} alerte în ultimele 24 h</span>
      </div>
    </section>
  );
}

export default function StatsPage() {

  const alerts = useDataStore((st) => st.alerts);
  const [hover, setHover] = useState<string | null>(null);
  const data = useMemo(() => {
    const total = alerts.length;
    const confirmed = alerts.filter((a) => a.status === "confirmed" || a.status === "closed").length;
    const rejected = alerts.filter((a) => a.status === "rejected").length;
    const pending = total - confirmed - rejected;
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
    const gravity = [
<<<<<<< INTEGRATION
      { name: "Critic", value: sev.critical, color: "var(--sev-critical)", label: `Critic (${pct(sev.critical)}%)` },
      { name: "Ridicat", value: sev.high, color: "var(--sev-high)", label: `Ridicat (${pct(sev.high)}%)` },
      { name: "Mediu", value: sev.medium, color: "var(--sev-medium)", label: `Mediu (${pct(sev.medium)}%)` },
      { name: "Info", value: sev.info, color: "var(--sev-info)", label: `Info (${pct(sev.info)}%)` },
=======
      { name: "Critic", value: sev.critical, color: "#FF3B3B", label: `Critic · ${sev.critical}` },
      { name: "Ridicat", value: sev.high, color: "#FF8A1F", label: `Ridicat · ${sev.high}` },
      { name: "Mediu", value: sev.medium, color: "#FFC23D", label: `Mediu · ${sev.medium}` },
      { name: "Info", value: sev.info, color: "#3DA5FF", label: `Info · ${sev.info}` },
>>>>>>> GITHUB_TARGET
    ].filter((g) => g.value > 0);
    const sevColor: Record<string, string> = { critical: "var(--sev-critical)", high: "var(--sev-high)", medium: "var(--sev-medium)", info: "var(--sev-info)" };
    const maxType = Math.max(1, ...Object.values(byType));
    const allTypes = Object.entries(byType).sort((x, y) => y[1] - x[1]).map(([t, n]) => ({
      label: ALERT_TYPE[t as keyof typeof ALERT_TYPE]?.label ?? t, count: n, percentage: Math.round((n / maxType) * 100),
      color: sevColor[ALERT_TYPE[t as keyof typeof ALERT_TYPE]?.severity ?? "info"],
    }));
<<<<<<< INTEGRATION
    const camColors = ["var(--sev-info)", "var(--sev-medium)", "var(--sev-high)", "var(--sev-critical)"];
    const cams = Object.entries(byCam).sort((x, y) => y[1].count - x[1].count).slice(0, 8).map(([id, v]) => ({
      camera: cameraById(id)?.name?.split(" – ")[0] ?? id, count: v.count, color: camColors[v.worst],
=======
    const types = allTypes.slice(0, 6);
    const camColors = ["#3DA5FF", "#FFC23D", "#FF8A1F", "#FF3B3B"];
    const cams = Object.entries(byCam).sort((x, y) => y[1].count - x[1].count).map(([id, v]) => ({
      camera: cameraById(id)?.name?.split(" – ")[0] ?? id, fullName: cameraById(id)?.name ?? id, count: v.count, color: camColors[v.worst],
>>>>>>> GITHUB_TARGET
    }));
    const maxCam = Math.max(1, ...cams.map((c) => c.count));
    const camsPct = cams.map((c) => ({ ...c, percentage: Math.round((c.count / maxCam) * 100) }));
    const maxHeat = Math.max(1, ...heat.flat());
<<<<<<< INTEGRATION
    return { total, confirmedPct: decided ? Math.round((confirmed / decided) * 100) : null, falsePct: decided ? Math.round((rejected / decided) * 100) : null, avg, gravity, types, cams: camsPct, camCount: Object.keys(byCam).length, heat, maxHeat, decided };
=======
    const hours = HOURS.map((h) => heat.reduce((sum, day) => sum + day[h], 0));
    const times = alerts.map((a) => new Date(a.createdAt).getTime()).filter((t) => Number.isFinite(t)).sort((x, y) => x - y);
    const day = (t: number) => fmtDateTime(new Date(t).toISOString()).slice(0, 10);
    const period = !times.length ? "nu există alerte în datele încărcate"
      : day(times[0]) === day(times[times.length - 1]) ? day(times[0]) : `${day(times[0])} – ${day(times[times.length - 1])}`;
    return { total, confirmed, rejected, pending, gravity, types, allTypes, cams, heat, maxHeat, hours, period };
>>>>>>> GITHUB_TARGET
  }, [alerts]);
  const totals = [
    { label: "Total alerte", count: data.total, note: `din ${data.cams.length} camere` },
    { label: "Alerte confirmate", count: data.confirmed, note: "decizia dispecerului" },
    { label: "Alerte respinse", count: data.rejected, note: "decizia dispecerului" },
    { label: "În așteptare", count: data.pending, note: "fără decizie încă" },
  ];
  const GRAVITY_DATA = data.gravity;
  const ALERT_TYPES_DATA = data.types;
  const CAMERAS_BAR_DATA = data.cams;

  // CSV export function
  const handleExportCSV = () => {
    const rows = [
      ["Indicator", "Valoare"],
<<<<<<< INTEGRATION
      ["Total alerte", String(data.total)],
      ["Alerte confirmate", data.confirmedPct === null ? "—" : `${data.confirmedPct}%`],
      ["Timp mediu pana la decizie (de la momentul evenimentului)", fmtAvg(data.avg)],
      ["Respinse din decise", data.falsePct === null ? "—" : `${data.falsePct}%`],
      ...data.types.map((t) => [t.label, String(t.count)]),
=======
      ...totals.map((t) => [t.label, String(t.count)]),
      ...data.allTypes.map((t) => [t.label, String(t.count)]),
>>>>>>> GITHUB_TARGET
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


  const SHADES = ["bg-elevation", "bg-action/20", "bg-action/40", "bg-action/65", "bg-action"];
  const shade = (d: number, h: number) => {
    const n = data.heat[d][h];
    return n === 0 ? SHADES[0] : SHADES[Math.min(4, 1 + Math.floor(((n - 1) / data.maxHeat) * 4))];
  };
  const peak = (() => {
    let best = { d: 0, h: 0, n: 0 };
    data.heat.forEach((row, d) => row.forEach((n, h) => { if (n > best.n) best = { d, h, n }; }));
    return best;
  })();

  // Donut: arcs are SVG circles with stroke-dasharray (attributes only, no inline styles).
  const R = 52, C = 2 * Math.PI * R;
  let acc = 0;
  const arcs = GRAVITY_DATA.map((g) => {
    const len = data.total ? (g.value / data.total) * C : 0;
    const arc = { ...g, len, off: -acc };
    acc += len;
    return arc;
  });

  const tile = "card px-4 py-4 flex flex-col gap-1";
  const eyebrow = "eyebrow";
  const bars = (rows: { label?: string; camera?: string; count: number; percentage: number; color: string }[]) => (
    <ul className="flex flex-col gap-3.5 stagger">
      {rows.map((row) => {
        const name = row.label ?? row.camera ?? "";
        return (
          <li key={name} className="flex flex-col gap-1.5">
            <div className="flex justify-between text-sm">
              <span className="text-text-primary truncate pr-3">{name}</span>
              <span className="font-mono tabular-nums text-text-secondary">{row.count}</span>
            </div>
            <svg role="img" aria-label={`${name}: ${row.count}`} viewBox="0 0 100 8" preserveAspectRatio="none" className="w-full h-2.5 rounded-full overflow-hidden bg-void/70">
              <rect className="bar-grow" x="0" y="0" width={Math.max(2, row.percentage)} height="8" rx="4" fill={row.color} />
            </svg>
          </li>
        );
      })}
    </ul>
  );

  return (
    <div className="flex flex-col p-3 sm:p-6 gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
<<<<<<< INTEGRATION
          <p className="eyebrow">Analiză</p>
          <h1 className="font-display text-3xl font-bold tracking-tight text-text-primary">Statistici</h1>
          <p className="text-sm text-text-secondary mt-1">Calculat din cele {data.total} alerte încărcate în sesiune, nu dintr-o perioadă fixă.</p>
=======
          <h1 className="font-heading text-3xl font-bold tracking-tight text-text-primary uppercase">
            Statistici / Analiză și performanță
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-[#3DA5FF] hover:bg-[#2C94F0] text-xs text-[#0A0E14] font-bold transition-colors cursor-pointer"
          >
            <span>Tipărește raportul</span>
            <Printer className="w-3.5 h-3.5" />
          </button>
          {/* Export Report button */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-elevation hover:bg-border text-xs text-text-primary border border-border transition-colors font-medium"
          >
            <span>Exportă CSV</span>
            <Download className="w-3.5 h-3.5 text-text-secondary" />
          </button>
>>>>>>> GITHUB_TARGET
        </div>
        <button onClick={handleExportCSV} className="press flex items-center gap-2 px-4 min-h-[var(--target-min)] rounded-lg bg-elevation hover:border-action/60 text-sm text-text-primary border border-border font-medium cursor-pointer">
          <span>Exportă raport</span>
          <Download className="w-4 h-4 text-text-secondary" aria-hidden="true" />
        </button>
      </div>

<<<<<<< INTEGRATION
      <ResponseTimes />

      {data.total === 0 ? (
        <div className="card"><EmptyState title="Nicio alertă încărcată" hint="Statisticile apar după ce există alerte în sesiune." /></div>
      ) : (<>
      <div className="stagger grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className={tile}>
          <span className={eyebrow}>Total alerte</span>
          <div className="flex items-baseline gap-2"><span className="text-5xl font-bold"><AnimatedNumber value={data.total} /></span></div>
          <span className="text-xs text-text-muted">din {data.camCount} camere</span>
        </div>
        <div className={tile}>
          <span className={eyebrow}>Alerte confirmate</span>
          <div className="text-5xl font-bold">{data.confirmedPct === null ? "—" : <><AnimatedNumber value={data.confirmedPct} /><span className="text-2xl text-text-secondary">%</span></>}</div>
          <span className="text-xs text-text-muted">din {data.decided} decise</span>
        </div>
        <div className={tile}>
          <span className={eyebrow}>Timp mediu până la decizie</span>
          <div className="num text-5xl font-bold">{fmtAvg(data.avg)}</div>
          <span className="text-xs text-text-muted">de la momentul evenimentului (nu de la crearea alertei)</span>
        </div>
        <div className={tile}>
          <span className={eyebrow}>Respinse din decise</span>
          <div className="text-5xl font-bold">{data.falsePct === null ? "—" : <><AnimatedNumber value={data.falsePct} /><span className="text-2xl text-text-secondary">%</span></>}</div>
          <span className="text-xs text-text-muted">din {data.decided} decise</span>
        </div>
=======
      {/* Row 1: plain counts; no percentage that could read as an accuracy figure */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {totals.map((kpi) => (
          <div key={kpi.label} className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between">
            <div className="text-xs font-mono text-text-secondary uppercase">{kpi.label}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-heading text-4xl font-bold text-text-primary tracking-tight">
                {kpi.count.toLocaleString("ro-RO")}
              </span>
              <span className="text-[11px] font-mono text-text-secondary">{kpi.note}</span>
            </div>
          </div>
        ))}
>>>>>>> GITHUB_TARGET
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        <section aria-labelledby="g-h" className="card p-5">
          <h2 id="g-h" className="font-display text-lg font-semibold mb-4">Alerte pe gravitate</h2>
          <div className="flex items-center gap-6 flex-wrap justify-center sm:justify-start">
            <svg viewBox="0 0 140 140" role="img" aria-label={`Total ${data.total} alerte, pe gravitate`} className="w-44 h-44 shrink-0 -rotate-90">
              <circle cx="70" cy="70" r={R} fill="none" stroke="var(--bg-elevation)" strokeWidth="16" />
              {arcs.map((a) => (
                <circle key={a.name} className="donut-arc" cx="70" cy="70" r={R} fill="none" stroke={a.color} strokeWidth="16" strokeDasharray={`${Math.max(0, a.len - 2)} ${C}`} strokeDashoffset={a.off} onMouseEnter={() => setHover(a.label)} onMouseLeave={() => setHover(null)}>
                  <title>{a.label}: {a.value}</title>
                </circle>
              ))}
            </svg>
            <ul className="flex flex-col gap-2.5 text-sm min-w-44">
              {GRAVITY_DATA.map((item) => (
                <li key={item.name} className={`flex items-center gap-2.5 ${hover === item.label ? "font-semibold" : ""}`}>
                  <span className="w-3 h-3 rounded-sm shrink-0 border border-border" aria-hidden="true" ><svg viewBox="0 0 10 10" className="w-full h-full block"><rect width="10" height="10" fill={item.color} /></svg></span>
                  <span className="text-text-primary">{item.label}</span>
                  <span className="ml-auto font-mono tabular-nums text-text-secondary">{item.value}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="t-h" className="card p-5">
          <h2 id="t-h" className="font-display text-lg font-semibold mb-4">Alerte pe tip</h2>
          {bars(ALERT_TYPES_DATA)}
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        <section aria-labelledby="c-h" className="card p-5">
          <h2 id="c-h" className="font-display text-lg font-semibold mb-4">Alerte pe cameră <span className="text-xs font-sans font-normal text-text-muted">(cele mai multe 8)</span></h2>
          {bars(CAMERAS_BAR_DATA)}
        </section>

<<<<<<< INTEGRATION
        <section role="region" aria-labelledby="h-h" tabIndex={0} className="card p-5 overflow-x-auto">
          <div className="flex items-baseline justify-between gap-3 mb-1">
            <h2 id="h-h" className="font-display text-lg font-semibold">Distribuție oră × zi</h2>
            <span className="text-xs text-text-secondary">00–23, ora locală a browserului</span>
          </div>
          <p className="text-xs text-text-secondary mb-3 min-h-4" aria-live="polite">
            {hover && hover.includes("alerte") ? hover : peak.n > 0 ? `Cele mai multe alerte: ${DAYS[peak.d]}, ${String(peak.h).padStart(2, "0")}:00 (${peak.n}).` : ""}
          </p>
          <div className="min-w-[520px]">
            <div className="flex items-center pl-9 mb-1 gap-1">
              {HOURS.map((h) => <div key={h} className="flex-1 text-center text-xs font-mono text-text-secondary">{h % 3 === 0 ? String(h).padStart(2, "0") : ""}</div>)}
=======
        <div className="rounded-md bg-panel border border-border p-4 flex flex-col justify-between overflow-x-auto">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-text-secondary font-semibold mb-2">
            <span>Distribuție oră × zi</span>
            <span className="text-[10px] text-text-secondary">Interval orar 00–23</span>
          </div>

          <div className="min-w-[500px]">
            <div className="flex items-center pl-8 mb-1 gap-1">
              {HOURS.map((h) => (
                <div key={h} className="flex-1 text-center text-[9px] font-mono text-text-secondary">
                  {h < 10 ? `0${h}` : h}
                </div>
              ))}
>>>>>>> GITHUB_TARGET
            </div>
            <div className="space-y-1">
              {DAYS.map((day, dayIdx) => (
                <div key={day} className="flex items-center gap-1">
                  <span className="w-8 text-xs font-mono text-text-secondary text-right pr-1">{day}</span>
                  {HOURS.map((h) => (
                    <div key={`${day}-${h}`} title={`${day} ${String(h).padStart(2, "0")}:00: ${data.heat[dayIdx][h]} alerte`}
                      onMouseEnter={() => setHover(`${day} ${String(h).padStart(2, "0")}:00: ${data.heat[dayIdx][h]} alerte`)} onMouseLeave={() => setHover(null)}
                      className={`flex-1 h-5 rounded-[3px] hover:ring-2 hover:ring-text-primary ${shade(dayIdx, h)}`} />
                  ))}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-3 pl-9 text-xs text-text-secondary" aria-hidden="true">
              <span>Mai puține</span>{SHADES.map((c) => <span key={c} className={`w-5 h-3 rounded-[3px] border border-border-subtle ${c}`} />)}<span>Mai multe</span>
            </div>
          </div>
        </section>
      </div>
<<<<<<< INTEGRATION
      </>)}
=======

      <ActivityReport
        period={data.period}
        generatedAt={fmtDateTime(new Date().toISOString()).slice(0, 16)}
        totals={totals}
        cameras={data.cams.map((c) => ({ label: c.fullName, count: c.count }))}
        types={data.allTypes}
        hours={data.hours}
      />
>>>>>>> GITHUB_TARGET
    </div>
  );
}
