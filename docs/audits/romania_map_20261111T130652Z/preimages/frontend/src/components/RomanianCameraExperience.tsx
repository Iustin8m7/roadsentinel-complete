import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { ExternalLink, Radio, Search, VideoOff } from "lucide-react";
import { useSearchParams } from "react-router";
import type { RomanianCameraCandidate } from "@/romanianCameraCandidates";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { CameraWorkerControls } from "@/components/CameraWorkerControls";

const LivePlayer = lazy(() => import("@/components/LivePlayer").then((m) => ({ default: m.LivePlayer })));

type Props = { cameras: RomanianCameraCandidate[]; loading: boolean; error: boolean; canManage: boolean; onRetry: () => void };
type PlayerState = "idle" | "connecting" | "playing" | "stalled" | "error";
type ProvisionedCamera = { id: string; slug: string; name: string };

function area(camera: RomanianCameraCandidate) {
  const id = camera.id;
  if (id.includes("-IS-")) return "Iași";
  if (id.includes("-BV-")) return "Brașov";
  if (id.includes("-CJ-")) return "Cluj";
  if (id.includes("DN1")) return "DN1";
  if (id.includes("DN17")) return "DN17";
  if (id.includes("A2")) return "A2";
  if (id.includes("DIGI-PIT") || id.includes("PIT-INF")) return "A1 · Pitești";
  if (id.includes("INF")) return "DN7";
  return "Alte zone";
}

function badge(camera: RomanianCameraCandidate, state: PlayerState, selected: boolean) {
  if (camera.sourceKind === "recorded_timelapse") return "RECORDED TIMELAPSE";
  if (camera.presentationResult === "unavailable") return "OFFLINE / INDISPONIBIL";
  if (camera.sourceKind === "refreshed_snapshot") return camera.sourceLabel || "REFRESHED SNAPSHOT";
  if (state === "playing" && selected) return "LIVE VIEW AVAILABLE";
  if (camera.playerKind === "supported_hls") return state === "error" ? "PLAYER INDISPONIBIL" : "PLAYER HLS · NEVERIFICAT";
  if (camera.playerKind === "official_iframe") return state === "error" ? "EMBED REFUZAT · OPEN ON PROVIDER" : "OFFICIAL EMBED · SNAPSHOT";
  return "OPEN ON PROVIDER";
}

export function RomanianCameraExperience({ cameras, loading, error, canManage, onRetry }: Props) {
  const [params, setParams] = useSearchParams();
  const requestedId = params.get("camera");
  const [selectedId, setSelectedId] = useState(requestedId ?? "");
  const [query, setQuery] = useState("");
  const [feedFilter, setFeedFilter] = useState("all");
  const [availability, setAvailability] = useState("all");
  const [playerState, setPlayerState] = useState<PlayerState>("idle");
  const [retry, setRetry] = useState(0);
  const [operationalCamera, setOperationalCamera] = useState<ProvisionedCamera | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [provisionError, setProvisionError] = useState("");
  const selected = cameras.find((item) => item.id === selectedId) ?? cameras[0];
  useEffect(() => {
    if (!selected || selected.playerKind !== "official_iframe" || !["idle", "connecting"].includes(playerState)) return;
    const timeout = window.setTimeout(() => setPlayerState("error"), 12000);
    return () => window.clearTimeout(timeout);
  }, [selected?.id, selected?.playerKind, playerState]);
  const filtered = useMemo(() => cameras.filter((item) => {
    const text = `${item.title} ${item.city} ${item.roadway} ${item.ownerProvider} ${area(item)}`.toLocaleLowerCase();
    const matchesQuery = text.includes(query.toLocaleLowerCase());
    const matchesFeed = feedFilter === "all" || (feedFilter === "live" ? item.sourceKind === "continuous_live" : feedFilter === "replay" ? item.sourceKind === "recorded_timelapse" : item.sourceKind === "refreshed_snapshot");
    const matchesAvailability = availability === "all" || (availability === "available" ? item.presentationResult === "documented" : item.presentationResult === "unavailable");
    return matchesQuery && matchesFeed && matchesAvailability;
  }), [cameras, query, feedFilter, availability]);
  const select = (item: RomanianCameraCandidate) => {
    setSelectedId(item.id);
    setParams((previous) => { const next = new URLSearchParams(previous); next.set("camera", item.id); return next; }, { replace: true });
    setPlayerState("idle");
    setOperationalCamera(null);
    setProvisionError("");
  };
  const provisionSelected = async () => {
    setProvisioning(true);
    setProvisionError("");
    try {
      setOperationalCamera(await api<ProvisionedCamera>("/api/cameras/provision/ilisesti-dn17", { method: "POST" }));
    } catch (reason) {
      setProvisionError((reason as Error).message || "Înregistrarea camerei a eșuat.");
    } finally {
      setProvisioning(false);
    }
  };
  const groupNames = [...new Set(filtered.map(area))];

  return <section className="card overflow-hidden" aria-labelledby="romanian-camera-title">
    <header className="border-b border-border bg-elevation/50 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="eyebrow">Surse publice · prezentare independentă de analiză</p><h2 id="romanian-camera-title" className="font-display text-2xl font-bold">Camere din România</h2>
          <p className="mt-1 max-w-3xl text-sm text-text-secondary">Deschide camera în RoadSentinel când există un player documentat, sau accesează pagina operatorului. Vizualizarea publică nu înseamnă permisiune de analiză automată.</p></div>
        <span className="rounded-full border border-border px-3 py-1.5 text-xs text-text-secondary">{loading ? "Se încarcă…" : `${cameras.length} intrări · ${cameras.filter((item) => item.ingestionEnabled).length} analize active`}</span>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-[minmax(12rem,1fr)_11rem_11rem]">
        <label className="flex items-center gap-2 rounded-lg border border-border bg-panel px-3"><Search size={16} aria-hidden="true"/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Caută oraș, drum sau cameră" aria-label="Caută camere românești" className="min-h-10 w-full bg-transparent text-sm outline-none"/></label>
        <select aria-label="Filtrează tipul sursei" value={feedFilter} onChange={(e) => setFeedFilter(e.target.value)} className="rounded-lg border border-border bg-panel px-3 text-sm"><option value="all">Toate tipurile</option><option value="live">Live declarat</option><option value="snapshot">Snapshot</option><option value="replay">Timelapse / replay</option></select>
        <select aria-label="Filtrează disponibilitatea" value={availability} onChange={(e) => setAvailability(e.target.value)} className="rounded-lg border border-border bg-panel px-3 text-sm"><option value="all">Toate stările</option><option value="available">Player documentat</option><option value="unavailable">Indisponibile</option></select>
      </div>
    </header>
    {error && <div role="alert" className="m-4 rounded-lg border border-caution/40 p-3 text-sm">Catalogul autentificat nu s-a încărcat. <Button size="sm" variant="secondary" onClick={onRetry}>Reîncearcă</Button></div>}
    {loading && cameras.length === 0 ? <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,2fr)_minmax(17rem,1fr)]" aria-label="Se încarcă camerele"><div className="aspect-video animate-pulse rounded-xl bg-elevation"/><div className="h-72 animate-pulse rounded-xl bg-elevation"/></div> : !selected ? <div className="p-8 text-center text-sm text-text-secondary">Nicio cameră nu corespunde filtrelor.</div> : <div className="grid lg:grid-cols-[minmax(0,2fr)_minmax(17rem,1fr)]">
      <div className="min-w-0 border-b border-border p-4 sm:p-5 lg:border-b-0 lg:border-r" aria-label="Previzualizare cameră selectată">
        <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-xl border border-border bg-black">
          {selected.playerKind === "supported_hls" && selected.playerUrl ? <Suspense fallback={<div className="text-sm text-white/70">Se încarcă playerul…</div>}><LivePlayer key={`${selected.id}-${retry}`} src={selected.playerUrl} controls className="h-full w-full" onStateChange={setPlayerState}/></Suspense> : selected.playerKind === "official_iframe" && selected.playerUrl ? <iframe key={selected.id} src={selected.playerUrl} title={`Player oficial ${selected.title} · ${selected.ownerProvider}`} loading="lazy" allow="fullscreen; picture-in-picture" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" className="h-full w-full border-0" onLoad={() => setPlayerState("connecting")} onError={() => setPlayerState("error")} /> : <div className="flex max-w-sm flex-col items-center gap-3 px-5 text-center text-white/80"><VideoOff size={36}/><span className="text-sm">{selected.sourceKind === "recorded_timelapse" ? "Înregistrare din ziua precedentă" : selected.presentationResult === "unavailable" ? "Imaginea nu este disponibilă în acest moment" : "Playerul individual nu este documentat pentru afișare aici"}</span></div>}
          <span className="absolute left-3 top-3 rounded-full border border-white/20 bg-black/70 px-2.5 py-1 text-[10px] font-bold tracking-wide text-white">{badge(selected, playerState, true)}</span>
        </div>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-3"><div><p className="eyebrow">{selected.city} · {selected.ownerProvider}</p><h3 className="font-display text-xl font-semibold">{selected.title}</h3><p className="mt-1 text-sm text-text-secondary">{selected.roadway}</p></div>
          <div className="flex gap-2">{selected.playerKind === "supported_hls" && <Button variant="secondary" size="sm" onClick={() => { setPlayerState("idle"); setRetry((n) => n + 1); }}>Reîncearcă playerul</Button>}<a href={selected.sourcePage} target="_blank" rel="noreferrer" className="press inline-flex min-h-[var(--target-min)] items-center gap-2 rounded-lg border border-action/50 px-3 text-sm text-action hover:bg-action/10"><ExternalLink size={15}/>Pagina operatorului</a></div>
        </div>
        <div className="mt-4 grid gap-2 rounded-lg border border-border bg-elevation/30 p-3 text-xs sm:grid-cols-2"><p><strong>Prezentare:</strong> {badge(selected, playerState, true)}</p><p><strong>Tip:</strong> {selected.sourceKind.replaceAll("_", " ")}</p><p><strong>Player:</strong> {selected.playerKind.replaceAll("_", " ")}</p><p><strong>Embed:</strong> {selected.embeddingPolicy}</p><p><strong>Analiză YOLO:</strong> {selected.id === "RO-DN17-WCR-001" ? "doar worker local cu scope tranzitoriu; fără înregistrare" : selected.ingestionEnabled ? "configurată" : "neconfigurată pentru acest candidat"}</p><p className="sm:col-span-2 text-text-secondary">{playerState === "error" ? "Redarea nu a pornit ori s-a oprit. Folosește pagina oficială a furnizorului." : selected.presentationFailureReason}</p></div>
        {selected.id === "RO-DN17-WCR-001" && canManage && <section className="mt-4 rounded-lg border border-action/30 bg-action/5 p-3" aria-label="Analiză locală Ilișești DN17">
          <div className="flex flex-wrap items-center justify-between gap-3"><div><h4 className="text-sm font-semibold">Analiză locală Ilișești DN17</h4><p className="mt-1 text-xs text-text-secondary">YOLOX rulează numai pe o imagine JPEG provider-published verificată ca proaspătă. Fără înregistrare sau export; snapshot cadence redusă nu activează reguli de mișcare.</p></div>{!operationalCamera && <Button size="sm" disabled={provisioning} onClick={() => void provisionSelected()}>{provisioning ? "Se configurează…" : "Configurează camera și analiza"}</Button>}</div>
          {provisionError && <p role="alert" className="mt-2 text-xs text-critical">{provisionError}</p>}
          {operationalCamera && <div className="mt-3"><p className="text-xs text-text-secondary">Cameră operațională: {operationalCamera.name} · {operationalCamera.slug}</p><CameraWorkerControls key={operationalCamera.id} cameraId={operationalCamera.id} initialConfigRef="ilisesti-dn17.yaml" /></div>}
        </section>}
      </div>
      <aside className="max-h-[70vh] overflow-y-auto p-3 sm:p-4" aria-label="Lista camerelor"><div className="flex items-center gap-2 px-2 pb-2 text-xs font-semibold text-text-secondary"><Radio size={14}/> CAMERE · SELECTEAZĂ O VIZUALIZARE</div>
        {groupNames.map((group) => <section key={group} className="mb-3"><h4 className="sticky top-0 z-10 bg-panel px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-text-muted">{group}</h4><ul className="space-y-1">{filtered.filter((item) => area(item) === group).map((item) => <li key={item.id}><button type="button" onClick={() => select(item)} aria-current={selected.id === item.id ? "true" : undefined} className={`w-full rounded-lg border p-2.5 text-left transition ${selected.id === item.id ? "border-action/60 bg-action/10" : "border-transparent hover:border-border hover:bg-elevation/50"}`}><span className="flex items-start justify-between gap-2"><span className="text-sm font-medium">{item.title}</span><span className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[9px] font-bold">{item.sourceKind === "recorded_timelapse" ? "REPLAY" : item.presentationResult === "unavailable" ? "OFFLINE" : item.playerKind === "supported_hls" ? "HLS" : "PROVIDER"}</span></span><span className="mt-1 block text-[11px] text-text-secondary">{item.ownerProvider} · {item.id}</span></button></li>)}</ul></section>)}
        {filtered.length === 0 && <p className="p-4 text-sm text-text-secondary">Nicio cameră nu corespunde căutării.</p>}
      </aside>
    </div>}
    <footer className="border-t border-border bg-elevation/20 px-4 py-3 text-[11px] text-text-muted">Sursa: paginile publice atribuite fiecărei intrări. „Live” poate fi o afirmație a editorului; nu afirmă că aici s-au decodat cadre. Previzualizarea nu pornește YOLO decât dacă un worker autorizat rulează separat.</footer>
  </section>;
}
