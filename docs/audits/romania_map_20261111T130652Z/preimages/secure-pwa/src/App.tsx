import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LockScreen, ReauthDialog } from "./components/Overlays";
import { AlertDetailPage, AlertsPage } from "./routes/AlertsPage";
import { AdminPage } from "./routes/AdminPage";
import { ApprovalsPage } from "./routes/ApprovalsPage";
import { AuditPage } from "./routes/AuditPage";
import { InvitePage } from "./routes/InvitePage";
import { LoginPage } from "./routes/LoginPage";
import { ResetPage } from "./routes/ResetPage";
import { SessionsPage } from "./routes/SessionsPage";
import { ErrorBoundary, ROLE_LABEL } from "./ui";

type Theme = "system" | "light" | "dark";
const THEME_LABEL: Record<Theme, string> = {
  system: "sistem",
  light: "luminoasă",
  dark: "întunecată",
};

/* The theme preference (light/dark/system) is the only thing kept in localStorage: it is not auth
   state, carries no user data, and logout wipes it with the rest of the client state. */
function readTheme(): Theme {
  try {
    // eslint-disable-next-line no-restricted-properties -- theme preference only
    const v = localStorage.getItem("rs-theme");
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  function next() {
    const order: Theme[] = ["system", "light", "dark"];
    const t = order[(order.indexOf(theme) + 1) % order.length];
    const el = document.documentElement;
    if (t === "system") el.removeAttribute("data-theme");
    else el.setAttribute("data-theme", t);
    try {
      /* eslint-disable no-restricted-properties -- theme preference only */
      if (t === "system") localStorage.removeItem("rs-theme");
      else localStorage.setItem("rs-theme", t);
      /* eslint-enable no-restricted-properties */
    } catch {
      /* storage blocked: the choice lasts for this session only */
    }
    setTheme(t);
  }
  return (
    <button
      type="button"
      className="secondary"
      onClick={next}
      aria-label={`Temă: ${THEME_LABEL[theme]}. Apasă pentru a schimba`}
    >
      Temă<span className="long">{`: ${THEME_LABEL[theme]}`}</span>
    </button>
  );
}

/* Decorative calm mode: no glow, blur or entrance motion. Preference only (no user data). */
function CalmToggle() {
  const [on, setOn] = useState(() => {
    try {
      // eslint-disable-next-line no-restricted-properties -- display preference only
      return localStorage.getItem("rs-calm") === "on";
    } catch {
      return false;
    }
  });
  return (
    <button
      type="button"
      className="secondary"
      aria-pressed={on}
      onClick={() => {
        const next = !on;
        const el = document.documentElement;
        if (next) el.setAttribute("data-calm", "on");
        else el.removeAttribute("data-calm");
        try {
          /* eslint-disable no-restricted-properties -- display preference only */
          if (next) localStorage.setItem("rs-calm", "on");
          else localStorage.removeItem("rs-calm");
          /* eslint-enable no-restricted-properties */
        } catch {
          /* storage blocked: the choice lasts for this session only */
        }
        setOn(next);
      }}
    >
      <span className="long">Mod calm</span>
      <span className="short">Calm</span>
    </button>
  );
}

const ICONS: Record<string, string[]> = {
  alerts: ["M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.3 21a1.94 1.94 0 0 0 3.4 0"],
  approvals: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "m9 12 2 2 4-4"],
  audit: [
    "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z",
    "M14 2v4a2 2 0 0 0 2 2h4",
    "M16 13H8",
    "M16 17H8",
    "M10 9H8",
  ],
  sessions: [
    "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z",
    "M12 18h.01",
  ],
};
function NavIcon({ name }: { name: keyof typeof ICONS }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

function BrandMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="bm" x1="6" y1="4" x2="42" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--action)" />
          <stop offset="1" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <rect
        x="3"
        y="3"
        width="42"
        height="42"
        rx="13"
        fill="var(--bg-elevation)"
        stroke="url(#bm)"
        strokeWidth="2"
      />
      <path
        d="M12 36 22 24l6 3 8-13"
        stroke="url(#bm)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="36" r="2.6" fill="var(--text-muted)" />
      <circle cx="22" cy="24" r="2.6" fill="var(--text-primary)" />
      <circle cx="36" cy="14" r="4.2" fill="url(#bm)" />
    </svg>
  );
}

function Protected({ children, permission }: { children: ReactNode; permission?: string }) {
  const { status, can } = useAuth();
  if (status === "loading")
    return (
      <p className="muted" role="status">
        Se încarcă…
      </p>
    );
  if (status !== "authenticated") return <Navigate to="/login" replace />;
  if (permission && !can(permission))
    return (
      <div className="stack">
        <h1>Acces restricționat</h1>
        <p className="error">Rolul dumneavoastră nu are acces la această pagină.</p>
      </div>
    );
  return <>{children}</>;
}

function Shell() {
  const { status, me, can, logout, locked, reauthOpen } = useAuth();
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const home = can("alerts:read") ? "/alerts" : can("audit:read") ? "/audit" : "/sessions";

  // New route: move focus to the content so keyboard and screen-reader users start there.
  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <>
      <a href="#main" className="skip-link">
        Sari la conținut
      </a>
      {status === "authenticated" && me && (
        <header className="topbar">
          <strong className="brand">
            <BrandMark />
            <span>
              Road<b>Sentinel</b>
            </span>
          </strong>
          <nav aria-label="Navigare principală">
            {can("alerts:read") && (
              <NavLink to="/alerts">
                <NavIcon name="alerts" />
                Alerte
              </NavLink>
            )}
            {(can("approvals:request") || can("approvals:decide")) && (
              <NavLink to="/approvals">
                <NavIcon name="approvals" />
                Aprobări
              </NavLink>
            )}
            {can("audit:read") && (
              <NavLink to="/audit">
                <NavIcon name="audit" />
                Audit
              </NavLink>
            )}
            <NavLink to="/sessions">
              <NavIcon name="sessions" />
              Sesiuni
            </NavLink>
            <NavLink to="/admin">
              <NavIcon name="sessions" />
              Cont
            </NavLink>
          </nav>
          <span className="who">
            <span>{me.display_name}</span>
            <span className="muted">
              {ROLE_LABEL[me.role] ?? me.role} · {me.tenant_name}
            </span>
          </span>
          <span className="toggles">
            <CalmToggle />
            <ThemeToggle />
          </span>
          <button className="secondary" onClick={() => void logout()}>
            Deconectare
          </button>
        </header>
      )}
      <main id="main" ref={mainRef} tabIndex={-1} className="content">
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/invite" element={<InvitePage />} />
            <Route path="/reset" element={<ResetPage />} />
            <Route
              path="/admin"
              element={
                <Protected>
                  <AdminPage />
                </Protected>
              }
            />
            <Route
              path="/alerts"
              element={
                <Protected permission="alerts:read">
                  <AlertsPage />
                </Protected>
              }
            />
            <Route
              path="/alerts/:id"
              element={
                <Protected permission="alerts:read">
                  <AlertDetailPage />
                </Protected>
              }
            />
            <Route
              path="/approvals"
              element={
                <Protected>
                  <ApprovalsPage />
                </Protected>
              }
            />
            <Route
              path="/audit"
              element={
                <Protected permission="audit:read">
                  <AuditPage />
                </Protected>
              }
            />
            <Route
              path="/sessions"
              element={
                <Protected>
                  <SessionsPage />
                </Protected>
              }
            />
            <Route
              path="*"
              element={<Navigate to={status === "authenticated" ? home : "/login"} replace />}
            />
          </Routes>
        </ErrorBoundary>
      </main>
      {status === "authenticated" && locked && <LockScreen />}
      {status === "authenticated" && reauthOpen && !locked && <ReauthDialog />}
    </>
  );
}

export function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
