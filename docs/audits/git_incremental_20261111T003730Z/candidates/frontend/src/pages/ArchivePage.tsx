import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router";
<<<<<<< INTEGRATION
import { Search, Play, Bookmark, Trash2 } from "lucide-react";
import { api, mediaUrl, USE_MOCKS } from "@/lib/api";
import { useDataStore, cameraById, HIDDEN_TYPES } from "@/store/data";
import { HIDDEN_IDS, RECLASSIFY } from "@/lib/demo";
import { ALERT_TYPE } from "@/lib/constants";
import { fmtDateTime } from "@/lib/format";
import { Button, Chip, EmptyState, ErrorState, RedactionChip, Skeleton } from "@/components/ui";
import { Field, TextInput } from "@/components/forms";
=======
import { format } from "date-fns";
import { Bookmark, FolderOpen, Loader2, Play, Save, Search, SlidersHorizontal, Trash2, X } from "lucide-react";
import { mediaUrl, USE_MOCKS } from "@/lib/api";
import { ALERT_TYPE, STATUS_LABEL } from "@/lib/constants";
import { archiveAssignees, archiveRequest, deleteSaved, errorMessage, listSaved, saveSearch, searchArchive, type ArchiveFilters, type ArchiveRun, type FilterChip, type Person, type SavedSearch, type TokenInterpretation } from "@/lib/cases";
import { RECLASSIFY } from "@/lib/demo";
import { iasiCameraName } from "@/lib/iasi";
import type { ApiEvent } from "@/lib/adapters";
import { useDataStore } from "@/store/data";
>>>>>>> GITHUB_TARGET
import { ClipModal } from "@/components/ClipModal";
import type { Alert } from "@/types";
import { FolderArt } from "@/components/Illustrations";

interface ApiHit {
  id: string | number; type: string; camera_id: string; camera_name?: string; location?: string;
  occurred_at?: string; object_class?: string; keyframe_url: string | null; clip_url: string | null; redaction?: string | null;
}

interface SavedSearch {
  id: string;
  name: string;
  created_at: string;
}

interface ArchiveClip {
  id: string;
  camera_name: string;
  createdAt: string;
  label: string;
  object?: string;
  thumbnail_url: string;
  clip_url?: string;
  redaction?: string | null;
}

<<<<<<< INTEGRATION
const OBJ_LABEL: Record<string, string> = { car: "Autoturism", truck: "Camion", bus: "Autobuz", motorcycle: "Motocicletă", bicycle: "Bicicletă", person: "Pieton", autoturism: "Autoturism", camion: "Camion", autobuz: "Autobuz", motocicleta: "Motocicletă", pieton: "Pieton" };

// Quick filters are exact, type-based filters over the loaded alerts (no camera names hard-coded).
const PRESETS: { label: string; match: (a: Alert) => boolean }[] = [
  { label: "Viteză foarte mare", match: (a) => a.type === "very_high_speed" },
  { label: "Schimbări de bandă periculoase", match: (a) => a.type === "dangerous_lane_change" },
  { label: "Frânări bruște", match: (a) => a.type === "hard_braking" },
  { label: "Accidente probabile", match: (a) => a.type === "probable_crash" },
  { label: "Camioane implicate", match: (a) => a.metrics?.vehicleClass === "camion" },
=======
// q only where the keyword parser has the concept and the structured filters do not.
const PRESETS: { label: string; q?: string; filters?: ArchiveFilters }[] = [
  { label: "Viteză peste 100 km/h", q: "viteză peste 100 km/h" },
  { label: "Toate depășirile de viteză", filters: { types: ["very_high_speed"] } },
  { label: "Schimbări de bandă periculoase", filters: { types: ["dangerous_lane_change"] } },
  { label: "Frânări bruște", filters: { types: ["hard_braking"] } },
  { label: "Accidente probabile", filters: { types: ["probable_crash"] } },
  { label: "Camioane implicate", q: "camioane" },
  { label: iasiCameraName("mx-bridge-night") ?? "mx-bridge-night", filters: { camera_id: "mx-bridge-night" } },
  { label: iasiCameraName("demo-highway") ?? "demo-highway", filters: { camera_id: "demo-highway" } },
>>>>>>> GITHUB_TARGET
];

function fromAlert(a: Alert): ArchiveClip {
  return {
    id: a.id, camera_name: cameraById(a.cameraId)?.name ?? a.cameraId, createdAt: a.createdAt,
    label: ALERT_TYPE[a.type]?.label ?? a.type,
    object: a.metrics?.vehicleClass ? (OBJ_LABEL[a.metrics.vehicleClass] ?? a.metrics.vehicleClass) : undefined,
    thumbnail_url: a.keyframeUrl ?? "", clip_url: a.clip?.src, redaction: a.redaction,
  };
}

export default function ArchivePage() {
<<<<<<< INTEGRATION
  const alerts = useDataStore((st) => st.alerts);
  const location = useLocation();
  const initialSearch = (location.state as { search?: unknown } | null)?.search;
  const [query, setQuery] = useState(typeof initialSearch === "string" ? initialSearch : "");
=======
  const cameras = useDataStore((s) => s.cameras);
  const location = useLocation();
  const initialQ = (location.state as { q?: string } | null)?.q ?? "";
  // "Istoric" on a camera tile links here with ?camera=<id>: the archive opens filtered to that camera.
  const initialCamera = new URLSearchParams(location.search).get("camera") || undefined;
  const initialFilters: ArchiveFilters = initialCamera ? { ...DEFAULT_FILTERS, camera_id: initialCamera } : DEFAULT_FILTERS;
  const cameraName = (ev: ApiEvent) => cameras.find((c) => c.id === ev.camera_id)?.name ?? ev.camera_name ?? ev.camera_id;
  const [query, setQuery] = useState(initialQ);
  const [filters, setFilters] = useState<ArchiveFilters>(initialFilters);
  const [days, setDays] = useState<{ from: string; to: string }>({ from: "", to: "" });
  const [results, setResults] = useState<ApiEvent[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<ArchiveRun | null>(null);
  const [tokens, setTokens] = useState<TokenInterpretation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
>>>>>>> GITHUB_TARGET
  const [playing, setPlaying] = useState<number | null>(null);
  const [interpreted, setInterpreted] = useState<string[]>([]);
  const [searched, setSearched] = useState<ArchiveClip[] | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState("");
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);
  const [selectedObjects, setSelectedObjects] = useState<string[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedName, setSavedName] = useState("");
  const [savedError, setSavedError] = useState("");
  const [saving, setSaving] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [activeSavedSearch, setActiveSavedSearch] = useState<SavedSearch | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (USE_MOCKS) return;
    let active = true;
    void api<SavedSearch[]>("/api/saved-searches")
      .then((items) => { if (active) setSavedSearches(items); })
      .catch((e) => { if (active) setSavedError((e as Error).message || "Căutările salvate nu au putut fi încărcate."); });
    return () => { active = false; };
  }, []);

  const allClips = useMemo(() => alerts.filter((a) => a.keyframeUrl).map(fromAlert), [alerts]);

  async function runSearch(q: string, cursor?: string) {
    if (!q.trim()) return;
    const currentRequest = ++requestId.current;
    setState("loading");
    setError("");
    if (!cursor) {
      setInterpreted([]);
      setActiveSavedSearch(null);
      setNextCursor(null);
    }
    try {
      if (USE_MOCKS) {
        const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
        setSearched(allClips.filter((c) => tokens.every((t) => `${c.label} ${c.camera_name}`.toLowerCase().includes(t))));
        setInterpreted(tokens);
      } else {
        const res = await api<{ filter?: { explanation?: string }; results?: ApiHit[]; next_cursor?: string | null }>("/api/search", {
          method: "POST", body: JSON.stringify({ q, ...(cursor ? { cursor } : {}), limit: 50 }),
        });
        if (currentRequest !== requestId.current) return;
        const hits = mapApiHits(res?.results ?? []);
        setSearched((previous) => cursor ? mergePage(previous ?? [], hits) : hits);
        setNextCursor(res?.next_cursor ?? null);
        const ex = res?.filter?.explanation;
        if (!cursor) setInterpreted(ex ? ex.split(/[;,·]/).map((x) => x.trim()).filter(Boolean) : []);
      }
      if (currentRequest === requestId.current) setState("idle");
    } catch (e) {
      if (currentRequest !== requestId.current) return;
      setError((e as Error).message || "Căutarea a eșuat.");
      setState("error");
    }
<<<<<<< INTEGRATION
  }
=======
  };
  useEffect(() => {
    if (USE_MOCKS) return;
    void run(false, initialFilters, initialQ);
    listSaved().then(setSaved).catch(() => setSaved([]));
    archiveAssignees().then(setAssignees).catch(() => setAssignees(null));
  }, []);
  const toggleEvidence = (kind: NonNullable<ArchiveFilters["evidence_types"]>[number]) =>
    setFilters((f) => {
      const cur = f.evidence_types ?? [];
      const next = cur.includes(kind) ? cur.filter((x) => x !== kind) : [...cur, kind];
      return { ...f, evidence_types: next.length ? next : undefined };
    });
>>>>>>> GITHUB_TARGET

  // Router history state carries searches without putting potentially sensitive text in the URL.
  const ran = useRef<string | null>(null);
  useEffect(() => {
    const incoming = (location.state as { search?: unknown } | null)?.search;
    const q = typeof incoming === "string" ? incoming : "";
    if (q && ran.current !== location.key) {
      ran.current = location.key;
      setQuery(q);
      void runSearch(q);
    }
  }, [location.key, location.state]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    ran.current = query.trim();
    void runSearch(query.trim());
  };
  const reset = () => { requestId.current++; setSearched(null); setInterpreted([]); setQuery(""); setNextCursor(null); setActiveSavedSearch(null); ran.current = null; setState("idle"); };
  const runPreset = (p: (typeof PRESETS)[number]) => {
    requestId.current++;
    setQuery(p.label); ran.current = null;
    setSearched(alerts.filter((a) => a.keyframeUrl && p.match(a)).map(fromAlert));
    setNextCursor(null); setActiveSavedSearch(null);
    setInterpreted([p.label]);
  };

  const mapApiHits = (hits: ApiHit[]) => hits
    .filter((ev) => !HIDDEN_TYPES.has(ev.type) && !HIDDEN_IDS.has(String(ev.id)) && ev.keyframe_url)
    .map((ev) => ({
      id: String(ev.id), camera_name: cameraById(ev.camera_id)?.name ?? ev.camera_name ?? ev.camera_id,
      createdAt: ev.occurred_at ?? "",
      label: ALERT_TYPE[(RECLASSIFY[String(ev.id)]?.type ?? ev.type) as keyof typeof ALERT_TYPE]?.label ?? ev.type,
      object: ev.object_class ? (OBJ_LABEL[ev.object_class] ?? ev.object_class) : undefined,
      thumbnail_url: mediaUrl(ev.keyframe_url) ?? "", clip_url: mediaUrl(ev.clip_url) ?? undefined, redaction: ev.redaction,
    }));

  const mergePage = (current: ArchiveClip[], incoming: ArchiveClip[]) => {
    const seen = new Set(current.map((clip) => clip.id));
    return [...current, ...incoming.filter((clip) => !seen.has(clip.id))];
  };

  async function saveSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim() || !savedName.trim()) return;
    setSaving(true);
    setSavedError("");
    try {
      const item = await api<SavedSearch>("/api/saved-searches", {
        method: "POST", body: JSON.stringify({ name: savedName.trim(), query: query.trim() }),
      });
      setSavedSearches((items) => [...items.filter((x) => x.id !== item.id), item].sort((a, b) => a.name.localeCompare(b.name)));
      setSavedName("");
    } catch (e) {
      setSavedError((e as Error).message || "Căutarea nu a putut fi salvată.");
    } finally {
      setSaving(false);
    }
  }

  async function runSavedSearch(item: SavedSearch, cursor?: string) {
    const currentRequest = ++requestId.current;
    setState("loading");
    setError("");
    setSavedError("");
    if (!cursor) setNextCursor(null);
    try {
      const res = await api<{ filter?: { explanation?: string }; results?: ApiHit[]; next_cursor?: string | null }>(
        `/api/saved-searches/${item.id}/run`,
        { method: "POST", ...(cursor ? { body: JSON.stringify({ cursor, limit: 50 }) } : {}) },
      );
      if (currentRequest !== requestId.current) return;
      const hits = mapApiHits(res.results ?? []);
      setSearched((previous) => cursor ? mergePage(previous ?? [], hits) : hits);
      setNextCursor(res.next_cursor ?? null);
      if (!cursor) {
        setInterpreted([item.name, ...(res.filter?.explanation ? [res.filter.explanation] : [])]);
        setActiveSavedSearch(item);
        setQuery("");
        ran.current = null;
      }
      setState("idle");
    } catch (e) {
      if (currentRequest !== requestId.current) return;
      setError((e as Error).message || "Căutarea salvată nu a putut fi executată.");
      setState("error");
    }
  }

  async function deleteSavedSearch(item: SavedSearch) {
    if (!window.confirm(`Ștergeți căutarea salvată „${item.name}”?`)) return;
    setSavedError("");
    try {
      await api<void>(`/api/saved-searches/${item.id}`, { method: "DELETE" });
      setSavedSearches((items) => items.filter((x) => x.id !== item.id));
    } catch (e) {
      setSavedError((e as Error).message || "Căutarea nu a putut fi ștearsă.");
    }
  }

  const base = searched ?? allClips;
  const cameras = [...new Set(base.map((c) => c.camera_name))];
  const objects = [...new Set(base.map((c) => c.object).filter(Boolean) as string[])];
  const clips = base.filter((c) =>
    (!selectedCameras.length || selectedCameras.includes(c.camera_name)) &&
    (!selectedObjects.length || (c.object && selectedObjects.includes(c.object))));
  const toggle = (list: string[], set: (v: string[]) => void, v: string) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const checkGroup = (title: string, items: string[], sel: string[], set: (v: string[]) => void) => items.length > 0 && (
    <fieldset className="border-t border-border pt-3 mt-3 first:border-0 first:pt-0 first:mt-0">
      <legend className="text-sm font-medium mb-2">{title}</legend>
      <div className="flex flex-col gap-1 max-h-52">
        {items.map((it) => (
          <label key={it} className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary cursor-pointer min-h-[var(--target-min)]">
            <input type="checkbox" checked={sel.includes(it)} onChange={() => toggle(sel, set, it)} className="w-4 h-4 accent-[var(--action)]" />
            <span>{it}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );

  return (
    <div className="flex flex-col lg:flex-row min-h-full">
      <div className="flex-1 flex flex-col min-w-0 p-3 sm:p-6 gap-4">
        <div>
          <p className="eyebrow">Arhivă</p>
          <h1 className="font-display text-3xl font-bold tracking-tight">Căutare în arhivă</h1>
        </div>
        {USE_MOCKS && <div><Chip kind="demo" /></div>}

        <form onSubmit={submit} role="search" className="glass rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <Field label="Ce căutați?" hint="Ex: camioane oprite ieri între 14 și 18">
              {(a) => <TextInput {...a} type="search" className="!min-h-14 !text-lg !rounded-xl" value={query} onChange={(e) => setQuery(e.target.value)} />}
            </Field>
          </div>
          <Button type="submit" size="lg" className="min-h-14 sm:min-w-32" loading={state === "loading"}><Search size={16} aria-hidden="true" /> Caută</Button>
        </form>

        {!USE_MOCKS && <section className="card p-4 flex flex-col gap-3" aria-labelledby="saved-searches-title">
          <div>
            <h2 id="saved-searches-title" className="font-display text-lg font-semibold">Căutări salvate</h2>
            <p className="text-xs text-text-secondary">Se păstrează filtrele interpretate; textul căutării nu este stocat.</p>
          </div>
          <form onSubmit={saveSearch} className="flex flex-col sm:flex-row gap-2 sm:items-end">
            <div className="flex-1"><Field label="Numele căutării">
              {(a) => <TextInput {...a} value={savedName} onChange={(e) => setSavedName(e.target.value)} maxLength={80} required />}
            </Field></div>
            <Button type="submit" variant="secondary" loading={saving} disabled={!query.trim()}><Bookmark size={15} aria-hidden="true" /> Salvează filtrele curente</Button>
          </form>
          {savedError && <p className="text-sm text-critical" role="alert">{savedError}</p>}
          {savedSearches.length ? <ul className="flex flex-wrap gap-2">{savedSearches.map((item) => <li key={item.id} className="flex items-center gap-1 rounded-lg border border-border bg-elevation px-2">
            <button type="button" onClick={() => void runSavedSearch(item)} disabled={state === "loading"} className="min-h-[var(--target-min)] px-1 text-sm hover:text-action disabled:opacity-50">{item.name}</button>
            <button type="button" onClick={() => void deleteSavedSearch(item)} aria-label={`Șterge căutarea: ${item.name}`} className="min-h-[var(--target-min)] min-w-[var(--target-min)] flex items-center justify-center text-text-secondary hover:text-critical"><Trash2 size={14} aria-hidden="true" /></button>
          </li>)}</ul> : <p className="text-sm text-text-secondary">Nu există căutări salvate pentru acest cont.</p>}
        </section>}

        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtre rapide">
          <span className="text-sm text-text-secondary">Filtre rapide:</span>
          {PRESETS.map((p) => (
            <button key={p.label} type="button" onClick={() => runPreset(p)}
              className="press px-3.5 min-h-[var(--target-min)] rounded-full bg-elevation border border-border text-sm hover:border-action hover:text-action cursor-pointer">
              {p.label} <span className="text-text-secondary">({alerts.filter((a) => a.keyframeUrl && p.match(a)).length})</span>
            </button>
          ))}
          {searched && <Button variant="ghost" size="sm" onClick={reset}>Resetează</Button>}
        </div>

        {interpreted.length > 0 && (
          <div className="flex flex-wrap items-center gap-2" aria-label="Interpretarea căutării">
            <span className="text-sm text-text-secondary">Interpretat:</span>
            <span className="stagger inline-flex flex-wrap gap-2">{interpreted.map((c) => <span key={c} className="px-3 py-1 rounded-full bg-action/10 border border-action/40 text-sm text-text-primary">{c}</span>)}</span>
          </div>
        )}

        <p className="text-sm text-text-secondary" role="status">
          <span className="text-text-primary font-medium">{clips.length} {clips.length === 1 ? "rezultat" : "rezultate"}</span>
          {searched ? " · rezultatele căutării" : " · toate alertele cu dovezi"}
        </p>

        {state === "error" ? (
          <ErrorState message={error} onRetry={() => activeSavedSearch
            ? void runSavedSearch(activeSavedSearch)
            : void runSearch(query)} />
        ) : state === "loading" ? (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">{[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <Skeleton key={i} className="aspect-[16/10]" />)}</div>
        ) : clips.length === 0 ? (
          <div className="card"><EmptyState art={<FolderArt />} title="Niciun rezultat" hint={searched ? "Încercați alt text sau resetați filtrele." : "Nu există încă alerte cu dovezi."} /></div>
        ) : (
          <ul key={String(searched?.length ?? "all") + location.key} className="stagger grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {clips.map((clip, idx) => (
              <li key={clip.id} className="group card flex flex-col overflow-hidden hover:border-action/50 hover:-translate-y-0.5 hover:shadow-[var(--shadow-2)] transition-[transform,box-shadow,border-color]">
                <div className="relative aspect-[16/10] bg-black">
                  {clip.thumbnail_url && <img src={clip.thumbnail_url} alt="" loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-500" />}
                  <div className="absolute top-2 left-2">{USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={clip.redaction} />}</div>
                  <button type="button" onClick={() => setPlaying(idx)} aria-label={`Redă clipul: ${clip.label}, ${clip.camera_name}`}
                    className="press btn-primary absolute bottom-2 right-2 w-11 h-11 rounded-full bg-accent text-on-accent flex items-center justify-center cursor-pointer">
                    <Play size={16} aria-hidden="true" />
                  </button>
                </div>
<<<<<<< INTEGRATION
                <div className="p-3 flex flex-col gap-0.5">
                  <Link to={`/app/alerte/${clip.id}`} className="font-display text-base font-semibold truncate hover:text-action">{clip.label}</Link>
                  <span className="text-sm text-text-secondary truncate">{clip.camera_name}</span>
                  <span className="text-xs text-text-secondary tabular-nums">{clip.createdAt ? fmtDateTime(clip.createdAt) : "—"}{clip.object ? ` · ${clip.object}` : ""}</span>
=======
                <div className="p-2.5 flex flex-col gap-1 border-t border-border/80">
                  <div className="text-xs font-semibold text-text-primary truncate">#{ev.id} · {cameraName(ev)}</div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-text-secondary">
                    <span>{fmtWhen(ev.occurred_at)}</span>
                    <span>{STATUS_LABEL[ev.status] ?? ev.status}</span>
                  </div>
                  <Link to={`/app/alerte/${ev.id}`} className="mt-1 inline-flex items-center gap-1 text-xs text-accent hover:underline" data-testid="open-case">
                    <FolderOpen className="w-3.5 h-3.5" /> Deschide dosarul
                  </Link>
>>>>>>> GITHUB_TARGET
                </div>
              </li>
            ))}
          </ul>
        )}
        {nextCursor && !USE_MOCKS && state !== "loading" && (
          <div className="flex justify-center">
            <Button variant="secondary" onClick={() => activeSavedSearch
              ? void runSavedSearch(activeSavedSearch, nextCursor)
              : void runSearch(query, nextCursor)}>
              Încarcă rezultatele următoare
            </Button>
          </div>
        )}
      </div>

      <aside aria-label="Filtrare" className="lg:w-72 border-t lg:border-t-0 lg:border-l border-border-subtle bg-panel/70 backdrop-blur p-4 lg:overflow-y-auto">
        <details open className="lg:[&>summary]:pointer-events-none" >
          <summary className="font-display text-lg font-semibold cursor-pointer mb-3 list-none">Filtrare</summary>
          {checkGroup("Camere", cameras, selectedCameras, setSelectedCameras)}
          {checkGroup("Obiect", objects, selectedObjects, setSelectedObjects)}
          {!cameras.length && !objects.length && <p className="text-sm text-text-secondary">Nu există filtre pentru rezultatele curente.</p>}
        </details>
      </aside>

      {playing !== null && (
        <ClipModal
<<<<<<< INTEGRATION
          clips={clips.map((c) => ({
            id: c.id, title: `${c.label} · ${c.camera_name}`, subtitle: c.createdAt ? fmtDateTime(c.createdAt) : undefined,
            src: c.clip_url, poster: c.thumbnail_url, at: c.createdAt || new Date().toISOString(),
            chip: USE_MOCKS ? <Chip kind="synthetic" /> : <RedactionChip redaction={c.redaction} />,
          }))}
=======
          clips={results.map((c) => ({ id: String(c.id), title: `${shownType(c)} · ${cameraName(c)}`, subtitle: fmtWhen(c.occurred_at), src: mediaUrl(c.clip_url), poster: mediaUrl(c.keyframe_url), at: c.occurred_at }))}
>>>>>>> GITHUB_TARGET
          start={playing}
          onClose={() => setPlaying(null)}
        />
      )}
    </div>
  );
}
