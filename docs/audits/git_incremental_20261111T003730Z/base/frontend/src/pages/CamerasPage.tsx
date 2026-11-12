import { useState, useMemo, useEffect } from "react";
import { Link } from "react-router";
import { Grid, Map as MapIcon, AlertTriangle, Eye, History, Radio, X, SlidersHorizontal } from "lucide-react";
import { useDataStore } from "@/store/data";
import { useAuthStore } from "@/store/auth";
import { USE_MOCKS } from "@/lib/api";
import { listControl, SOURCE_LABEL, STATE_LABEL, type ControlSummary } from "@/lib/cameraControl";
import { CameraControlPanel, StateBadge } from "@/components/CameraControlPanel";
import TacticalMap from "@/components/TacticalMap";
import { ClipModal, type ModalClip } from "@/components/ClipModal";
import { ALERT_TYPE } from "@/lib/constants";
import { LiveBadge, LivePlayer } from "@/components/LivePlayer";

// MOCK: Supplementary telemetry, thumbnails, coordinates, and offline state
interface CameraExtended {
  id: string;
  name: string;
  location: string;
  status: "online" | "offline" | "degraded";
  coords?: string;
  speed_avg?: string;
  alerts_count?: number;
  last_seen?: string;
  image_url?: string;
  video_url?: string;
  live_url?: string;
  heartbeat?: boolean;
  live?: boolean;
}

export default function CamerasPage() {
  const realCameras = useDataStore((st) => st.cameras);
  const alerts = useDataStore((st) => st.alerts);
  const [viewMode, setViewMode] = useState<"grid" | "map">("grid");
  const [hoveredCam, setHoveredCam] = useState<string | null>(null);
  const [playerClips, setPlayerClips] = useState<ModalClip[] | null>(null);
  const [liveCam, setLiveCam] = useState<CameraExtended | null>(null);
  // Control plane status (real API only): truthful runtime state per camera slug.
  const isAdmin = useAuthStore((st) => st.user?.role === "admin");
  const [controls, setControls] = useState<Record<string, ControlSummary>>({});
  const [controlCam, setControlCam] = useState<string | null>(null);
  useEffect(() => {
    if (USE_MOCKS) return;
    const load = () => listControl()
      .then((list) => setControls(Object.fromEntries(list.map((c) => [c.slug, c]))))
      .catch(() => setControls({})); // no status permission: cards keep the basic view
    void load();
    const timer = window.setInterval(load, 15_000);
    return () => window.clearInterval(timer);
  }, [controlCam]);
  const openPlayer = (camId: string) => {
    const cam = realCameras.find((c) => c.id === camId);
    const list = alerts.filter((a) => a.cameraId === camId && a.clip?.src).sort((x, y) => y.createdAt.localeCompare(x.createdAt))
      .map((a) => ({ id: a.id, title: `${ALERT_TYPE[a.type]?.label ?? a.type} · ${cam?.name ?? camId}`, subtitle: `${cam?.road ?? ""} · ${new Date(a.createdAt).toLocaleString("ro-RO")}`, src: a.clip?.src, poster: a.keyframeUrl, at: a.createdAt }));
    if (list.length) setPlayerClips(list);
  };

  // Real cameras; image = latest alert keyframe of that camera; counts = open alerts.
  const cameras: CameraExtended[] = useMemo(() => realCameras.map((c) => {
    const camAlerts = alerts.filter((a) => a.cameraId === c.id).sort((x, y) => y.createdAt.localeCompare(x.createdAt));
    const latest = camAlerts.find((a) => a.keyframeUrl);
    return {
      id: c.id, name: c.name, location: c.road || c.id, status: c.status === "offline" ? "offline" : "online",
      alerts_count: camAlerts.filter((a) => a.status === "new" || a.status === "in_review").length,
      image_url: latest?.keyframeUrl ?? `/cams/${c.id}.jpg`, video_url: c.videoUrl, live_url: c.liveUrl, heartbeat: c.heartbeat, live: c.live,
      last_seen: latest ? new Date(latest.createdAt).toLocaleString("ro-RO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : undefined,
    };
  }), [realCameras, alerts]);

  const onlineCount = cameras.filter(c => c.status === "online").length;
  const offlineCount = cameras.length - onlineCount;

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 gap-5 bg-deep-void">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div>
          <h1 className="font-heading text-3xl font-bold tracking-tight text-text-primary uppercase">
            Camere de trafic
          </h1>
          <div className="flex items-center gap-3 text-xs text-text-secondary mt-1 font-mono">
            <span>{onlineCount} online · {offlineCount} fără semnal</span>
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block shadow-[0_0_8px_#2ED47A]" />
              online
            </span>
            <span className="flex items-center gap-1 text-rose-500">
              <span className="w-2 h-2 rounded-full bg-rose-500 inline-block shadow-[0_0_8px_#FF3B3B]" />
              fără semnal
            </span>
          </div>
        </div>

        {/* View Mode & Add Camera */}
        <div className="flex items-center gap-4">
          <div className="flex items-center bg-panel border border-border rounded-md p-1 text-xs">
            <span className="text-text-secondary px-2 font-sans font-medium">Vizualizare:</span>
            <button
              onClick={() => setViewMode("grid")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${
                viewMode === "grid"
                  ? "bg-accent/20 text-accent font-semibold border border-accent/40"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              <span>[Grilă]</span>
            </button>
            <span className="text-border px-1">/</span>
            <button
              onClick={() => setViewMode("map")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${
                viewMode === "map"
                  ? "bg-accent/20 text-accent font-semibold border border-accent/40"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              <MapIcon className="w-3.5 h-3.5" />
              <span>Hartă</span>
            </button>
          </div>

        </div>
      </div>

      {/* Main Content Area: 5-column grid or Map */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {viewMode === "map" ? (
          <div className="h-full rounded-md border border-border bg-panel overflow-hidden relative shadow-lg">
            <TacticalMap />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5 pb-4">
            {cameras.map((cam) => {
              const isOffline = cam.status === "offline";
              const isHovered = hoveredCam === cam.id;
              const control = controls[cam.id];

              return (
                <div
                  key={cam.id}
                  onMouseEnter={() => setHoveredCam(cam.id)}
                  onMouseLeave={() => setHoveredCam(null)}
                  className={`group relative flex flex-col rounded-md bg-panel border transition-all duration-200 overflow-hidden ${
                    isHovered
                      ? "border-accent shadow-[0_0_16px_rgba(61,165,255,0.35)]"
                      : isOffline
                      ? "border-rose-500/40 bg-rose-950/10"
                      : "border-border hover:border-border-highlight"
                  }`}
                >
                  {/* Top Bar OSD */}
                  <div className="flex items-center justify-between px-2.5 py-1.5 bg-elevation/90 border-b border-border/80 text-[10px] font-mono text-text-secondary">
                    <span className="font-semibold text-text-primary truncate" title={cam.location}>{cam.name}</span>
                    <span>{cam.last_seen ? `ultima alertă ${cam.last_seen}` : "fără alerte"}</span>
                  </div>

                  {/* Camera Monitor Preview Box */}
                  <div className="relative aspect-[16/10] bg-black/80 flex items-center justify-center overflow-hidden">
                    {isOffline ? (
                      <div className="flex flex-col items-center justify-center text-rose-500 gap-1.5 p-4 text-center">
                        <AlertTriangle className="w-8 h-8 animate-pulse text-rose-500" />
                        <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono text-[10px] border border-rose-500/40 font-bold">
                          FĂRĂ SEMNAL
                        </span>
                      </div>
                    ) : (
                      <>
                        {cam.heartbeat && cam.live_url ? (
                          <LivePlayer src={cam.live_url} className="w-full h-full" />
                        ) : (
                          <img
                            src={cam.image_url || `/cams/${cam.id}.jpg`}
                            alt={cam.name}
                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                            onError={(e) => {
                              const img = e.currentTarget as HTMLImageElement; if (!img.src.endsWith(`/cams/${cam.id}.jpg`)) img.src = `/cams/${cam.id}.jpg`;
                            }}
                          />
                        )}

                        {/* Top-left status badge: server-computed state when the control plane knows
                            the camera (a replay is never LIVE); else LIVE only for a declared live source */}
                        <div className="absolute top-2 left-2">
                          {control ? (
                            <StateBadge state={control.runtime.state} />
                          ) : cam.live ? (
                            <LiveBadge />
                          ) : (
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md border border-emerald-500/30 text-[10px] font-mono text-emerald-400">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              <span>Online</span>
                            </div>
                          )}
                        </div>

                        {/* Top-right Alert Badge */}
                        <div className="absolute top-2 right-2">
                          {cam.alerts_count && cam.alerts_count > 0 ? (
                            <span className={`px-2 py-0.5 rounded text-[10px] font-medium font-mono border ${
                              cam.alerts_count >= 2
                                ? "bg-rose-500/30 text-rose-400 border-rose-500/50"
                                : "bg-amber-500/30 text-amber-400 border-amber-500/50"
                            }`}>
                              {cam.alerts_count} {cam.alerts_count === 1 ? "alertă" : "alerte"}
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono text-text-secondary bg-black/60 border border-border">
                              0 alerte
                            </span>
                          )}
                        </div>

                        {/* Hover Overlay Action Buttons */}
                        {isHovered && (
                          <div className="absolute inset-0 bg-deep-void/70 backdrop-blur-sm flex items-center justify-center gap-2 p-3 transition-opacity">
                            {cam.live_url && (
                              <button
                                type="button"
                                onClick={() => setLiveCam(cam)}
                                className="flex-1 cursor-pointer flex items-center justify-center gap-1.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded transition-colors"
                              >
                                <Radio className="w-3.5 h-3.5" />
                                <span>{cam.live ? "Live" : "Flux video"}</span>
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => openPlayer(cam.id)}
                              className="flex-1 cursor-pointer flex items-center justify-center gap-1.5 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-semibold rounded shadow-glow-accent transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>Redă clipuri</span>
                            </button>
                            <Link
                              to={`/app/arhiva?camera=${cam.id}`}
                              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-elevation hover:bg-border text-text-primary text-xs font-medium rounded border border-border transition-colors"
                            >
                              <History className="w-3.5 h-3.5" />
                              <span>Istoric</span>
                            </Link>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Bottom Info & Telemetry Bar */}
                  <div className="p-2.5 bg-panel flex flex-col gap-1 border-t border-border/60">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-text-primary truncate">
                        {cam.name}
                      </span>
                    </div>

                    {control && (
                      <div className="flex items-center justify-between gap-2 text-[10px] font-mono text-text-secondary" data-testid={`control-${cam.id}`}>
                        <span className="truncate" title={control.source_display ?? undefined}>
                          {control.source_kind ? SOURCE_LABEL[control.source_kind] : "Sursă nedeclarată"}
                          {control.runtime.applied_revision != null && ` · r${control.runtime.applied_revision} aplicată`}
                        </span>
                        <button
                          type="button"
                          onClick={() => setControlCam(control.id)}
                          className="flex items-center gap-1 px-1.5 py-0.5 rounded border border-border hover:border-accent text-text-primary"
                          aria-label={`Control ${cam.name}`}
                        >
                          <SlidersHorizontal className="w-3 h-3" />
                          Control
                        </button>
                      </div>
                    )}
                    {control ? (
                      <div className="text-[11px] font-mono text-text-secondary">
                        {STATE_LABEL[control.runtime.state] ?? control.runtime.state} · {cam.alerts_count ?? 0} alerte deschise
                      </div>
                    ) : isOffline ? (
                      <div className="text-[11px] text-rose-400 font-mono">
                        Fără semnal{cam.last_seen ? ` · ultima alertă ${cam.last_seen}` : ""}
                      </div>
                    ) : (
                      <div className="flex items-center justify-between text-[10px] font-mono text-text-secondary pt-0.5">
                        <span className="flex items-center gap-1 text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          Online
                        </span>
                        <span>{cam.alerts_count ?? 0} alerte deschise</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {playerClips && <ClipModal clips={playerClips} onClose={() => setPlayerClips(null)} />}
      {controlCam && <CameraControlPanel cameraId={controlCam} isAdmin={isAdmin} onClose={() => setControlCam(null)} />}
      {liveCam?.live_url && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6" onClick={() => setLiveCam(null)}>
          <div className="w-full max-w-6xl flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between text-sm text-text-primary">
              <div className="flex items-center gap-3">
                {liveCam.live && <LiveBadge />}
                <span className="font-semibold">{liveCam.name}</span>
                <span className="text-text-secondary text-xs">{liveCam.location}</span>
              </div>
              <button type="button" onClick={() => setLiveCam(null)} className="p-1 rounded hover:bg-elevation" aria-label="Închide">
                <X className="w-5 h-5" />
              </button>
            </div>
            <LivePlayer src={liveCam.live_url} className="w-full aspect-video rounded-md border border-border" controls />
            <p className="text-[11px] text-text-secondary font-mono">
              Flux public brut. Detecțiile rulează pe server, iar alertele apar în panou cu clipul ±3 s.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
