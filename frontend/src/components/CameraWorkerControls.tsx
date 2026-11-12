import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui";
import { Field, TextInput } from "@/components/forms";

type WorkerState = {
  state: "STOPPED" | "STARTING" | "RUNNING" | "STOPPING" | "RECONNECTING" | "ERROR";
  desired_state: "STOPPED" | "RUNNING";
  pid: number | null;
  config_version?: string;
  last_exit_code?: number | null;
  heartbeat_age_s?: number | null;
  last_error?: string | null;
  telemetry?: {
    fps?: number | null;
    processing_fps?: number | null;
    detections?: number;
    unique_tracks?: number;
    inference_latency_ms_p95?: number | null;
    model?: string | null;
    inference_provider?: string | null;
    provider_fallback_reason?: string | null;
    source?: { state?: string; kind?: string; transport?: string; last_frame_age_s?: number | null; width?: number | null; height?: number | null };
  };
};

export function CameraWorkerControls({ cameraId, initialConfigRef }: { cameraId: string; initialConfigRef?: string }) {
  const [configRef, setConfigRef] = useState(initialConfigRef ?? "");
  const [worker, setWorker] = useState<WorkerState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try { setWorker(await api<WorkerState>(`/api/cameras/${cameraId}/worker`)); }
    catch { setError("Starea workerului nu este disponibilă."); }
  }, [cameraId]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  async function act(action: "start" | "stop" | "restart") {
    setBusy(true); setError("");
    try {
      const result = await api<WorkerState>(`/api/cameras/${cameraId}/worker/${action}`, {
        method: "POST",
        ...(action === "stop" ? {} : { body: JSON.stringify({ config_ref: configRef.trim() }) }),
      });
      setWorker(result);
    } catch (reason) {
      setError((reason as Error).message || "Comanda workerului a eșuat.");
      await refresh();
    } finally { setBusy(false); }
  }

  return <section className="mt-3 rounded-lg border border-border bg-elevation/30 p-3" aria-label="Control analytics worker">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-xs font-semibold">Worker analytics · stare backend</h3><span role="status" className={`rounded-full border px-2 py-1 text-[10px] font-bold ${worker?.state === "RUNNING" ? "border-ok/40 text-ok" : worker?.state === "ERROR" ? "border-critical/40 text-critical" : "border-border text-text-secondary"}`}>{worker?.state ?? "LOADING"}</span></div>
    <p className="mt-1 text-[11px] text-text-secondary">Dorit: {worker?.desired_state ?? "—"}{worker?.pid ? ` · PID ${worker.pid}` : ""}{worker?.last_exit_code != null ? ` · exit ${worker.last_exit_code}` : ""}</p>
    {worker?.last_error && <p role="status" className="mt-1 text-[11px] text-caution">Sursa: {worker.last_error}</p>}
    <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(10rem,1fr)_auto]">
      <Field label="Config local cameras/*.yaml">
        {(attrs) => <TextInput {...attrs} value={configRef} onChange={(event) => setConfigRef(event.target.value)} placeholder="ex. local-uvc.yaml" maxLength={72} autoComplete="off" readOnly={Boolean(initialConfigRef)} />}
      </Field>
      <div className="flex flex-wrap items-end gap-1.5">
        <Button size="sm" disabled={busy || !configRef.trim()} onClick={() => void act("start")}>Start</Button>
        <Button size="sm" variant="secondary" disabled={busy || worker?.state === "STOPPED"} onClick={() => void act("stop")}>Stop</Button>
        <Button size="sm" variant="secondary" disabled={busy || !configRef.trim()} onClick={() => void act("restart")}>Restart</Button>
      </div>
    </div>
    {worker?.telemetry && <div className="mt-2 grid grid-cols-2 gap-2 rounded border border-border p-2 text-[10px] text-text-secondary sm:grid-cols-4" aria-label="Telemetrie măsurată de pipeline">
      <p>Sursă: {worker.telemetry.source?.state ?? "fără heartbeat"}{worker.telemetry.source?.transport ? ` · ${worker.telemetry.source.transport}` : ""}</p>
      <p>Cadru proaspăt: {worker.telemetry.source?.last_frame_age_s == null ? "—" : `${worker.telemetry.source.last_frame_age_s.toFixed(1)} s`}</p>
      <p>Cadence măsurată: {worker.telemetry.fps == null ? "—" : `${worker.telemetry.fps.toFixed(3)} FPS`}</p>
      <p>Procesare: {worker.telemetry.processing_fps == null ? "—" : `${worker.telemetry.processing_fps.toFixed(3)} FPS`}</p>
      <p>Detecții / piste: {worker.telemetry.detections ?? "—"} / {worker.telemetry.unique_tracks ?? "—"}</p>
      <p>Inferență P95: {worker.telemetry.inference_latency_ms_p95 == null ? "—" : `${worker.telemetry.inference_latency_ms_p95.toFixed(1)} ms`}</p>
      <p>Model / provider: {worker.telemetry.model ?? "—"} · {worker.telemetry.inference_provider ?? "necunoscut"}</p>
      {worker.telemetry.provider_fallback_reason && <p className="col-span-2 text-caution sm:col-span-4">{worker.telemetry.provider_fallback_reason}</p>}
    </div>}
    {worker?.heartbeat_age_s != null && <p className="mt-1 text-[10px] text-text-muted">Ultimul heartbeat cu date de procesare: {worker.heartbeat_age_s.toFixed(1)} s în urmă.</p>}
    {worker?.config_version && <p className="mt-1 break-all text-[10px] text-text-muted">Config SHA-256: {worker.config_version}</p>}
    {error && <p role="alert" className="mt-2 text-xs text-critical">{error}</p>}
  </section>;
}
