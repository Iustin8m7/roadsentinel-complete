import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { format } from "date-fns";
import { Bookmark, FolderOpen, Loader2, Play, Save, Search, SlidersHorizontal, Trash2, X } from "lucide-react";
import { mediaUrl, USE_MOCKS } from "@/lib/api";
import { ALERT_TYPE, STATUS_LABEL } from "@/lib/constants";
import { archiveAssignees, archiveRequest, deleteSaved, errorMessage, listSaved, saveSearch, searchArchive, type ArchiveFilters, type ArchiveRun, type FilterChip, type Person, type SavedSearch, type TokenInterpretation } from "@/lib/cases";
import { RECLASSIFY } from "@/lib/demo";
import type { ApiEvent } from "@/lib/adapters";
import { useDataStore } from "@/store/data";
import { ClipModal } from "@/components/ClipModal";

const STATUSES = ["new", "confirmed", "rejected"] as const;
const EVIDENCE_TYPES: [NonNullable<ArchiveFilters["evidence_types"]>[number], string][] = [["keyframe", "Cadru cheie"], ["clip", "Clip video"], ["camera_video", "Înregistrarea camerei"]];
const PRIORITIES: [string, string][] = [["critical", "Critic"], ["high", "Ridicat"], ["medium", "Mediu"], ["info", "Informativ"]];
const fmtWhen = (iso: string) => new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
// <input type="date"> is local midnight; the API wants an explicit offset (UTC ISO).
const dayStart = (d: string) => new Date(`${d}T00:00:00`).toISOString();
const nextDay = (d: string) => new Date(new Date(`${d}T00:00:00`).getTime() + 864e5).toISOString();
const DEFAULT_FILTERS: ArchiveFilters = { has_evidence: true };
// Inverse of the two above, for a saved filter: back to the days shown in the date inputs.
const savedDays = (f: ArchiveFilters) => ({
  from: f.date_from ? format(new Date(f.date_from), "yyyy-MM-dd") : "",
  to: f.date_to ? format(new Date(new Date(f.date_to).getTime() - 864e5), "yyyy-MM-dd") : "",
});
const typeLabel = (type: string) => ALERT_TYPE[type as keyof typeof ALERT_TYPE]?.label ?? type;
// Display-only correction, same as the alert queue: the row keeps its stored type.
const shownType = (ev: ApiEvent) => typeLabel(RECLASSIFY[String(ev.id)]?.type ?? ev.type);

// q only where the keyword parser has the concept and the structured filters do not.
const PRESETS: { label: string; q?: string; filters?: ArchiveFilters }[] = [
  { label: "Viteză peste 100 km/h", q: "viteză peste 100 km/h" },
  { label: "Toate depășirile de viteză", filters: { types: ["very_high_speed"] } },
  { label: "Schimbări de bandă periculoase", filters: { types: ["dangerous_lane_change"] } },
  { label: "Frânări bruște", filters: { types: ["hard_braking"] } },
  { label: "Accidente probabile", filters: { types: ["probable_crash"] } },
  { label: "Camioane implicate", q: "camioane" },
  { label: "Pasaj Mihai Eminescu, noaptea", filters: { camera_id: "mx-bridge-night" } },
  { label: "Centura Iași", filters: { camera_id: "demo-highway" } },
];

function Chip({ t }: { t: TokenInterpretation }) {
  const cls = t.status === "recognized" ? "border-accent/50 text-accent" : t.status === "unsupported" ? "border-amber-500/50 text-amber-400" : "border-border text-text-secondary";
  const label = t.status === "recognized" ? t.meanings.join(" + ") : t.status === "unsupported" ? "nerecunoscut, ignorat" : "cuvânt de legătură";
  return (
    <span className={`px-2 py-0.5 rounded-md border text-xs ${cls}`} data-testid={`token-${t.status}`} title={t.ambiguous ? "Cuvânt ambiguu: aplică mai multe filtre" : undefined}>
      <b>{t.token}</b> → {label}{t.ambiguous ? " (ambiguu)" : ""}
    </span>
  );
}

export default function ArchivePage() {
  const cameras = useDataStore((s) => s.cameras);
  const initialQ = (useLocation().state as { q?: string } | null)?.q ?? "";
  const [query, setQuery] = useState(initialQ);
  const [filters, setFilters] = useState<ArchiveFilters>(DEFAULT_FILTERS);
  const [days, setDays] = useState<{ from: string; to: string }>({ from: "", to: "" });
  const [results, setResults] = useState<ApiEvent[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<ArchiveRun | null>(null);
  const [tokens, setTokens] = useState<TokenInterpretation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState<number | null>(null);
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [saveName, setSaveName] = useState("");
  const [chips, setChips] = useState<FilterChip[]>([]);
  // null = this role may not filter by assignee (the server refuses it): the control is hidden.
  const [assignees, setAssignees] = useState<Person[] | null>(null);

  const effective = (): ArchiveFilters => ({
    ...filters,
    date_from: days.from ? dayStart(days.from) : undefined,
    date_to: days.to ? nextDay(days.to) : undefined,
  });

  const run = async (append = false, f = effective(), q = query) => {
    if (USE_MOCKS) return;
    setLoading(true);
    setError(null);
    try {
      const request = archiveRequest(append, { q, filters: f }, lastRun, cursor);
      const page = await searchArchive(request.run.q, request.run.filters, request.cursor);
      setLastRun(request.run);
      setResults((prev) => (append ? [...prev, ...page.results] : page.results));
      setTotal(page.total);
      setCursor(page.next_cursor);
      setTokens(page.interpretation);
      setChips(page.applied_filters ?? []);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (USE_MOCKS) return;
    void run(false, DEFAULT_FILTERS, initialQ);
    listSaved().then(setSaved).catch(() => setSaved([]));
    archiveAssignees().then(setAssignees).catch(() => setAssignees(null));
  }, []);
  const toggleEvidence = (kind: NonNullable<ArchiveFilters["evidence_types"]>[number]) =>
    setFilters((f) => {
      const cur = f.evidence_types ?? [];
      const next = cur.includes(kind) ? cur.filter((x) => x !== kind) : [...cur, kind];
      return { ...f, evidence_types: next.length ? next : undefined };
    });

  const toggle = (key: "statuses" | "priorities", value: string) =>
    setFilters((f) => {
      const cur = f[key] ?? [];
      return { ...f, [key]: cur.includes(value) ? cur.filter((x) => x !== value) : [...cur, value] };
    });

  const applySaved = (s: SavedSearch) => {
    setFilters(s.filters);
    setDays(savedDays(s.filters));
    setQuery("");
    void run(false, s.filters, "");
  };
  const runPreset = (p: (typeof PRESETS)[number]) => {
    const f = { ...DEFAULT_FILTERS, ...p.filters };
    setFilters(f);
    setDays({ from: "", to: "" });
    setQuery(p.q ?? "");
    void run(false, f, p.q ?? "");
  };
  const save = async () => {
    try {
      const row = await saveSearch(saveName.trim(), effective());
      setSaved((xs) => [row, ...xs]);
      setSaveName("");
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  if (USE_MOCKS) {
    return <div className="p-6 text-sm text-amber-400">Mod demo (VITE_USE_MOCKS): arhiva cu filtre și paginare funcționează doar cu serverul real.</div>;
  }

  const label = "flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary cursor-pointer select-none";
  return (
    <div className="flex h-full overflow-hidden bg-deep-void">
      <div className="flex-1 flex flex-col h-full min-w-0 p-6 overflow-hidden">
        <form onSubmit={(e) => { e.preventDefault(); void run(); }} className="relative w-full mb-3" role="search">
          <div className="flex items-center rounded-md bg-panel border-2 border-accent/60 focus-within:border-accent transition-all px-4 py-2">
            <Search className="w-5 h-5 text-text-secondary mr-3" aria-hidden />
            <input
              type="text"
              value={query}
              maxLength={500}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ex: camioane oprite pe banda de urgență ieri seara"
              aria-label="Căutare în arhivă după cuvinte cheie"
              className="flex-1 bg-transparent text-text-primary text-base placeholder:text-text-secondary focus:outline-none font-sans"
            />
            <button type="submit" disabled={loading} className="ml-3 px-5 py-2 bg-accent hover:bg-accent/90 text-white font-medium text-sm rounded-md">
              {loading ? "Se caută…" : "Caută"}
            </button>
          </div>
        </form>
        <p className="text-[11px] text-text-secondary mb-2">
          Căutare după cuvinte cheie (română/engleză), nu înțelegere semantică. Textul căutării nu se salvează și nu apare în adresa paginii.
        </p>
        <div className="flex flex-wrap items-center gap-2 mb-3" aria-label="Căutări rapide">
          <span className="text-xs text-text-secondary">Căutări rapide:</span>
          {PRESETS.map((p) => (
            <button key={p.label} type="button" disabled={loading} onClick={() => runPreset(p)} data-testid="archive-preset"
              className="px-2.5 py-1 rounded-md bg-elevation border border-border text-xs text-text-primary hover:border-accent hover:text-accent transition-colors disabled:opacity-50">
              {p.label}
            </button>
          ))}
        </div>
        {tokens.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mb-3" aria-label="Interpretarea căutării">
            <span className="text-xs text-text-secondary">Interpretare:</span>
            {tokens.map((t, i) => <Chip key={`${t.token}-${i}`} t={t} />)}
          </div>
        )}
        {chips.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mb-3" aria-label="Filtre aplicate de server">
            <span className="text-xs text-text-secondary">Filtre aplicate:</span>
            {chips.map((c) => <span key={c.key} className="px-2 py-0.5 rounded-md border border-accent/50 text-accent text-xs" data-testid="filter-chip">{c.label}</span>)}
          </div>
        )}
        <div className="text-xs text-text-secondary mb-3" aria-live="polite">
          {total !== null && <span className="text-text-primary font-semibold" data-testid="archive-total">{total} rezultate</span>}
          {total !== null && ` · afișate ${results.length} · ordonate după momentul detecției, cele mai noi primele`}
        </div>
        {error && <p role="alert" className="text-xs text-rose-400 mb-2">{error}</p>}

        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
          {!loading && total === 0 && <p className="text-sm text-text-secondary">Niciun caz nu corespunde filtrelor.</p>}
          <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5 pb-4">
            {results.map((ev, idx) => (
              <li key={ev.id} className="group relative flex flex-col rounded-md bg-panel border border-border hover:border-accent overflow-hidden" data-testid="archive-card">
                <div className="relative aspect-[16/10] bg-black/90 overflow-hidden">
                  {ev.keyframe_url ? (
                    <img src={mediaUrl(ev.keyframe_url)} alt={`Cadru cheie caz #${ev.id}`} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} />
                  ) : <div className="w-full h-full flex items-center justify-center text-xs text-text-secondary">Fără cadru cheie</div>}
                  {ev.clip_url && (
                    <button type="button" onClick={() => setPlaying(idx)} aria-label={`Redă clipul cazului #${ev.id}`} className="absolute inset-0 w-full flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 bg-deep-void/40 transition-opacity">
                      <span className="w-11 h-11 rounded-full bg-accent/80 flex items-center justify-center"><Play className="w-5 h-5 fill-white ml-0.5" /></span>
                    </button>
                  )}
                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-[10px] font-mono text-text-primary">{shownType(ev)}</span>
                </div>
                <div className="p-2.5 flex flex-col gap-1 border-t border-border/80">
                  <div className="text-xs font-semibold text-text-primary truncate">#{ev.id} · {ev.camera_name ?? ev.camera_id}</div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-text-secondary">
                    <span>{fmtWhen(ev.occurred_at)}</span>
                    <span>{STATUS_LABEL[ev.status] ?? ev.status}</span>
                  </div>
                  <Link to={`/app/alerte/${ev.id}`} className="mt-1 inline-flex items-center gap-1 text-xs text-accent hover:underline" data-testid="open-case">
                    <FolderOpen className="w-3.5 h-3.5" /> Deschide dosarul
                  </Link>
                </div>
              </li>
            ))}
          </ul>
          {cursor && (
            <button type="button" disabled={loading} onClick={() => void run(true)} className="mx-auto mb-6 flex items-center gap-2 px-4 py-2 rounded-md border border-border text-sm text-text-primary hover:border-accent">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />} Încarcă mai multe
            </button>
          )}
        </div>
      </div>

      <aside className="w-72 border-l border-border bg-panel flex flex-col h-full p-5 overflow-y-auto gap-5" aria-label="Filtre arhivă">
        <h2 className="font-heading text-lg font-bold uppercase tracking-wider text-text-primary flex items-center justify-between">
          <span>Filtre</span><SlidersHorizontal className="w-4 h-4 text-text-secondary" />
        </h2>
        <label className="text-xs text-text-primary font-bold flex flex-col gap-1.5">Cameră
          <select value={filters.camera_id ?? ""} onChange={(e) => setFilters((f) => ({ ...f, camera_id: e.target.value || undefined }))} className="bg-deep-void border border-border rounded-md p-1.5 font-normal">
            <option value="">Toate camerele</option>
            {cameras.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        {!!filters.types?.length && (
          <div className="text-xs text-text-primary flex items-center justify-between gap-2" data-testid="active-types">
            <span><b>Tip:</b> {filters.types.map(typeLabel).join(", ")}</span>
            <button type="button" aria-label="Elimină filtrul de tip" onClick={() => setFilters((f) => ({ ...f, types: undefined }))} className="text-text-secondary hover:text-rose-400"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}
        <fieldset className="space-y-1.5"><legend className="text-xs font-bold text-text-primary mb-1">Stare</legend>
          {STATUSES.map((s) => <label key={s} className={label}><input type="checkbox" checked={filters.statuses?.includes(s) ?? false} onChange={() => toggle("statuses", s)} />{STATUS_LABEL[s]}</label>)}
        </fieldset>
        <fieldset className="space-y-1.5"><legend className="text-xs font-bold text-text-primary mb-1">Prioritate</legend>
          {PRIORITIES.map(([k, l]) => <label key={k} className={label}><input type="checkbox" checked={filters.priorities?.includes(k) ?? false} onChange={() => toggle("priorities", k)} />{l}</label>)}
        </fieldset>
        <fieldset className="space-y-1.5"><legend className="text-xs font-bold text-text-primary mb-1">Interval</legend>
          <label className="text-xs text-text-secondary flex items-center justify-between gap-2">De la<input type="date" value={days.from} onChange={(e) => setDays((d) => ({ ...d, from: e.target.value }))} className="bg-deep-void border border-border rounded p-1" /></label>
          <label className="text-xs text-text-secondary flex items-center justify-between gap-2">Până la<input type="date" value={days.to} onChange={(e) => setDays((d) => ({ ...d, to: e.target.value }))} className="bg-deep-void border border-border rounded p-1" /></label>
        </fieldset>
        {assignees && (
          <label className="text-xs text-text-primary font-bold flex flex-col gap-1.5">Responsabil (patrulă asignată)
            <select value={filters.assigned_to ?? ""} onChange={(e) => setFilters((f) => ({ ...f, assigned_to: e.target.value || undefined }))} className="bg-deep-void border border-border rounded-md p-1.5 font-normal" data-testid="filter-assignee">
              <option value="">Oricare</option>
              <option value="unassigned">Neasignate</option>
              {assignees.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        )}
        <fieldset className="space-y-1.5"><legend className="text-xs font-bold text-text-primary mb-1">Tip de probă stocată</legend>
          {EVIDENCE_TYPES.map(([k, l]) => <label key={k} className={label}><input type="checkbox" checked={filters.evidence_types?.includes(k) ?? false} onChange={() => toggleEvidence(k)} data-testid={`filter-evidence-${k}`} />{l}</label>)}
        </fieldset>
        <label className={label}><input type="checkbox" checked={filters.has_evidence === true} onChange={(e) => setFilters((f) => ({ ...f, has_evidence: e.target.checked ? true : undefined }))} />Doar cazuri cu probe stocate</label>
        <div className="flex gap-2">
          <button type="button" onClick={() => void run()} className="flex-1 px-3 py-1.5 rounded-md bg-accent text-white text-xs font-semibold">Aplică</button>
          <button type="button" onClick={() => { setFilters(DEFAULT_FILTERS); setDays({ from: "", to: "" }); setQuery(""); void run(false, DEFAULT_FILTERS, ""); }} className="px-3 py-1.5 rounded-md border border-border text-xs text-text-secondary"><X className="w-3.5 h-3.5 inline" /> Resetează</button>
        </div>

        <section className="border-t border-border/60 pt-4 space-y-2" aria-label="Filtre salvate">
          <h3 className="text-xs font-bold text-text-primary flex items-center gap-1.5"><Bookmark className="w-3.5 h-3.5" /> Filtre salvate</h3>
          <p className="text-[10px] text-text-secondary">Se salvează doar filtrele structurate, niciodată textul căutării.</p>
          <form onSubmit={(e) => { e.preventDefault(); if (saveName.trim()) void save(); }} className="flex gap-1.5">
            <input value={saveName} maxLength={80} onChange={(e) => setSaveName(e.target.value)} placeholder="Nume filtru" aria-label="Nume filtru salvat" className="flex-1 min-w-0 bg-deep-void border border-border rounded p-1 text-xs" />
            <button type="submit" disabled={!saveName.trim()} aria-label="Salvează filtrele curente" className="px-2 rounded border border-border text-text-secondary hover:text-accent disabled:opacity-40"><Save className="w-3.5 h-3.5" /></button>
          </form>
          <ul className="space-y-1">
            {saved.map((s) => (
              <li key={s.id} className="flex items-center gap-1.5 text-xs">
                <button type="button" onClick={() => applySaved(s)} className="flex-1 text-left truncate text-text-primary hover:text-accent">{s.name}</button>
                <button type="button" aria-label={`Șterge filtrul ${s.name}`} onClick={() => void deleteSaved(s.id).then(() => setSaved((xs) => xs.filter((x) => x.id !== s.id))).catch((e) => setError(errorMessage(e)))} className="text-text-secondary hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
              </li>
            ))}
          </ul>
        </section>
      </aside>
      {playing !== null && (
        <ClipModal
          clips={results.map((c) => ({ id: String(c.id), title: `${shownType(c)} · ${c.camera_name ?? c.camera_id}`, subtitle: fmtWhen(c.occurred_at), src: mediaUrl(c.clip_url), poster: mediaUrl(c.keyframe_url), at: c.occurred_at }))}
          start={playing}
          onClose={() => setPlaying(null)}
        />
      )}
    </div>
  );
}
