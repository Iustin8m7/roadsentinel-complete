import { lazy, Suspense, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Grid, Map as MapIcon, VideoOff, Pencil, Activity, Plus } from "lucide-react";
import { api, apiUrl, USE_MOCKS } from "@/lib/api";
import { adaptCamera, type ApiCamera } from "@/lib/adapters";
import { LIVE_STREAM } from "@/lib/adapters";
import { useDataStore } from "@/store/data";
import { hasBackendPermission } from "@/lib/permissions";
import type { RomanianCameraCandidate } from "@/romanianCameraCandidates";
import { RomanianCameraExperience } from "@/components/RomanianCameraExperience";
import { CameraWorkerControls } from "@/components/CameraWorkerControls"
import { CameraControlPanel } from "@/components/CameraControlPanel";
import TacticalMap from "@/components/TacticalMap";
import { ClipModal, type ModalClip } from "@/components/ClipModal";
import { Dialog } from "@/components/Dialog";
import { Button, Chip, EmptyState, RedactionChip } from "@/components/ui";
import { Field, TextInput } from "@/components/forms";
import { ALERT_TYPE } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import type { AlertType, Camera } from "@/types";

// hls.js (~400 kB) is only fetched when the external live demo is switched on and opened.
const LivePlayer = lazy(() => import("@/components/LivePlayer").then((m) => ({ default: m.LivePlayer })));

type View = "grid" | "map";

function sourceLabel(camera: Camera): string {
  const source = camera.sourceHealth;
  if (!source || source.state !== "healthy") return source?.state === "waiting" ? "AȘTEAPTĂ CADRU" : "OFFLINE / STALE";
  if (source.replay || source.kind === "file") return "RECORDED REPLAY";
  if (source.kind === "device") return "LOCAL CAMERA LIVE";
  return "LIVE · NETWORK SOURCE";
}

export default function CamerasPage() {
  const realCameras = useDataStore((st) => st.cameras);
  const alerts = useDataStore((st) => st.alerts);
  const [cameraManageAllowed, setCameraManageAllowed] = useState(false);
  const [controlCamera, setControlCamera] = useState<string | null>(null);
  const [view, setView] = useState<View>("grid");
  const [playerClips, setPlayerClips] = useState<ModalClip[] | null>(null);
  const [liveCam, setLiveCam] = useState<{ name: string; url: string } | null>(null);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [creatingCamera, setCreatingCamera] = useState(false);
  const [detailCamera, setDetailCamera] = useState<Camera | null>(null);
  const [candidateCameras, setCandidateCameras] = useState<RomanianCameraCandidate[]>([]);
  const [candidateLoading, setCandidateLoading] = useState(true);
  const [candidateError, setCandidateError] = useState(false);

  useEffect(() => {
    if (USE_MOCKS) return;
    let active = true;
    const refresh = async () => {
      try {
        const cameras = await api<ApiCamera[]>("/api/cameras");
        if (active) useDataStore.setState({ cameras: cameras.map(adaptCamera) });
      } catch { /* the shared store surfaces connection errors; the last verified snapshot remains visible */ }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (USE_MOCKS) return;
    let active = true;
    api<RomanianCameraCandidate[]>("/api/cameras/discovery")
      .then((items) => {
        if (!active) return;
        setCandidateCameras(items);
        setCandidateError(false);
      })
      .catch(() => { if (active) setCandidateError(true); })
      .finally(() => { if (active) setCandidateLoading(false); });
    return () => { active = false; };
  }, []);

  const refreshCandidateCatalog = async () => {
    setCandidateLoading(true);
    try {
      setCandidateCameras(await api<RomanianCameraCandidate[]>("/api/cameras/discovery"));
      setCandidateError(false);
    } catch {
      setCandidateError(true);
    } finally {
      setCandidateLoading(false);
    }
  };

  useEffect(() => {
    if (USE_MOCKS) return;
    let active = true;
    void api<{ permissions?: string[] }>("/api/auth/me")
      .then((me) => { if (active) setCameraManageAllowed(hasBackendPermission(me.permissions, "cameras:manage")); })
      .catch(() => { if (active) setCameraManageAllowed(false); });
    return () => { active = false; };
  }, []);

  const openPlayer = (camId: string) => {
    const cam = realCameras.find((c) => c.id === camId);
    const list = alerts
      .filter((a) => a.cameraId === camId && a.clip?.src)
      .sort((x, y) => y.createdAt.localeCompare(x.createdAt))
      .map((a) => ({
        id: a.id, title: `${ALERT_TYPE[a.type]?.label ?? a.type} · ${cam?.name ?? camId}`, subtitle: fmtDateTime(a.createdAt),
        src: a.clip?.src, poster: a.keyframeUrl, at: a.createdAt,
        chip: USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={a.redaction} />,
      }));
    if (list.length) setPlayerClips(list);
  };

  const cameras = useMemo(
    () =>
      realCameras.map((c) => {
        const camAlerts = alerts.filter((a) => a.cameraId === c.id).sort((x, y) => y.createdAt.localeCompare(x.createdAt));
        const latest = camAlerts.find((a) => a.keyframeUrl);
        return {
          ...c,
          open: camAlerts.filter((a) => a.status === "new" || a.status === "in_review").length,
          clips: camAlerts.filter((a) => a.clip?.src).length,
          image: latest?.keyframeUrl,
          redaction: latest?.redaction,
          lastAlert: latest?.createdAt,
        };
      }),
    [realCameras, alerts],
  );

  const status = (c: (typeof cameras)[number]) =>
    c.status === "offline" ? { label: "Inactivă", dot: "bg-critical" } : c.live ? { label: "Activă (semnal recent)", dot: "bg-ok" } : { label: "Fără semnal recent", dot: "bg-caution" };
  const active = cameras.filter((c) => c.live && c.status !== "offline").length;

  return (
    <div className="flex flex-col p-3 sm:p-6 gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="eyebrow">Rețea</p>
          <h1 className="font-display text-3xl font-bold tracking-tight">Camere</h1>
          <p className="text-sm text-text-secondary mt-1">{cameras.length} camere · {active} cu semnal recent (heartbeat din ultimele 2 minute)</p>
        </div>
        <div role="group" aria-label="Mod de afișare" className="inline-flex rounded-lg border border-border overflow-hidden bg-panel/70">
          {([["grid", "Listă", Grid], ["map", "Hartă", MapIcon]] as const).map(([v, label, Icon]) => (
            <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}
              className={`press flex items-center gap-1.5 px-3.5 min-h-[var(--target-min)] text-sm cursor-pointer ${view === v ? "bg-elevation text-action font-semibold" : "text-text-secondary hover:text-text-primary"}`}>
              <Icon size={15} aria-hidden="true" /> {label}
            </button>
          ))}
        </div>
        {cameraManageAllowed && !USE_MOCKS && <Button onClick={() => setCreatingCamera(true)}><Plus size={15} aria-hidden="true" /> Adaugă cameră</Button>}
      </div>

      {view === "map" ? (
        <div className="h-[65dvh] min-h-80 card overflow-hidden rise">
          <TacticalMap />
        </div>
      ) : cameras.length === 0 ? (
        <EmptyState title="Nicio cameră" hint="Camerele apar după ce sunt configurate în sistem." />
      ) : (
        <ul className="stagger grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {cameras.map((cam) => {
            const st = status(cam);
            return (
              <li key={cam.id} className="cam-card group card flex flex-col overflow-hidden hover:border-action/50 hover:-translate-y-0.5 hover:shadow-[var(--shadow-2)] focus-within:border-action/60">
                <div className={`relative aspect-[16/10] flex items-center justify-center ${cam.image ? "bg-black" : "bg-elevation"}`}>
                  {cam.image ? (
                    <img src={cam.image} alt={`Ultimul cadru cu alertă, ${cam.name}`} loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-500" />
                  ) : (
                    <span className="text-sm text-text-secondary px-4 text-center flex flex-col items-center gap-2"><VideoOff size={28} aria-hidden="true" className="text-text-muted" /><span>Fără imagine: nicio alertă cu cadru cheie</span></span>
                  )}
                  {cam.image && <div className="absolute top-2 left-2">{USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={cam.redaction} />}</div>}
                </div>
                <div className="p-3 flex flex-col gap-2">
                  <div>
                    <h2 className="font-display text-base font-semibold truncate">{cam.name}</h2>
                    {cam.road && <p className="text-xs text-text-secondary truncate">{cam.road}</p>}
                  </div>
                  <p className="text-sm flex items-center gap-2"><span className={`w-2.5 h-2.5 rounded-full ${st.dot} ${st.dot === "bg-ok" ? "live-dot text-ok" : ""}`} aria-hidden="true" />{st.label}</p>
                  {cam.fps > 0 && <p className="text-xs text-text-secondary">Cadre sursă/s: {cam.fps.toFixed(2)} · procesare: {(cam.processingFps ?? 0).toFixed(2)} FPS</p>}
                  {cam.sourceHealth && <p className="text-xs text-text-secondary">Sursă: {sourceLabel(cam)}{cam.sourceHealth.transport && cam.sourceHealth.transport !== "auto" ? ` · ${cam.sourceHealth.transport.toUpperCase()}` : ""}{cam.sourceHealth.width && cam.sourceHealth.height ? ` · ${cam.sourceHealth.width}×${cam.sourceHealth.height}` : ""}{cam.sourceHealth.reconnects ? ` · reconectări ${cam.sourceHealth.reconnects}` : ""}</p>}
                  {cam.sourceHealth && <p className="text-xs text-text-secondary">Observații: {cam.detections ?? 0} · piste: {cam.uniqueTracks ?? 0} · p95: {cam.inferenceLatencyP95Ms?.toFixed(1) ?? "—"} ms</p>}
                  {cam.traffic && <p className="text-xs text-text-secondary">Numărări la linii: {cam.traffic.total_crossings} · flux detectat: {cam.traffic.rolling_flow_per_minute.total.toFixed(1)}/min (fereastră {cam.traffic.rolling_flow_per_minute.window_seconds}s)</p>}
                  {!!cam.unsupportedRules?.length && (
                    <p className="text-xs text-caution" role="note">
                      Nu poate produce la acest ritm: {cam.unsupportedRules.map((r) => ALERT_TYPE[r.rule as AlertType].label).join(", ")}.
                    </p>
                  )}
                  <p className="text-xs text-text-secondary">{cam.open} alerte de verificat{cam.lastAlert ? ` · ultima alertă ${fmtDateTime(cam.lastAlert)}` : ""}</p>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" onClick={() => setDetailCamera(cam)}><Activity size={14} aria-hidden="true" /> Detalii live</Button>
                    <Button size="sm" variant="secondary" disabled={cam.clips === 0} onClick={() => openPlayer(cam.id)}>Clipuri ({cam.clips})</Button>
                    {cameraManageAllowed && !USE_MOCKS && cam.backendUuid && <Button size="sm" variant="secondary" onClick={() => setEditingCamera(cam)}><Pencil size={14} aria-hidden="true" /> Editează metadatele</Button>}
                    <Link to="/app/arhiva" state={{ search: cam.name }} className="press inline-flex items-center px-3 min-h-[var(--target-min)] rounded-lg border border-border text-xs hover:border-action">Istoric</Link>
                    {LIVE_STREAM && cam.liveUrl && <Button size="sm" variant="secondary" onClick={() => setLiveCam({ name: cam.name, url: cam.liveUrl! })}>Flux extern (demo)</Button>}
                  </div>
                  {cameraManageAllowed && !USE_MOCKS && cam.backendUuid && <><CameraWorkerControls cameraId={cam.backendUuid} /><Button size="sm" variant="secondary" onClick={() => setControlCamera(cam.backendUuid!)}>Control și configurare</Button>{controlCamera === cam.backendUuid && <CameraControlPanel cameraId={cam.backendUuid} isAdmin={cameraManageAllowed} onClose={() => setControlCamera(null)} />}</>}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {!USE_MOCKS && <RomanianCameraExperience cameras={candidateCameras} loading={candidateLoading} error={candidateError} canManage={cameraManageAllowed} onRetry={() => void refreshCandidateCatalog()} />}

      {playerClips && <ClipModal clips={playerClips} onClose={() => setPlayerClips(null)} />}
        {detailCamera && <CameraTelemetryDialog camera={cameras.find((c) => c.id === detailCamera.id) ?? detailCamera} onClose={() => setDetailCamera(null)} />}
        {editingCamera && <CameraMetadataDialog camera={editingCamera} onClose={() => setEditingCamera(null)} />}
      {creatingCamera && <CameraCreateDialog onClose={() => setCreatingCamera(false)} />}
      {liveCam && (
        <Dialog open title={`${liveCam.name}: flux public extern (demo)`} onClose={() => setLiveCam(null)} wide>
          <Suspense fallback={<p className="text-sm text-text-secondary">Se încarcă playerul…</p>}>
            <LivePlayer src={liveCam.url} className="w-full aspect-video rounded-md border border-border" controls />
          </Suspense>
          <p className="text-sm text-text-secondary">Flux public al unui terț, nefiltrat și neredactat, activat doar prin VITE_LIVE_STREAM=1. Nu face parte din dovezile sistemului.</p>
          <div className="flex justify-end"><Button variant="secondary" onClick={() => setLiveCam(null)}>Închide</Button></div>
        </Dialog>
      )}
    </div>
  );
}

function CameraTelemetryDialog({ camera, onClose }: { camera: Camera; onClose: () => void }) {
  const classes = Object.entries(camera.tracksByClass ?? {}).sort((a, b) => b[1] - a[1]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewAt, setPreviewAt] = useState<string | null>(null);
  const [previewSequence, setPreviewSequence] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<"waiting" | "live" | "offline" | "denied">("waiting");

  useEffect(() => {
    if (USE_MOCKS || !camera.backendUuid) return;
    let active = true;
    let busy = false;
    let latestObjectUrl: string | null = null;
    const urls = new Set<string>();
    const refresh = async () => {
      if (busy || !active) return;
      busy = true;
      try {
        const response = await fetch(apiUrl(`/api/cameras/${camera.backendUuid}/preview`), {
          credentials: "include",
          cache: "no-store",
        });
        if (response.status === 403 || response.status === 401) {
          if (active) setPreviewState("denied");
          return;
        }
        if (response.status === 404) {
          if (active && latestObjectUrl) {
            URL.revokeObjectURL(latestObjectUrl);
            urls.delete(latestObjectUrl);
            latestObjectUrl = null;
            setPreviewUrl(null);
            setPreviewAt(null);
            setPreviewSequence(null);
            setPreviewState("offline");
          } else if (active) setPreviewState("waiting");
          return;
        }
        if (!response.ok) throw new Error(`preview HTTP ${response.status}`);
        const next = URL.createObjectURL(await response.blob());
        urls.add(next);
        if (!active) return;
        const previous = latestObjectUrl;
        latestObjectUrl = next;
        setPreviewUrl(next);
        setPreviewAt(response.headers.get("X-RS-Captured-At"));
        setPreviewSequence(response.headers.get("X-RS-Frame-Sequence"));
        setPreviewState("live");
        if (previous) window.setTimeout(() => { URL.revokeObjectURL(previous); urls.delete(previous); }, 1500);
      } catch {
        if (active) {
          if (latestObjectUrl) {
            URL.revokeObjectURL(latestObjectUrl);
            urls.delete(latestObjectUrl);
            latestObjectUrl = null;
          }
          setPreviewUrl(null);
          setPreviewAt(null);
          setPreviewSequence(null);
          setPreviewState("offline");
        }
      } finally {
        busy = false;
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 750);
    return () => {
      active = false;
      window.clearInterval(timer);
      for (const url of urls) URL.revokeObjectURL(url);
    };
  }, [camera.backendUuid]);

  return <Dialog open title={`Stare și analize · ${camera.name}`} onClose={onClose}>
    <section className="mb-4 overflow-hidden rounded-xl border border-border bg-black" aria-label="Previzualizare video cu detecții">
      {previewUrl ? <img
        key={previewSequence ?? previewUrl}
        src={previewUrl}
        alt={`Cadru procesat cu detecții YOLO și linii de numărare · ${camera.name}`}
        data-testid="camera-live-preview"
        data-captured-at={previewAt ?? ""}
        className="block w-full aspect-video object-contain"
      /> : <div className="flex aspect-video items-center justify-center p-4 text-center text-sm text-text-secondary" role="status">
        {previewState === "waiting" ? "Se așteaptă primul cadru anotat al procesării…" : previewState === "denied" ? "Previzualizarea necesită o sesiune autorizată pentru această cameră." : previewState === "offline" ? "Previzualizarea nu este disponibilă; verificați starea sursei." : "Previzualizarea nu este activată în modul demo."}
      </div>}
      <p className="px-3 py-2 text-xs text-text-secondary">
        {previewState === "offline" ? "OFFLINE / CADRU EXPIRAT" : sourceLabel(camera)}
        {previewAt ? ` · capturat ${fmtDateTime(previewAt)}` : ""}
        {previewSequence ? ` · cadru #${previewSequence}` : ""}
      </p>
    </section>
    <div className="grid grid-cols-2 gap-3 text-sm">
      <Metric label="Stare sursă" value={sourceLabel(camera)} />
      <Metric label="Cadre procesate" value={`${(camera.processingFps ?? 0).toFixed(2)} FPS`} testId="camera-processing-fps" />
      <Metric label="Vehicule și obiecte detectate" value={String(camera.detections ?? 0)} testId="camera-detections" />
      <Metric label="Piste unice" value={String(camera.uniqueTracks ?? 0)} />
      <Metric label="P95 inferență" value={camera.inferenceLatencyP95Ms == null ? "—" : `${camera.inferenceLatencyP95Ms.toFixed(1)} ms`} />
      <Metric label="Memorie maximă proces" value={camera.processPeakRssMb == null ? "—" : `${camera.processPeakRssMb.toFixed(0)} MB`} />
      <Metric label="Model" value={camera.model ?? "—"} />
    </div>
    <section className="mt-4" aria-label="Piste după clasă"><h3 className="text-sm font-semibold">Piste după clasă</h3>
      {classes.length ? <ul className="mt-2 grid grid-cols-2 gap-2 text-sm">{classes.map(([name, count]) => <li key={name} className="rounded border border-border p-2">{name}: <strong>{count}</strong></li>)}</ul> : <p className="mt-2 text-sm text-text-secondary">Așteaptă prima bătaie de stare cu rezultate de model.</p>}
    </section>
    <section className="mt-4"><h3 className="text-sm font-semibold">Numărări la linii</h3><p data-testid="camera-crossings" className="mt-1 text-sm text-text-secondary">{camera.traffic?.total_crossings ?? 0} traversări · flux curent: {camera.traffic?.rolling_flow_per_minute.total.toFixed(1) ?? "0.0"}/min</p>
      {camera.traffic?.counts_by_line_lane_class.map((row) => <p key={`${row.line}-${row.lane}-${row.object_class}`} className="text-xs text-text-secondary">{row.line} / {row.lane} / {row.object_class}: {row.count}</p>)}
    </section>
    {camera.modelSha256 && <p className="mt-3 break-all text-xs text-text-muted">SHA-256: {camera.modelSha256}</p>}
    <p className="mt-3 text-xs text-text-secondary">Actualizat: <time data-testid="camera-reported-at" dateTime={camera.telemetryAt}>{camera.telemetryAt ?? "fără telemetrie"}</time> · ecranul reîncarcă starea din backend la 3 s. Valorile sunt măsurători ale detectorului, nu adevăr de referință.</p>
  </Dialog>;
}

function Metric({ label, value, testId }: { label: string; value: string; testId?: string }) {
  return <div className="rounded border border-border p-2"><p className="text-xs text-text-secondary">{label}</p><p data-testid={testId} className="mt-1 font-semibold">{value}</p></div>;
}

function CameraCreateDialog({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [location, setLocation] = useState("");
  const [timezone, setTimezone] = useState("Europe/Bucharest");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      await api("/api/cameras", { method: "POST", body: JSON.stringify({
        name: name.trim(), slug: slug.trim(), location: location.trim(), timezone: timezone.trim(),
      }) });
      const rows = await api<ApiCamera[]>("/api/cameras");
      useDataStore.setState({ cameras: rows.map(adaptCamera) });
      onClose();
    } catch (reason) {
      setError((reason as Error).message || "Camera nu a putut fi adăugată. Verifică MFA și ID-ul unic.");
    } finally { setSaving(false); }
  }

  return <Dialog open title="Adaugă o cameră" onClose={onClose} describedBy="camera-create-note">
    <p id="camera-create-note" className="mb-3 text-sm text-text-secondary">Camera este creată în tenantul curent și auditata. Pentru procesare, profilul local `cameras/*.yaml` trebuie să folosească același slug; pornirea workerului este separată.</p>
    <form onSubmit={(event) => void create(event)} className="grid gap-3">
      <Field label="Nume cameră">{(attrs) => <TextInput {...attrs} value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={200} required />}</Field>
      <Field label="ID cameră (slug)" hint="1–64 litere, cifre, _ sau -. Trebuie să coincidă cu id-ul profilului local.">{(attrs) => <TextInput {...attrs} value={slug} onChange={(e) => setSlug(e.target.value)} minLength={1} maxLength={64} pattern="(?:[A-Za-z0-9]|-|_)+" required />}</Field>
      <Field label="Locație / drum">{(attrs) => <TextInput {...attrs} value={location} onChange={(e) => setLocation(e.target.value)} minLength={2} maxLength={300} required />}</Field>
      <Field label="Fus orar IANA">{(attrs) => <TextInput {...attrs} value={timezone} onChange={(e) => setTimezone(e.target.value)} maxLength={64} required />}</Field>
      {error && <p role="alert" className="text-sm text-critical">{error}</p>}
      <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={saving} onClick={onClose}>Anulează</Button><Button type="submit" loading={saving}>Adaugă camera</Button></div>
    </form>
  </Dialog>;
}

function CameraMetadataDialog({ camera, onClose }: { camera: Camera; onClose: () => void }) {
  const [name, setName] = useState(camera.name);
  const [location, setLocation] = useState(camera.road);
  const [latitude, setLatitude] = useState(Number.isFinite(camera.lat) ? String(camera.lat) : "");
  const [longitude, setLongitude] = useState(Number.isFinite(camera.lng) ? String(camera.lng) : "");
  const [timezone, setTimezone] = useState(camera.timezone ?? "Europe/Bucharest");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!camera.backendUuid) return;
    const hasLatitude = latitude.trim() !== "";
    const hasLongitude = longitude.trim() !== "";
    if (hasLatitude !== hasLongitude) {
      setError("Introduceți ambele coordonate sau lăsați-le pe ambele necompletate.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await api<{ name: string; location: string; latitude: number | null; longitude: number | null }>(
        `/api/cameras/${camera.backendUuid}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            name: name.trim(),
            location: location.trim(),
            latitude: hasLatitude ? Number(latitude) : null,
            longitude: hasLongitude ? Number(longitude) : null,
            timezone: timezone.trim(),
          }),
        },
      );
      useDataStore.setState((state) => ({
        cameras: state.cameras.map((item) => item.backendUuid === camera.backendUuid
          ? { ...item, name: updated.name, road: updated.location, lat: updated.latitude ?? Number.NaN, lng: updated.longitude ?? Number.NaN, timezone: timezone.trim() }
          : item),
      }));
      onClose();
    } catch (e) {
      setError((e as Error).message || "Metadatele camerei nu au putut fi salvate.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open title={`Metadate cameră: ${camera.name}`} onClose={onClose} describedBy="camera-edit-note">
      <p id="camera-edit-note" className="text-sm text-text-secondary">
        Modificările sunt înregistrate în audit. Această acțiune schimbă doar metadatele din registrul camerelor.
      </p>
      <form onSubmit={(e) => void save(e)} className="grid gap-3 sm:grid-cols-2">
        <Field label="Nume cameră">
          {(a) => <TextInput {...a} value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={200} required />}
        </Field>
        <Field label="Locație / drum">
          {(a) => <TextInput {...a} value={location} onChange={(e) => setLocation(e.target.value)} minLength={2} maxLength={300} required />}
        </Field>
        <Field label="Latitudine" hint="WGS84, −90 … 90; împreună cu longitudinea.">
          {(a) => <TextInput {...a} type="number" step="any" min={-90} max={90} value={latitude} onChange={(e) => setLatitude(e.target.value)} />}
        </Field>
        <Field label="Longitudine" hint="WGS84, −180 … 180; împreună cu latitudinea.">
          {(a) => <TextInput {...a} type="number" step="any" min={-180} max={180} value={longitude} onChange={(e) => setLongitude(e.target.value)} />}
        </Field>
        <div className="sm:col-span-2">
          <Field label="Fus orar IANA" hint="Exemplu: Europe/Bucharest">
            {(a) => <TextInput {...a} value={timezone} onChange={(e) => setTimezone(e.target.value)} maxLength={64} required />}
          </Field>
        </div>
        {error && <p className="sm:col-span-2 text-sm text-critical" role="alert">{error}</p>}
        <div className="sm:col-span-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Anulează</Button>
          <Button type="submit" loading={saving}>Salvează metadatele</Button>
        </div>
      </form>
    </Dialog>
  );
}
