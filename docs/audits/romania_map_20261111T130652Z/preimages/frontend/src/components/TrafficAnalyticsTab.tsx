import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, LoaderCircle, RotateCcw } from "lucide-react";
import { api, apiUrl, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

type Recording = { id: string; original_filename: string; width: number; height: number; duration_ms: number };
type Run = {
  id: string;
  status: string;
  configuration: { sample_fps: number; confidence: number };
  model_id: string;
  model_sha256: string;
  has_analytics: boolean;
  observation_count: number;
};
type Summary = {
  analysis_run_id: string; status: string; partial: boolean; source_width: number; source_height: number;
  source_duration_s: number; crop: { x: number; y: number; width: number; height: number };
  sample_fps: number; inference_fps: number; processed_samples: number; sampled_span_s: [number, number] | null;
  sample_coverage_seconds: number; sample_coverage_ratio: number;
  model_name: string; model_sha256: string; confidence: number;
  observation_totals_by_class: Record<string, number>;
  estimated_tracker_id_totals_by_class: Record<string, number>;
  line_crossings: Record<string, number> | null; warnings: string[]; available_metrics: string[];
};
type Heatmap = {
  grid_width: number; grid_height: number; values: number[]; max_value: number; total_weight: number;
  included_observations: number; processed_samples: number; missing_data: boolean;
  normalization: string; observation_totals_by_class: Record<string, number>;
};
type TimelineBin = {
  start_s: number; end_s: number; observations_by_class: Record<string, number>;
  vehicle_seconds_by_class: Record<string, number>; sampled_frames: number; coverage_flag: string;
};
type Timeline = { bins: TimelineBin[]; bin_seconds: number; warnings: string[] };
type Metric = "observations" | "presence_seconds";
const CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle"] as const;
const LABEL: Record<(typeof CLASSES)[number], string> = {
  car: "Autoturisme", truck: "Camioane", bus: "Autobuze", motorcycle: "Motociclete", bicycle: "Biciclete",
};
const COLOR: Record<(typeof CLASSES)[number], string> = {
  car: "#31d18b", truck: "#50a7ff", bus: "#f5b642", motorcycle: "#db75ef", bicycle: "#43d5dc",
};
const clock = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

export default function TrafficAnalyticsTab({ recording, run }: { recording: Recording; run: Run }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [heat, setHeat] = useState<Heatmap | null>(null);
  const [series, setSeries] = useState<Timeline | null>(null);
  const [classes, setClasses] = useState<string[]>([...CLASSES]);
  const [startText, setStartText] = useState("0");
  const [endText, setEndText] = useState(String(recording.duration_ms / 1000));
  const [mode, setMode] = useState<Metric>("observations");
  const [opacity, setOpacity] = useState(62);
  const [radius, setRadius] = useState(0.03);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);
  const canvas = useRef<HTMLCanvasElement>(null);
  const duration = recording.duration_ms / 1000;
  const start = Number(startText), end = Number(endText);
  const validRange = Number.isFinite(start) && Number.isFinite(end) && start >= 0 && start < end && end <= duration;
  const query = useMemo(() => {
    if (!validRange) return "";
    const params = new URLSearchParams({ start_s: String(start), end_s: String(end), classes: classes.join(",") });
    return params.toString();
  }, [validRange, start, end, classes]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setSummary(null);
    void api<Summary>(`/api/recordings/${recording.id}/analyses/${run.id}/analytics/summary`, { signal: controller.signal })
      .then((value) => {
        setSummary(value);
        setEndText(String(value.source_duration_s));
      })
      .catch((err) => { if (!controller.signal.aborted) setError(err instanceof ApiError && err.status === 409 ? "Datele structurate nu există pentru această rulare. Reanalizează înregistrarea pentru a genera observațiile." : "Rezumatul analitic nu este disponibil pentru această rulare."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [recording.id, run.id]);

  useEffect(() => {
    if (!summary || !query) return;
    const controller = new AbortController();
    const route = `/api/recordings/${recording.id}/analyses/${run.id}/analytics`;
    const heatParams = new URLSearchParams(query);
    heatParams.set("mode", mode); heatParams.set("radius", String(radius)); heatParams.set("grid_width", "128");
    const timelineParams = new URLSearchParams(query); timelineParams.set("bin_seconds", "5");
    setError(""); setHeat(null); setSeries(null);
    void Promise.all([
      api<Heatmap>(`${route}/heatmap?${heatParams}`, { signal: controller.signal }),
      api<Timeline>(`${route}/timeline?${timelineParams}`, { signal: controller.signal }),
    ]).then(([h, t]) => { setHeat(h); setSeries(t); })
      .catch((err) => { if (!controller.signal.aborted) setError(err instanceof ApiError ? err.message : "Filtrarea analiticelor a eșuat."); });
    return () => controller.abort();
  }, [recording.id, run.id, summary, query, mode, radius, refreshToken]);

  useEffect(() => {
    if (!heat || !canvas.current) return;
    const node = canvas.current;
    node.width = heat.grid_width; node.height = heat.grid_height;
    const context = node.getContext("2d");
    if (!context) return;
    const image = context.createImageData(heat.grid_width, heat.grid_height);
    const max = heat.max_value;
    heat.values.forEach((value, index) => {
      if (value <= 0 || max <= 0) return;
      const t = clamp(value / max, 0, 1);
      const stops = t < 0.5
        ? [40 + 215 * t * 2, 190 + 25 * t * 2, 255 - 125 * t * 2]
        : [255, 215 - 160 * (t - 0.5) * 2, 130 - 110 * (t - 0.5) * 2];
      const offset = index * 4;
      image.data[offset] = stops[0]; image.data[offset + 1] = stops[1]; image.data[offset + 2] = stops[2];
      image.data[offset + 3] = Math.round(255 * (opacity / 100) * (0.14 + 0.72 * Math.sqrt(t)));
    });
    context.putImageData(image, 0, 0);
  }, [heat, opacity]);

  const toggleClass = (name: string) => setClasses((old) => old.includes(name)
    ? old.length === 1 ? old : old.filter((item) => item !== name)
    : [...old, name]);
  const selectBin = (bin: TimelineBin) => { setStartText(String(bin.start_s)); setEndText(String(bin.end_s)); };
  const toggleAll = () => setClasses((old) => old.length === CLASSES.length ? ["car"] : [...CLASSES]);
  const totals = heat?.observation_totals_by_class ?? {};
  const trackerTotals = summary?.estimated_tracker_id_totals_by_class ?? {};
  const selectedFramePts = summary?.sampled_span_s?.[0] ?? 0;
  const maxBin = Math.max(1, ...(series?.bins.map((bin) => CLASSES.reduce((total, name) => total + (mode === "observations" ? (bin.observations_by_class[name] ?? 0) : (bin.vehicle_seconds_by_class[name] ?? 0)), 0)) ?? [1]));

  if (loading) return <div className="grid min-h-48 place-items-center text-sm text-text-secondary"><LoaderCircle className="mr-2 animate-spin"/>Se încarcă analiticele înregistrării…</div>;
  if (error && !summary) return <div role="status" className="rounded-xl border border-caution/40 bg-caution/5 p-5"><p className="flex items-center gap-2 font-semibold text-caution"><AlertTriangle size={17}/> Analitice indisponibile</p><p className="mt-2 text-sm text-text-secondary">{error}</p><p className="mt-2 text-xs text-text-muted">Rulare {run.id} · {run.status.toUpperCase()} · fără date simulate.</p></div>;
  if (!summary) return null;

  return <div className="space-y-5" aria-label="Analiză trafic înregistrat">
    {error && <p role="alert" className="rounded-lg border border-critical/30 bg-critical/10 p-3 text-sm text-critical">{error}</p>}
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="eyebrow">RECORDED VIDEO ANALYSIS</p><h3 className="font-display text-xl font-semibold">Analitice trafic</h3><p className="mt-1 text-xs text-text-secondary">{recording.original_filename} · {recording.width}×{recording.height} · {clock(duration)} sursă · {summary.processed_samples} cadre eșantionate</p></div><span className="rounded-full border border-ok/30 bg-ok/10 px-3 py-1.5 text-xs font-semibold text-ok">DATE COMPLETE · {summary.processed_samples} mostre</span></div>

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Observații YOLOX" value={String(run.observation_count)} note="Detecții de vehicule în cadrele eșantionate; nu vehicule unice."/>
      <Metric label="Cadre analizate" value={summary.processed_samples.toLocaleString("ro-RO")} note={`Eșantionare solicitată: ${summary.sample_fps} cadre/s.`}/>
      <Metric label="ID-uri tracker estimate" value={JSON.stringify(trackerTotals)} note="ID-urile pot fragmenta un vehicul în mai multe track-uri."/>
      <Metric label="Traversări linie" value={summary.line_crossings ? JSON.stringify(summary.line_crossings) : "Neconfigurată"} note="Nu reprezintă volumul total al traficului."/>
    </div>

    <section className="space-y-4 rounded-xl border border-border bg-elevation/25 p-4" aria-label="Filtre analitice">
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-xs text-text-secondary">Metrică spatială<select aria-label="Metrică spatială" value={mode} onChange={(e) => setMode(e.target.value as Metric)} className="mt-1 min-h-10 rounded-lg border border-border bg-panel px-3 text-sm text-text-primary"><option value="observations">Densitate observații</option><option value="presence_seconds">Prezență vizuală estimată (s)</option></select></label>
        <label className="text-xs text-text-secondary">Început PTS (s)<input aria-label="Început interval sursă" type="number" min={0} max={duration} step={0.1} value={startText} onChange={(e) => setStartText(e.target.value)} className="mt-1 block min-h-10 w-32 rounded-lg border border-border bg-panel px-3 font-mono text-sm text-text-primary"/></label>
        <label className="text-xs text-text-secondary">Sfârșit PTS (s)<input aria-label="Sfârșit interval sursă" type="number" min={0} max={duration} step={0.1} value={endText} onChange={(e) => setEndText(e.target.value)} className="mt-1 block min-h-10 w-32 rounded-lg border border-border bg-panel px-3 font-mono text-sm text-text-primary"/></label>
        <label className="text-xs text-text-secondary">Opacitate {opacity}%<input aria-label="Opacitate heatmap" type="range" min={0} max={100} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} className="mt-2 block w-36 accent-action"/></label>
        <label className="text-xs text-text-secondary">Rază de netezire<select aria-label="Rază de netezire" value={radius} onChange={(e) => setRadius(Number(e.target.value))} className="mt-1 min-h-10 rounded-lg border border-border bg-panel px-3 text-sm text-text-primary"><option value={0.02}>Mică · 2% din lățime</option><option value={0.03}>Medie · 3%</option><option value={0.05}>Mare · 5%</option></select></label>
        <Button variant="secondary" size="sm" onClick={() => { setClasses([...CLASSES]); setStartText("0"); setEndText(String(duration)); setMode("observations"); setRadius(0.03); setOpacity(62); setRefreshToken((value) => value + 1); }}><RotateCcw size={14}/> Resetează</Button>
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtru categorii vehicule">
        <button type="button" aria-pressed={classes.length === CLASSES.length} onClick={toggleAll} className={`rounded-full border px-3 py-1.5 text-xs ${classes.length === CLASSES.length ? "border-action bg-action/10 text-action" : "border-border text-text-secondary"}`}>Toate</button>
        {CLASSES.map((name) => <button key={name} type="button" aria-pressed={classes.includes(name)} onClick={() => toggleClass(name)} className="rounded-full border px-3 py-1.5 text-xs" style={{ borderColor: classes.includes(name) ? COLOR[name] : "var(--border)", color: classes.includes(name) ? COLOR[name] : undefined }}>{LABEL[name]}</button>)}
      </div>
      {!validRange && <p role="alert" className="text-xs text-critical">Intervalul trebuie să fie crescător și în interiorul duratei înregistrării.</p>}
      {validRange && <p className="text-[11px] text-text-muted">Timp sursă selectat: {clock(start)}–{clock(end)} · limite [început, sfârșit), ultimul capăt inclus numai la sfârșitul înregistrării.</p>}
    </section>

    {validRange && <>
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="overflow-hidden rounded-xl border border-border bg-panel">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border p-3"><div><h4 className="font-semibold">{mode === "observations" ? "Densitate spațială a observațiilor" : "Prezență vizuală estimată"}</h4><p className="text-[11px] text-text-secondary">Ancore bottom-center · coordonate normalizate pe cadrul original</p></div><span className="text-[11px] text-text-muted">Scală per filtru · maxim {heat?.max_value.toFixed(3) ?? "—"}</span></div>
          <div className="relative mx-auto w-full max-w-5xl bg-black" style={{ aspectRatio: `${recording.width}/${recording.height}` }}>
            <img src={apiUrl(`/api/recordings/${recording.id}/analyses/${run.id}/analytics/frame?pts_seconds=${selectedFramePts}`)} alt="Cadru de referință redacted din înregistrarea analizată" className="absolute inset-0 h-full w-full object-fill"/>
            {heat && <canvas ref={canvas} aria-label="Heatmap al observațiilor YOLOX peste cadrul sursă" className="pointer-events-none absolute inset-0 h-full w-full" style={{ imageRendering: "auto" }} />}
            <div aria-hidden="true" className="pointer-events-none absolute border border-dashed border-white/80" style={{ left: `${summary.crop.x * 100}%`, top: `${summary.crop.y * 100}%`, width: `${summary.crop.width * 100}%`, height: `${summary.crop.height * 100}%` }}/>
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-border p-3 text-[11px] text-text-secondary"><span>Intensitate (valori mici → mari)</span><span aria-hidden="true" className="h-2.5 w-40 rounded-full" style={{ background: "linear-gradient(90deg,#28beff,#ffe56a,#ff3746)" }}/><span>{mode === "observations" ? "observații" : "secunde estimate"}</span></div>
          {heat?.missing_data && <p className="p-4 text-sm text-text-secondary">Nu există eșantioane procesate în intervalul selectat.</p>}
          {heat && !heat.missing_data && heat.included_observations === 0 && <p className="p-4 text-sm text-text-secondary">Cadrele au fost procesate, dar modelul nu a raportat observații din categoriile selectate.</p>}
        </div>
      <aside className="space-y-3 rounded-xl border border-border bg-panel p-4"><h4 className="font-semibold">Proveniență și limite</h4><dl className="space-y-2 text-xs"><Fact label="Sursă" value="RECORDED VIDEO ANALYSIS"/><Fact label="Detector" value={summary.model_name}/><Fact label="Model SHA-256" value={summary.model_sha256}/><Fact label="Prag detector" value={summary.confidence.toFixed(2)}/><Fact label="Eșantionare solicitată" value={`${summary.sample_fps.toFixed(2)} mostre/s sursă`}/><Fact label="Procesare măsurată" value={`${summary.inference_fps.toFixed(2)} cadre/s perete`}/><Fact label="Cadru referință" value={`${clock(selectedFramePts)} PTS · redacted`}/><Fact label="Acoperire temporală eșantionată" value={`${summary.sample_coverage_seconds.toFixed(1)} s · ${(summary.sample_coverage_ratio * 100).toFixed(1)}% estimat`}/><Fact label="Observații filtrate" value={String(heat?.included_observations ?? "—")}/><Fact label="Pondere metrică" value={mode === "observations" ? "1 per observation" : "capped source-time seconds"}/></dl><div className="rounded-lg border border-caution/30 bg-caution/5 p-3 text-[11px] text-text-secondary">Observațiile nu sunt trafic validat, număr de vehicule unice, viteză, densitate fizică sau dovadă de incident. Raza Gaussiană este raportată la lățimea sursei; valorile sunt renormalizate după masca ROI.</div></aside>
      </section>

      <section className="rounded-xl border border-border bg-panel p-4"><div className="flex flex-wrap items-end justify-between gap-3"><div><h4 className="font-semibold">Activitate în timpul sursei</h4><p className="mt-1 text-xs text-text-secondary">{mode === "observations" ? "Observații detector per interval" : "Secunde de prezență vizuală estimată per interval"}; cadrele procesate fără observații rămân acoperire validă.</p></div><span className="text-[11px] text-text-muted">{series?.bins.length ?? 0} intervale · {series?.bin_seconds.toFixed(1) ?? "5"} s fiecare</span></div>
        <div className="mt-4 overflow-x-auto pb-2"><div role="img" aria-label="Grafic cu activitatea YOLOX pe timpul sursei; selectează o bară pentru interval" className="flex h-40 min-w-[700px] items-end gap-px border-b border-l border-border px-1">
          {series?.bins.map((bin, index) => {
            const values = CLASSES.map((name) => mode === "observations" ? (bin.observations_by_class[name] ?? 0) : (bin.vehicle_seconds_by_class[name] ?? 0));
            const total = values.reduce((a, b) => a + b, 0);
            return <button key={`${bin.start_s}-${index}`} type="button" title={`${clock(bin.start_s)}–${clock(bin.end_s)} · ${total.toFixed(mode === "observations" ? 0 : 1)} ${mode === "observations" ? "observații" : "s estimate"} · ${bin.sampled_frames} cadre`} onClick={() => selectBin(bin)} className="group flex min-w-[3px] flex-1 flex-col justify-end bg-transparent p-0 hover:opacity-75" aria-label={`${clock(bin.start_s)}–${clock(bin.end_s)}, ${total} ${mode === "observations" ? "observații" : "secunde estimate"}, ${bin.sampled_frames} cadre procesate`}>
              {total > 0 && values.map((value, i) => value > 0 ? <span key={CLASSES[i]} style={{ height: `${100 * value / maxBin}%`, backgroundColor: COLOR[CLASSES[i]] }} className="block w-full"/> : null)}
              {total === 0 && bin.sampled_frames > 0 && <span className="h-0.5 w-full bg-text-muted/50"/>}
            </button>;
          })}
        </div><div className="flex min-w-[700px] justify-between px-1 pt-1 font-mono text-[10px] text-text-muted"><span>{clock(start)}</span><span>{clock(end)}</span></div></div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">{CLASSES.filter((name) => classes.includes(name)).map((name) => <span key={name} className="inline-flex items-center gap-1.5 text-xs" style={{ color: COLOR[name] }}><i className="h-2 w-2 rounded-sm" style={{ backgroundColor: COLOR[name] }}/>{LABEL[name]} · {totals[name] ?? 0} obs.</span>)}</div>
        <p className="mt-3 text-[11px] text-text-muted">Mostre procesate în selecție: {heat?.processed_samples ?? 0}. Binurile fără cadre procesate sunt „fără eșantioane”; linia joasă indică un cadru procesat cu zero observații.</p>
      </section>

      <section className="overflow-x-auto rounded-xl border border-border bg-panel p-4"><h4 className="font-semibold">Observații după categorie</h4><table className="mt-3 w-full min-w-[460px] text-left text-xs"><caption className="sr-only">Observații YOLOX după clasă și număr aproximativ de track-uri</caption><thead className="text-text-muted"><tr><th className="py-2">Categorie</th><th>Observații filtrate</th><th>ID-uri tracker estimate</th></tr></thead><tbody>{CLASSES.filter((name) => classes.includes(name)).map((name) => <tr key={name} className="border-t border-border"><th scope="row" className="py-2 font-medium" style={{ color: COLOR[name] }}>{LABEL[name]}</th><td>{totals[name] ?? 0}</td><td>{trackerTotals[name] ?? 0} <span className="text-text-muted">(aproximativ)</span></td></tr>)}</tbody><tfoot><tr className="border-t border-border font-semibold"><th className="py-2">Total observații</th><td>{heat?.included_observations ?? 0}</td><td>Nu reprezintă vehicule unice</td></tr></tfoot></table></section>
      <p className="text-[11px] text-text-muted">{summary.warnings.join(" ")}</p>
    </>}
  </div>;
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="rounded-xl border border-border bg-panel p-3"><p className="text-[10px] uppercase tracking-wide text-text-muted">{label}</p><p className="mt-1 break-all font-mono text-sm font-semibold text-text-primary">{value}</p><p className="mt-1 text-[10px] leading-relaxed text-text-secondary">{note}</p></div>;
}
function Fact({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-text-muted">{label}</dt><dd className="break-all font-mono text-text-primary">{value}</dd></div>;
}
