import { Link, useRouteError } from "react-router";
import { Home, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { SignalLostArt, FolderArt } from "@/components/Illustrations";

function Shell({ tone, code, title, h, children, art }: { tone: "critical" | "neutral"; code: string; title: string; h: "h1" | "h2"; children: ReactNode; art: ReactNode }) {
  const H = h;
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className={`card rise p-8 text-center max-w-md w-full flex flex-col items-center gap-2 ${tone === "critical" ? "!border-critical/40" : ""}`}>
        {art}
        <div className={`eyebrow mt-2 ${tone === "critical" ? "!text-critical" : ""}`}>{code}</div>
        <H className="font-display text-2xl font-bold text-text-primary">{title}</H>
        {children}
      </div>
    </div>
  );
}

const homeLink = (
  <Link to="/app" className="btn-primary press mt-4 inline-flex items-center gap-2 px-5 min-h-[var(--target-min)] bg-accent text-on-accent font-semibold text-sm rounded-lg">
    <Home size={16} aria-hidden="true" />
    <span>Revenire la panou</span>
  </Link>
);

export function ForbiddenPage() {
  return (
    <Shell tone="critical" code="Eroare 403" title="Acces restricționat" h="h2" art={<SignalLostArt />}>
      <p className="text-sm text-text-secondary">Rolul dumneavoastră curent nu deține permisiunile necesare pentru a accesa această secțiune.</p>
      {homeLink}
    </Shell>
  );
}

export function NotFoundPage() {
  return (
    <Shell tone="neutral" code="Eroare 404" title="Pagina nu a fost găsită" h="h1" art={<FolderArt />}>
      <p className="text-sm text-text-secondary">Resursa sau secțiunea solicitată nu există în RoadSentinel.</p>
      {homeLink}
    </Shell>
  );
}

export function RouteErrorPage() {
  const error = useRouteError();
  return (
    <Shell tone="critical" code="Eroare de sistem" title="A apărut o problemă" h="h1" art={<SignalLostArt />}>
      <p className="text-sm text-text-secondary font-mono break-all">
        {error instanceof Error ? error.message : "Eroare neașteptată în interfață."}
      </p>
      <button
        type="button"
        onClick={() => { window.location.href = "/app"; }}
        className="btn-primary press mt-4 inline-flex items-center gap-2 px-5 min-h-[var(--target-min)] bg-accent text-on-accent font-semibold text-sm rounded-lg cursor-pointer"
      >
        <RefreshCw size={16} aria-hidden="true" />
        <span>Reîncarcă sistemul</span>
      </button>
    </Shell>
  );
}
