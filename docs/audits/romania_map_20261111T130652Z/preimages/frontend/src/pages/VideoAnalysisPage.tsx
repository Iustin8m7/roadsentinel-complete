import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type PointerEvent } from "react";
import { AlertTriangle, Check, Film, FolderOpen, LineChart, LoaderCircle, Play, RefreshCw, Upload, X } from "lucide-react";
import { api, apiUrl, ApiError, uploadFile } from "@/lib/api";
import { Button } from "@/components/ui";
import OfflinePromotion from '@/components/OfflinePromotion';
import TrafficAnalyticsTab from "@/components/TrafficAnalyticsTab";

type Crop = { x: number; y: number; width: number; height: number; confirmed: boolean; source_width?: number; source_height?: number; coordinate_space?: string };
type Recording = {
  id: string; original_filename: string; sha256: string; size_bytes: number; codec: string;
  duration_ms: number; width: number; height: number; fps_num: number; fps_den: number;
  source_kind: "RECORDED SCREENCAST"; imported_at: string; provenance_note: string;
  status: string; crop: Crop | null; crop_revision: number;
};
type Run = {
  id: string; recording_id: string; status: "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted";
  configuration: { sample_fps: number; confidence: number; counting_line: [{x:number;y:number},{x:number;y:number}] | null; rules?: { stationary_enabled: boolean; stationary_duration_s: number; queue_enabled: boolean; queue_min_vehicles: number; queue_duration_s: number } };
  model_id: string; model_sha256: string; created_at: string; started_at: string | null; ended_at: string | null;
  processed_frames: number; decoded_frames: number; skipped_frames: number; total_estimated_frames: number;
  latest_media_pts_ms: number; progress: number; inference_fps: number; counts: Record<string, unknown>;
  warnings: string[]; error_code: string | null; output_size_bytes: number | null; output_duration_ms: number | null;
  output_fps: number | null; has_output: boolean; preview_sequence: number;
  has_analytics: boolean; observation_count: number; observation_schema_version: number | null;
};
type Point = { x: number; y: number };
type Drag = { mode: "create" | "move" | "resize"; sx: number; sy: number; crop: Crop };

const FULL: Crop = { x: 0, y: 0, width: 1, height: 1, confirmed: false };
const statusRo: Record<Run["status"], string> = {
  queued: "ÎN AȘTEPTARE", running: "ANALIZARE ÎN CURS", completed: "FINALIZATĂ",
  failed: "EROARE", cancelled: "ANULATĂ", interrupted: "ÎNTRERUPTĂ",
};
const fmtDuration = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
const fmtBytes = (bytes: number) => bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(2)} GiB` : `${(bytes / 1024 ** 2).toFixed(1)} MiB`;
const fmtPts = (ms: number) => `${Math.floor(ms / 60000).toString().padStart(2, "0")}:${((ms % 60000) / 1000).toFixed(2).padStart(5, "0")}`;
const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));

export default function VideoAnalysisPage() {
  const [canPromote, setCanPromote] = useState(false);
  useEffect(() => { let active = true; void api<{permissions: string[]}>('/api/auth/me').then(me => { if (active) setCanPromote(me.permissions.includes('alerts:create') && me.permissions.includes('videos:analyze')); }).catch(() => {}); return () => { active = false; }; }, []);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [analysisTab, setAnalysisTab] = useState<"video" | "analytics">("video");
  const [crop, setCrop] = useState<Crop>(FULL);
  const [line, setLine] = useState<Point[]>([]);
  const [drawCrop, setDrawCrop] = useState(false);
  const [drawLine, setDrawLine] = useState(false);
  const [sampleFps, setSampleFps] = useState(1);
  const [confidence, setConfidence] = useState(0.3);
  const [stationaryEnabled, setStationaryEnabled] = useState(true);
  const [stationaryDuration, setStationaryDuration] = useState(120);
  const [queueEnabled, setQueueEnabled] = useState(true);
  const [queueMin, setQueueMin] = useState(5);
  const [queueDuration, setQueueDuration] = useState(60);
  const outputVideo = useRef<HTMLVideoElement>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const imageBox = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);

  const selected = recordings.find((r) => r.id === selectedId) ?? null;
  const activeRun = runs.find((r) => r.id === selectedRunId) ?? runs.find((r) => r.status === "running" || r.status === "queued") ?? runs[0] ?? null;
  const cropIsConfirmed = Boolean(selected?.crop?.confirmed && crop.confirmed && selected.crop_revision > 0);

  const refresh = useCallback(async (selectFirst = false) => {
    setLoading(true);
    try {
      const data = await api<Recording[]>("/api/recordings");
      setRecordings(data);
      setSelectedId((previous) => selectFirst || !previous || !data.some((r) => r.id === previous) ? data[0]?.id ?? "" : previous);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nu s-au putut încărca înregistrările. Verifică autentificarea și conexiunea API.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void refresh(true); }, [refresh]);
  useEffect(() => {
    if (!selected) { setRuns([]); setSelectedRunId(""); setCrop(FULL); setLine([]); return; }
    setCrop(selected.crop ?? FULL);
    setLine([]);
    setSelectedRunId("");
    setAnalysisTab("video");
    let live = true;
    void api<Run[]>(`/api/recordings/${selected.id}/analyses`).then((value) => { if (live) setRuns(value); })
      .catch((err) => { if (live) setError(err instanceof ApiError ? err.message : "Istoricul analizei nu este disponibil."); });
    return () => { live = false; };
  }, [selectedId]);

  useEffect(() => {
    if (!activeRun || !["queued", "running"].includes(activeRun.status)) return;
    let live = true;
    const poll = async () => {
      try {
        const updated = await api<Run>(`/api/analyses/${activeRun.id}`);
        if (live) setRuns((old) => [updated, ...old.filter((r) => r.id !== updated.id)]);
      } catch (err) { if (live) setError(err instanceof ApiError ? err.message : "Actualizarea progresului a eșuat."); }
    };
    const timer = window.setInterval(() => void poll(), 1800);
    void poll();
    return () => { live = false; window.clearInterval(timer); };
  }, [activeRun?.id, activeRun?.status]);

  const importFile = async (file?: File) => {
    if (!file) return;
    setBusy(true); setError(""); setUploadProgress(0);
    try {
      const row = await uploadFile<Recording>("/api/recordings", file, (loaded, total) => setUploadProgress(total ? loaded / total : 0));
      setRecordings((old) => [row, ...old.filter((r) => r.id !== row.id)]);
      setSelectedId(row.id); setRuns([]); setSelectedRunId(""); setCrop(row.crop ?? FULL);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Importul a eșuat. Verifică formatul, spațiul liber și serviciul local.");
    } finally { setBusy(false); setUploadProgress(null); }
  };

  const updateCrop = (key: "x" | "y" | "width" | "height", value: number) => {
    if (!selected) return;
    setCrop((old) => {
      const minWidth = 64 / selected.width;
      const minHeight = 64 / selected.height;
      const max = key === "x" ? 1 - old.width : key === "y" ? 1 - old.height
        : key === "width" ? 1 - old.x : 1 - old.y;
      const min = key === "width" ? minWidth : key === "height" ? minHeight : 0;
      return { ...old, [key]: clamp(value, min, max), confirmed: false };
    });
  };
  const saveCrop = async () => {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      const row = await api<Recording>(`/api/recordings/${selected.id}/crop`, { method: "PATCH", body: JSON.stringify({ x: crop.x, y: crop.y, width: crop.width, height: crop.height, confirmed: true, expected_revision: selected.crop_revision }) });
      setRecordings((old) => old.map((item) => item.id === row.id ? row : item));
      setCrop(row.crop ?? FULL);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Nu s-a putut salva decupajul."); }
    finally { setBusy(false); }
  };

  const startAnalysis = async () => {
    if (!selected || !cropIsConfirmed) return;
    setBusy(true); setError("");
    try {
      const run = await api<Run>(`/api/recordings/${selected.id}/analyses`, {
        method: "POST", body: JSON.stringify({ sample_fps: sampleFps, confidence, crop_revision: selected.crop_revision,
          output_mode: "sampled_timeline", counting_line: line.length === 2 ? line : null,
          stationary_enabled: stationaryEnabled, stationary_duration_s: stationaryDuration,
          queue_enabled: queueEnabled, queue_min_vehicles: queueMin, queue_duration_s: queueDuration }),
      });
      setRuns((old) => [run, ...old.filter((r) => r.id !== run.id)]); setSelectedRunId(run.id);
      setAnalysisTab("video");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Analiza nu a putut porni."); }
    finally { setBusy(false); }
  };

  const cancelRun = async () => {
    if (!activeRun) return;
    setBusy(true);
    try {
      const updated = await api<Run>(`/api/analyses/${activeRun.id}/cancel`, { method: "POST", body: "{}" });
      setRuns((old) => [updated, ...old.filter((r) => r.id !== updated.id)]);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Anularea analizei a eșuat."); }
    finally { setBusy(false); }
  };

  const pointerPosition = (event: { clientX: number; clientY: number }) => {
    const rect = imageBox.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return { x: clamp((event.clientX - rect.left) / rect.width), y: clamp((event.clientY - rect.top) / rect.height) };
  };
  const pointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!selected || !imageBox.current) return;
    if (drawLine) {
      const point = pointerPosition(event);
      if (point.x < crop.x || point.x > crop.x + crop.width || point.y < crop.y || point.y > crop.y + crop.height) return;
      const local = { x: (point.x - crop.x) / crop.width, y: (point.y - crop.y) / crop.height };
      setLine((old) => old.length >= 2 ? [local] : [...old, local]);
      return;
    }
    const p = pointerPosition(event);
    const inside = p.x >= crop.x && p.x <= crop.x + crop.width && p.y >= crop.y && p.y <= crop.y + crop.height;
    const mode: Drag["mode"] = drawCrop || !inside ? "create" : event.currentTarget.dataset.handle === "resize" ? "resize" : "move";
    drag.current = { mode, sx: p.x, sy: p.y, crop: { ...crop } };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const active = drag.current;
    if (!active) return;
    const p = pointerPosition(event);
    const dx = p.x - active.sx, dy = p.y - active.sy;
    let next: Crop;
    if (active.mode === "create") {
      next = { ...active.crop, x: Math.min(active.sx, p.x), y: Math.min(active.sy, p.y), width: Math.abs(dx), height: Math.abs(dy), confirmed: false };
    } else if (active.mode === "resize") {
      next = { ...active.crop, width: clamp(active.crop.width + dx, 0.05, 1 - active.crop.x), height: clamp(active.crop.height + dy, 0.05, 1 - active.crop.y), confirmed: false };
    } else {
      next = { ...active.crop, x: clamp(active.crop.x + dx, 0, 1 - active.crop.width), y: clamp(active.crop.y + dy, 0, 1 - active.crop.height), confirmed: false };
    }
    setCrop(next);
  };
  const pointerUp = () => { drag.current = null; setDrawCrop(false); };

  const runList = useMemo(() => runs.slice().sort((a, b) => b.created_at.localeCompare(a.created_at)), [runs]);
  const runCounts = activeRun?.counts ?? {};

  return <main className="mx-auto w-full max-w-[1500px] space-y-5 overflow-y-auto p-4 pb-10 sm:p-6" aria-labelledby="video-analysis-title">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="eyebrow">PROCESARE LOCALĂ · FĂRĂ ÎNCĂRCARE EXTERNĂ</p><h1 id="video-analysis-title" className="font-display text-2xl font-bold sm:text-3xl">Analiză video înregistrată</h1>
        <p className="mt-2 max-w-3xl text-sm text-text-secondary">Importă o înregistrare, confirmă cadrul de trafic, apoi rulează YOLOX-S + ByteTrack local. Conținutul este etichetat RECORDED ANALYSIS, niciodată LIVE.</p></div>
      <span className="rounded-full border border-border px-3 py-1.5 text-xs text-text-secondary">YOLOX-S ONNX · local</span>
    </header>

    {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-critical/40 bg-critical/10 p-3 text-sm text-critical"><AlertTriangle size={18} className="mt-0.5 shrink-0"/><span>{error}</span><button className="ml-auto" onClick={() => setError("")} aria-label="Închide mesajul"><X size={16}/></button></div>}

    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-4">
        <section className={`rounded-2xl border border-dashed p-5 transition ${dragOver ? "border-action bg-action/10" : "border-border bg-panel/60"}`}
          onDragOver={(e: DragEvent) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)}
          onDrop={(e: DragEvent) => { e.preventDefault(); setDragOver(false); void importFile(e.dataTransfer.files[0]); }}>
          <div className="flex flex-wrap items-center gap-4"><span className="grid h-12 w-12 place-items-center rounded-xl bg-action/10 text-action"><Upload size={22}/></span><div className="min-w-52 flex-1"><h2 className="font-semibold">Importă o înregistrare WebM / MP4</h2><p className="mt-1 text-xs text-text-secondary">Încărcare locală, limită 1 GiB. Fișierul se criptează la stocare; originalul ales rămâne nemodificat.</p></div>
            <label className="press inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg bg-action px-4 text-sm font-semibold text-on-accent"><FolderOpen size={16}/> Alege fișier<input type="file" accept="video/webm,video/mp4,video/x-m4v,video/quicktime,video/x-matroska,.webm,.mp4,.m4v,.mov,.mkv" className="sr-only" disabled={busy} onChange={(e) => { void importFile(e.target.files?.[0]); e.currentTarget.value = ""; }}/></label>
          </div>
          {uploadProgress !== null && <div className="mt-4" role="status"><div className="mb-1 flex justify-between text-xs"><span>Încărcare și validare video</span><span>{Math.round(uploadProgress * 100)}%</span></div><progress max={1} value={uploadProgress} className="h-2 w-full accent-action"/></div>}
        </section>

        {!selected && <section className="grid min-h-56 place-items-center rounded-2xl border border-border bg-panel/40 text-center" aria-live="polite">
          {loading ? <div className="text-text-secondary"><LoaderCircle className="mx-auto mb-2 animate-spin"/>Se încarcă înregistrările…</div> : <div><Film className="mx-auto mb-3 text-text-muted" size={32}/><h2 className="font-semibold">Nicio înregistrare importată</h2><p className="mt-1 text-sm text-text-secondary">Alege unul dintre screencasturile WebM din calculator.</p></div>}
        </section>}

        {selected && <>
          <section className="overflow-hidden rounded-2xl border border-border bg-panel">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4"><div><span className="rounded border border-caution/40 bg-caution/10 px-2 py-1 text-[10px] font-bold tracking-wide text-caution">RECORDED SCREENCAST · OFFLINE</span><h2 className="mt-2 break-all font-display text-lg font-semibold">{selected.original_filename}</h2></div><button className="text-xs text-action underline" onClick={() => void refresh()}>Reîncarcă lista</button></div>
            <div className="grid gap-x-5 gap-y-3 p-4 text-xs sm:grid-cols-2 xl:grid-cols-4">
              <p><strong>Container / codec:</strong> WebM / {selected.codec.toUpperCase()}</p><p><strong>Dimensiune:</strong> {selected.width} × {selected.height}</p>
              <p><strong>Durată:</strong> {fmtDuration(selected.duration_ms)}</p><p><strong>FPS din container:</strong> {(selected.fps_num / selected.fps_den).toFixed(2)} (nu este FPS-ul optic al camerei)</p>
              <p><strong>Mărime:</strong> {fmtBytes(selected.size_bytes)}</p><p><strong>Importată:</strong> {new Date(selected.imported_at).toLocaleString("ro-RO")}</p>
              <p className="break-all sm:col-span-2"><strong>SHA-256:</strong> {selected.sha256}</p><p className="sm:col-span-2 text-text-secondary">{selected.provenance_note}</p>
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-border bg-panel">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border p-4"><div><h2 className="font-display text-lg font-semibold">Cadrul real și zona analizată</h2><p className="mt-1 text-xs text-text-secondary">Trage pe imagine pentru a desena o zonă nouă; trage selecția pentru a o muta. Confirmarea este necesară înainte de analiză.</p></div>
              <div className="flex gap-2"><Button variant="secondary" size="sm" onClick={() => { setDrawCrop(true); setDrawLine(false); }}>Desenează decupaj</Button><Button variant="secondary" size="sm" onClick={() => { setDrawLine(!drawLine); setLine([]); setDrawCrop(false); }}><LineChart size={14}/> Linie de numărare</Button></div></div>
            <div ref={imageBox} className="relative mx-auto w-full max-w-5xl touch-none select-none bg-black" style={{ aspectRatio: `${selected.width}/${selected.height}` }} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp}>
              <img src={apiUrl(`/api/recordings/${selected.id}/thumbnail?pts_seconds=${Math.min(2, selected.duration_ms / 2000)}&rev=${selected.crop_revision}`)} alt={`Cadru real din înregistrarea ${selected.original_filename}`} className="absolute inset-0 h-full w-full object-fill" draggable={false}/>
              <div className={`absolute border-2 ${crop.confirmed ? "border-ok" : "border-action"}`} style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.width * 100}%`, height: `${crop.height * 100}%`, boxShadow: "0 0 0 9999px rgba(0,0,0,.52)" }}>
                <span className="absolute left-1 top-1 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-white">{crop.confirmed ? "ZONĂ CONFIRMATĂ" : "PREVIZUALIZARE · NECONFIRMATĂ"}</span>
                <button type="button" data-handle="resize" aria-label="Redimensionează zona" className="pointer-events-auto absolute -bottom-2 -right-2 h-5 w-5 rounded-full border-2 border-white bg-action" onPointerDown={(e) => { e.stopPropagation(); const p = pointerPosition(e); drag.current = { mode: "resize", sx: p.x, sy: p.y, crop: { ...crop } }; e.currentTarget.parentElement?.setPointerCapture(e.pointerId); }}/>
              </div>
              {line.length === 2 && <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1={(crop.x + line[0].x * crop.width) * 100} y1={(crop.y + line[0].y * crop.height) * 100} x2={(crop.x + line[1].x * crop.width) * 100} y2={(crop.y + line[1].y * crop.height) * 100} stroke="#fbbf24" strokeWidth="0.6"/><circle cx={(crop.x + line[0].x * crop.width) * 100} cy={(crop.y + line[0].y * crop.height) * 100} r="1.1" fill="#fbbf24"/><circle cx={(crop.x + line[1].x * crop.width) * 100} cy={(crop.y + line[1].y * crop.height) * 100} r="1.1" fill="#fbbf24"/></svg>}
            </div>
            <div className="grid gap-4 p-4 lg:grid-cols-[1fr_auto]">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{(["x", "y", "width", "height"] as const).map((key) => <label key={key} className="text-xs text-text-secondary">{({x:"X stânga",y:"Y sus",width:"Lățime",height:"Înălțime"})[key]} <input type="number" min={0} max={1} step={0.01} value={Number(crop[key].toFixed(3))} onChange={(e) => updateCrop(key, clamp(Number(e.target.value), 0, 1))} aria-label={`Coordonată decupaj ${key}`} className="mt-1 min-h-10 w-full rounded-lg border border-border bg-elevation px-2 font-mono text-text-primary"/></label>)}</div>
              <div className="flex flex-wrap items-end gap-2"><Button onClick={() => void saveCrop()} disabled={busy || crop.width * selected.width < 64 || crop.height * selected.height < 64}><Check size={15}/> Confirmă zona</Button>{selected.crop?.confirmed && <span className="pb-2 text-xs text-ok">Salvată · v{selected.crop_revision}</span>}</div>
              <p className="text-xs text-text-secondary lg:col-span-2">Coordonate normalizate față de cadrul original {selected.width}×{selected.height}; analiza păstrează maparea la pixeli. Linia, dacă este adăugată, este raportată în pixeli ai decupajului și nu presupune distanțe reale.</p>
              {drawLine && <p className="text-xs text-caution lg:col-span-2">Alege două puncte în zona confirmată. Linia este doar pentru numărarea trecerilor observate; geometria nu este calibrată pentru viteză sau distanțe.</p>}
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="rounded-2xl border border-border bg-panel p-4">
              <h2 className="font-display text-lg font-semibold">Setări și analiză</h2><p className="mt-1 text-xs text-text-secondary">Preset CPU recomandat: 1 eșantion/s. Reducerea frecvenței poate degrada continuitatea urmăririi ByteTrack.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-xs text-text-secondary">Eșantioane pe secundă<select value={sampleFps} onChange={(e) => setSampleFps(Number(e.target.value))} className="mt-1 min-h-10 w-full rounded-lg border border-border bg-elevation px-3 text-sm text-text-primary"><option value={1}>Recomandat · 1</option><option value={2}>2</option><option value={3}>3</option><option value={5}>5 · intensiv CPU</option></select></label>
                <label className="text-xs text-text-secondary">Prag detecție<select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="mt-1 min-h-10 w-full rounded-lg border border-border bg-elevation px-3 text-sm text-text-primary"><option value={0.3}>0.30 · implicit</option><option value={0.4}>0.40</option><option value={0.5}>0.50</option></select></label></div>
              <div className="mt-4 rounded-xl border border-border bg-elevation/40 p-3"><h3 className="font-semibold">Reguli și evenimente</h3><p className="mt-1 text-xs text-text-secondary">Zona monitorizată este decupajul confirmat; presupune cameră fixă. Rezultatele sunt candidați care cer verificare umană.</p><div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={stationaryEnabled} onChange={e => setStationaryEnabled(e.target.checked)}/> Posibilă obstrucție staționară</label><label className="text-xs">Durată minimă (sec.)<input type="number" min={30} max={1800} step={10} value={stationaryDuration} onChange={e => setStationaryDuration(Number(e.target.value))} className="mt-1 min-h-9 w-full rounded-lg border border-border bg-panel px-2 text-text-primary"/></label>
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={queueEnabled} onChange={e => setQueueEnabled(e.target.checked)}/> Coada persistentă</label><label className="text-xs">Vehicule simultane min.<input type="number" min={3} max={30} value={queueMin} onChange={e => setQueueMin(Number(e.target.value))} className="mt-1 min-h-9 w-full rounded-lg border border-border bg-panel px-2 text-text-primary"/></label><label className="text-xs sm:col-start-2">Durată coadă (sec.)<input type="number" min={20} max={900} step={10} value={queueDuration} onChange={e => setQueueDuration(Number(e.target.value))} className="mt-1 min-h-9 w-full rounded-lg border border-border bg-panel px-2 text-text-primary"/></label>
              </div><p className="mt-3 text-[11px] text-caution">La 0.5 eșantioane/s regula de coadă este dezactivată; opririle necesită continuitate tracker. Excluderi de intersecție/parcare nu sunt configurate. Viteză, distanțe, TTC, semafor și sens legal necesită calibrare/configurare explicită.</p></div>
              <div className="mt-4 flex flex-wrap gap-2"><Button onClick={() => void startAnalysis()} disabled={!cropIsConfirmed || busy || Boolean(activeRun && ["queued", "running"].includes(activeRun.status))}><Play size={15}/> Pornește analiza</Button>{activeRun && ["queued", "running"].includes(activeRun.status) && <Button variant="secondary" onClick={() => void cancelRun()} disabled={busy}><X size={15}/> Anulează în siguranță</Button>}{!cropIsConfirmed && <span className="self-center text-xs text-caution">Confirmă mai întâi zona de trafic.</span>}</div>
            </div>
            <div className="rounded-2xl border border-border bg-panel p-4"><h3 className="font-semibold">Istoric analize</h3>{runList.length ? <ul className="mt-3 space-y-2">{runList.map((run) => <li key={run.id}><button type="button" onClick={() => setSelectedRunId(run.id)} aria-current={run.id === activeRun?.id ? "true" : undefined} className={`w-full rounded-lg border p-3 text-left ${run.id === activeRun?.id ? "border-action/60 bg-action/10" : "border-border hover:bg-elevation"}`}><span className="flex justify-between gap-2 text-xs font-semibold"><span>{statusRo[run.status]}</span><span>{new Date(run.created_at).toLocaleTimeString("ro-RO")}</span></span><span className="mt-1 block truncate font-mono text-[10px] text-text-muted">{run.id}</span></button></li>)}</ul> : <p className="mt-3 text-sm text-text-secondary">Nu există rulări. Importul și crop-ul sunt păstrate în cont.</p>}</div>
          </section>

          {activeRun && <section className="space-y-4 rounded-2xl border border-border bg-panel p-4" aria-live="polite">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-display text-lg font-semibold">{statusRo[activeRun.status]} · RECORDED ANALYSIS</h2><p className="mt-1 font-mono text-xs text-text-muted">Rulare {activeRun.id} · YOLOX-S ONNX · {activeRun.configuration.sample_fps} eșantioane/s</p></div><button className="inline-flex items-center gap-1 text-xs text-action" onClick={() => void refresh()}><RefreshCw size={13}/> Reîncarcă</button></div>
            {activeRun.status === "completed" && <div role="tablist" aria-label="Rezultate analiză" className="flex gap-2 border-b border-border pb-2"><button role="tab" aria-selected={analysisTab === "video"} onClick={() => setAnalysisTab("video")} className={`rounded-lg px-3 py-2 text-sm ${analysisTab === "video" ? "bg-action/10 text-action" : "text-text-secondary"}`}>Video și sumar</button><button role="tab" aria-selected={analysisTab === "analytics"} onClick={() => setAnalysisTab("analytics")} className={`rounded-lg px-3 py-2 text-sm ${analysisTab === "analytics" ? "bg-action/10 text-action" : "text-text-secondary"}`}>Heatmap și analitice {activeRun.has_analytics ? "" : "· reanaliză necesară"}</button></div>}
            {analysisTab === "analytics" && activeRun.status === "completed" && selected ? <TrafficAnalyticsTab recording={selected} run={activeRun}/> : <>
            {(activeRun.status === "queued" || activeRun.status === "running") && <div><div className="mb-1 flex justify-between text-xs"><span>{activeRun.decoded_frames.toLocaleString("ro-RO")} cadre decodate · {activeRun.processed_frames.toLocaleString("ro-RO")} inferențe · PTS {fmtPts(activeRun.latest_media_pts_ms)}</span><span>{Math.round(activeRun.progress * 100)}%</span></div><progress className="h-2 w-full accent-action" max={1} value={activeRun.progress}/><p className="mt-1 text-[11px] text-text-secondary">Debit observat: {activeRun.inference_fps.toFixed(2)} inferențe/s · cadre sărite pentru eșantionare: {activeRun.skipped_frames.toLocaleString("ro-RO")}</p></div>}
            {activeRun.status === "running" && activeRun.preview_sequence > 0 && <div className="overflow-hidden rounded-xl border border-border bg-black"><img key={`${activeRun.id}-${activeRun.preview_sequence}`} src={apiUrl(`/api/analyses/${activeRun.id}/preview?sequence=${activeRun.preview_sequence}`)} alt={`Previzualizare YOLOX RECORDED ANALYSIS la PTS ${fmtPts(activeRun.latest_media_pts_ms)}`} className="mx-auto max-h-[55vh] w-auto max-w-full"/><div className="flex justify-between p-2 text-xs text-white"><span>PREVIEW ANOTAT · RECORDED ANALYSIS</span><span>PTS {fmtPts(activeRun.latest_media_pts_ms)}</span></div></div>}
            {activeRun.status === "failed" && <p role="alert" className="text-sm text-critical">Analiza a eșuat. Cod: {activeRun.error_code ?? "unknown"}. Verifică FFmpeg, modelul și spațiul local.</p>}
            {activeRun.status === "interrupted" && <p className="text-sm text-caution">Backendul s-a oprit în timpul procesării. Rularea a fost marcată întreruptă; pornește o analiză nouă.</p>}
            {activeRun.warnings.map((warning) => <p key={warning} className="flex gap-2 text-xs text-caution"><AlertTriangle size={14} className="shrink-0"/>{warning}</p>)}
            {activeRun.has_output && <><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Detectări observate" value={JSON.stringify(runCounts.detection_observations_by_class ?? {})}/><Metric label="ID-uri tracker observate" value={JSON.stringify(runCounts.unique_track_ids_by_class ?? {})}/><Metric label="Traversări pe linie" value={JSON.stringify(runCounts.line_crossings ?? "Neconfigurată")}/><Metric label="Video de ieșire" value={`${fmtDuration(activeRun.output_duration_ms ?? 0)} · ${activeRun.output_fps ?? 0} fps`}/></div>
                <p className="text-xs text-text-secondary">Numărul de detecții este numărul de observații ale modelului, nu vehicule unice. ID-urile ByteTrack sunt aproximative la eșantionare rară. {activeRun.configuration.counting_line ? "Linia este plasată manual, necalibrată." : "Nu s-a configurat linie de numărare."} Ieșirea păstrează cronologia prin redare eșantionată; audio nu este inclus.</p>
                <video ref={outputVideo} key={activeRun.id} controls preload="metadata" className="max-h-[70vh] w-full rounded-xl bg-black" src={apiUrl(`/api/analyses/${activeRun.id}/video`)} aria-label="Video adnotat RECORDED ANALYSIS"/>
                <section className="rounded-xl border border-border p-3"><h3 className="font-semibold">Reguli și evenimente · {Array.isArray(runCounts.candidate_events) ? runCounts.candidate_events.length : 0} candidate</h3><p className="mt-1 text-xs text-text-secondary">Sursă RECORDED SCREENCAST. Evenimentele sunt persistate în rulare; pot fi trimise explicit pentru verificare ca înregistrări, fără alertare LIVE.</p>
                  {Boolean(runCounts.event_rule_summary) && <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3"><p className="rounded bg-elevation/50 p-2">Staționare: {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).stationary?.status)} · prag {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).stationary?.threshold_s)} s</p><p className="rounded bg-elevation/50 p-2">Coada: {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).queue?.status)} · min. {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).queue?.minimum_vehicles)} vehicule / {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).queue?.threshold_s)} s</p><p className="rounded bg-elevation/50 p-2">Traversări: {String((runCounts.event_rule_summary as Record<string, Record<string, unknown>>).crossing?.count)} · numai analiză flux</p></div>}
                  {Array.isArray(runCounts.candidate_events) && runCounts.candidate_events.length ? <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">{(runCounts.candidate_events as Array<Record<string, unknown>>).map((ev, i) => <li key={`${ev.type}-${ev.pts_ms}-${ev.track_id}-${i}`}><button type="button" className="w-full rounded-lg border border-caution/30 bg-caution/5 p-3 text-left" onClick={() => { if (outputVideo.current) { outputVideo.current.currentTime = Number(ev.output_time_s ?? 0); void outputVideo.current.play(); } }}><strong>{String(ev.label ?? ev.type)} · PTS {fmtPts(Number(ev.pts_ms ?? 0))}</strong><span className="mt-1 block text-xs">Track {String(ev.track_id ?? "—")} · {String(ev.class ?? "")} · încredere {String(ev.confidence ?? "—")}</span><span className="mt-1 block text-xs text-text-secondary">{String(ev.reason ?? "")}</span><span className="mt-1 block text-[11px] text-caution">{String(ev.limitations ?? "Candidat; necesită verificare operator.")}</span></button>{canPromote && selected && activeRun && <OfflinePromotion recording={selected.id} run={activeRun.id} index={i} />}</li>)}</ul> : <p className="mt-3 rounded-lg bg-elevation/40 p-3 text-sm">0 candidate events. Cadre procesate: {activeRun.processed_frames.toLocaleString("ro-RO")} · reguli evaluate: {String((runCounts.event_rule_summary as Record<string, unknown> | undefined)?.stationary ? "staționare și coadă" : "rezultatul regulilor se încarcă")}. Nicio condiție configurată nu a atins pragurile sau continuitatea necesară.</p>}
                  {Array.isArray(runCounts.flow_events) && runCounts.flow_events.length > 0 && <div className="mt-3"><p className="text-xs text-action">Flux: {runCounts.flow_events.length} traversări · clasă/direcție {JSON.stringify(runCounts.line_crossings_by_class_direction ?? runCounts.line_crossings)}.</p><ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">{(runCounts.flow_events as Array<Record<string, unknown>>).slice(0, 100).map((ev, i) => <li key={`flow-${i}`}><button type="button" className="w-full rounded border border-border px-2 py-1 text-left text-xs hover:bg-elevation" onClick={() => { if (outputVideo.current) { outputVideo.current.currentTime = Number(ev.output_time_s ?? 0); void outputVideo.current.play(); } }}>PTS {fmtPts(Number(ev.pts_ms ?? 0))} · {String(ev.class)} · {String(ev.direction)} · track {String(ev.track_id)}</button></li>)}</ul></div>}
                </section>
                <a className="text-sm text-action underline" href={apiUrl(`/api/analyses/${activeRun.id}/export`)}>Descarcă video-ul procesat prin acces autentificat</a></>}
            </>}
          </section>}
        </>}
      </div>

      <aside className="rounded-2xl border border-border bg-panel p-3 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto" aria-label="Înregistrări importate">
        <h2 className="flex items-center gap-2 px-2 py-2 text-sm font-semibold"><Film size={16}/> Înregistrări · {recordings.length}</h2>
        {loading && !recordings.length && <div className="space-y-2 p-2" aria-label="Se încarcă înregistrările"><div className="h-14 animate-pulse rounded-lg bg-elevation"/><div className="h-14 animate-pulse rounded-lg bg-elevation"/></div>}
        <ul className="space-y-1">{recordings.map((row) => <li key={row.id}><button type="button" onClick={() => setSelectedId(row.id)} aria-current={row.id === selectedId ? "true" : undefined} className={`w-full rounded-xl border p-3 text-left ${row.id === selectedId ? "border-action/60 bg-action/10" : "border-transparent hover:border-border hover:bg-elevation"}`}><span className="block break-all text-sm font-medium">{row.original_filename}</span><span className="mt-1 block text-xs text-text-secondary">RECORDED · {fmtDuration(row.duration_ms)} · {fmtBytes(row.size_bytes)}</span><span className="mt-1 block text-[10px] text-text-muted">{row.width}×{row.height} · {row.codec.toUpperCase()}</span></button></li>)}</ul>
      </aside>
    </section>
  </main>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-border bg-elevation/40 p-3"><p className="text-[10px] uppercase tracking-wide text-text-muted">{label}</p><p className="mt-1 break-all font-mono text-xs text-text-primary">{value}</p></div>;
}
