<<<<<<< INTEGRATION
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import {
  LayoutDashboard, Video, Archive, BarChart2, Settings, Search, LogOut, Sliders, Car, FileText, X, ArrowRight, Menu, Command as CommandIcon, Film,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { useDataStore } from '@/store/data'
import { useConnection } from '@/store/connection'
=======
import { PRELOAD_FIRST, PRELOAD_MAX_WAIT_MS, preloadClips, preloadReady } from '@/lib/demo'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import {
  LayoutDashboard,
  Video,
  Archive,
  BarChart2,
  Settings,
  Search,
  LogOut,
  Sliders,
  Car,
  FileText,
  X,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { cameraById, useDataStore } from '@/store/data'
import { ALERT_TYPE, ROLE_LABEL } from '@/lib/constants'
>>>>>>> GITHUB_TARGET
import { can, type Permission } from '@/lib/permissions'
import { USE_MOCKS } from '@/lib/api'
import { useLiveFeed, useQueue } from '@/hooks'
import type { Alert } from '@/types'
import { Logo } from '@/assets/brand/Logo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { CalmToggle } from '@/components/CalmToggle'
import { CommandPalette, type Command } from '@/components/CommandPalette'
import { Banner, Button } from '@/components/ui'
import { ALERT_TYPE, ROLE_LABEL } from '@/lib/constants'

interface NavItem { to: string; label: string; icon: LucideIcon; permission: Permission; exact?: boolean; mockOnly?: boolean }

export const NAV: NavItem[] = [
  { to: '/app', label: 'Alerte', icon: LayoutDashboard, permission: 'dashboard.view', exact: true },
  { to: '/app/camere', label: 'Camere', icon: Video, permission: 'cameras.view' },
  { to: '/app/analiza-video', label: 'Analiză video', icon: Film, permission: 'video-analysis.view' },
  { to: '/app/arhiva', label: 'Căutare', icon: Archive, permission: 'archive.search' },
  { to: '/app/statistici', label: 'Statistici', icon: BarChart2, permission: 'stats.view' },
  { to: '/app/audit', label: 'Audit', icon: FileText, permission: 'audit.view' },
  { to: '/app/patrule', label: 'Patrule', icon: Car, permission: 'patrols.view', mockOnly: true },
  { to: '/app/reguli', label: 'Reguli', icon: Sliders, permission: 'rules.view', mockOnly: true },
  { to: '/app/setari', label: 'Setări', icon: Settings, permission: 'settings.admin' },
]

<<<<<<< INTEGRATION
/** Route -> document.title / h1. Pages that render their own h1 have `own: true`. */
const TITLES: { match: (p: string) => boolean; title: string; own?: Permission }[] = [
  { match: (p) => p === '/app' || p === '/app/', title: 'Alerte' },
  { match: (p) => p.startsWith('/app/alerte/'), title: 'Dosar alertă', own: 'alerts.view' },
  { match: (p) => p === '/app/camere', title: 'Camere', own: 'cameras.view' },
  { match: (p) => p === '/app/analiza-video', title: 'Analiză video', own: 'video-analysis.view' },
  { match: (p) => p === '/app/arhiva', title: 'Căutare în arhivă', own: 'archive.search' },
  { match: (p) => p === '/app/statistici', title: 'Statistici', own: 'stats.view' },
  { match: (p) => p === '/app/patrule', title: 'Patrule' },
  { match: (p) => p === '/app/reguli', title: 'Reguli și zone' },
  { match: (p) => p === '/app/audit', title: 'Jurnal de audit' },
  { match: (p) => p === '/app/setari', title: 'Setări' },
=======
export const EXTRA_NAV: NavItem[] = [
  { to: '/app/patrule', label: 'Patrule', icon: Car, permission: 'patrols.view' },
  { to: '/app/reguli', label: 'Reguli & Zone', icon: Sliders, permission: 'rules.view' },
  { to: '/app/audit', label: 'Jurnal de audit', icon: FileText, permission: 'audit.view' },
>>>>>>> GITHUB_TARGET
]

function beep() {
  try {
    const ctx = new AudioContext()
    const o = ctx.createOscillator()
    o.frequency.value = 880
    o.connect(ctx.destination)
    o.start()
    o.stop(ctx.currentTime + 0.15)
  } catch { /* blocked by browser audio policy */ }
}

const CONN_LABEL = { connecting: 'Se conectează…', live: 'Conectat', reconnecting: 'Reconectare…', demo: 'Mod demo' } as const

function ConnectionIndicator() {
  const state = useConnection((s) => s.state)
  const dot = state === 'live' ? 'bg-ok' : state === 'demo' ? 'bg-caution' : 'bg-critical'
  return (
    <span className="inline-flex items-center gap-2 text-xs text-text-secondary px-2.5 py-1.5 rounded-full border border-border-subtle bg-panel/70" role="status">
      <span className={`w-2 h-2 rounded-full ${dot} ${state === 'live' ? 'live-dot text-ok' : ''}`} aria-hidden="true" />
      <span className="sr-only sm:not-sr-only">{CONN_LABEL[state]}</span>
    </span>
  )
}

const fmtClock = new Intl.DateTimeFormat('ro-RO', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Europe/Bucharest', timeZoneName: 'short' })

export default function AppLayout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const soundOnCritical = useDataStore((s) => s.settings.soundOnCritical)
  const storeError = useDataStore((s) => s.error)
  const queue = useQueue()
  const navigate = useNavigate()
  const location = useLocation()
  const mainRef = useRef<HTMLElement>(null)

  const [toast, setToast] = useState<Alert | null>(null)
  const [time, setTime] = useState(() => fmtClock.format(new Date()))
  const [menu, setMenu] = useState(false)
  const [palette, setPalette] = useState(false)

  useEffect(() => {
    const t = setInterval(() => setTime(fmtClock.format(new Date())), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette((p) => !p) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useLiveFeed((a) => {
    if (a.severity === 'critical' || a.severity === 'high') {
      setToast(a)
      if (a.severity === 'critical' && soundOnCritical) beep()
    }
  })

  const route = TITLES.find((t) => t.match(location.pathname)) ?? TITLES[0]
  // Per-route document title; move focus to <main> on navigation so keyboard/AT users land on the new content.
  useEffect(() => {
    document.title = `${route.title} · RoadSentinel`
    mainRef.current?.focus({ preventScroll: true })
    setMenu(false)
  }, [location.pathname, route.title])

  const items = NAV.filter((i) => (!i.mockOnly || USE_MOCKS) && (user ? can(user.role, i.permission) : true))
  const openAlertsCount = queue.filter((a) => a.status === 'new' || a.status === 'in_review').length
<<<<<<< INTEGRATION
  const roleLabel = user ? (ROLE_LABEL[user.role] ?? user.role) : '—'

  const commands: Command[] = [
    ...items.map((i) => ({ id: `nav-${i.to}`, label: i.label, hint: 'Pagină', icon: <i.icon size={16} aria-hidden="true" />, run: () => navigate(i.to) })),
    ...(can(user?.role, 'dashboard.view') ? queue.filter((a) => a.status === 'new' || a.status === 'in_review').slice(0, 5).map((a) => ({
      id: `alert-${a.id}`,
      label: `Dosar: ${ALERT_TYPE[a.type]?.label ?? a.ruleSummary ?? a.type}`,
      hint: 'Alertă',
      icon: <CommandIcon size={16} aria-hidden="true" />,
      run: () => navigate(`/app/alerte/${a.id}`),
    })) : []),
  ]
=======
  // The first few clips are preloaded before the app is shown; the rest follow in the background.
  // The overlay never waits for all of them, nor longer than PRELOAD_MAX_WAIT_MS.
  const loaded = useDataStore((s) => USE_MOCKS || s.stats !== null)
  const dataError = useDataStore((s) => s.error)
  const loadFailed = dataError !== null
  const [overlay, setOverlay] = useState(true)
  const [timedOut, setTimedOut] = useState(false)
  const [clipsDone, setClipsDone] = useState(0)
  const clipTotal = new Set(queue.map((a) => a.clip?.src).filter(Boolean)).size
  const clipKey = queue.map((a) => a.id).join(',')
  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), PRELOAD_MAX_WAIT_MS)
    return () => clearTimeout(timer)
  }, [])
  useEffect(() => {
    void preloadClips(queue.map((a) => a.clip?.src), (done) => setClipsDone(done))
  }, [clipKey])
  const ready = preloadReady({ loaded, failed: loadFailed, timedOut, total: clipTotal, done: clipsDone })
  useEffect(() => { if (ready) setOverlay(false) }, [ready])
  const clipTarget = Math.min(clipTotal, PRELOAD_FIRST)
  const initials = user?.fullName
    ? user.fullName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : '—'

  // Dynamic Page titles
  const getPageHeader = () => {
    const p = location.pathname
    if (p === '/app' || p === '/app/') {
      return {
        title: 'Dispecerat / Panou principal',
        hasLiveDot: true,
      }
    }
    if (p.startsWith('/app/alerte/') && p !== '/app/alerte') {
      return null // AlertDetailPage renders its own custom CCTV header
    }
    if (p === '/app/camere') {
      return null // CamerasPage renders its own title + controls header
    }
    if (p === '/app/arhiva') {
      return null // ArchivePage renders its own prominent search bar
    }
    if (p === '/app/statistici') {
      return null // StatsPage renders its own title + 30 days selector + export
    }
    if (p === '/app/patrule') {
      return { title: 'Dispecerat / Patrule pe teren', hasLiveDot: false }
    }
    if (p === '/app/reguli') {
      return { title: 'Configurare / Reguli și zone de trafic', hasLiveDot: false }
    }
    if (p === '/app/audit') {
      return { title: 'Securitate / Jurnal de audit', hasLiveDot: false }
    }
    if (p === '/app/setari') {
      return { title: 'Sistem / Setări operaționale', hasLiveDot: false }
    }
    return { title: 'Dispecerat / Panou principal', hasLiveDot: true }
  }
>>>>>>> GITHUB_TARGET

  const linkCls = (active: boolean) =>
    `nav-link relative flex items-center gap-3 rounded-lg px-3 min-h-[var(--target-min)] py-2 text-sm font-medium ${
      active ? 'nav-active bg-elevation text-action' : 'text-text-secondary hover:text-text-primary hover:bg-elevation/60'
    }`

  const badge = (i: NavItem) =>
    i.to === '/app' && openAlertsCount > 0 ? (
      <span className="ml-auto min-w-[20px] px-1.5 text-xs font-semibold rounded-full bg-danger text-white text-center" aria-label={`${openAlertsCount} alerte de verificat`}>
        {openAlertsCount}
      </span>
    ) : null

  return (
<<<<<<< INTEGRATION
    <div className="flex h-dvh w-full overflow-hidden text-text-primary font-sans">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-3 focus:py-2 focus:rounded-md focus:bg-action focus:text-on-accent">
        Sari la conținut
      </a>

      {/* Left rail: icons only 640-1023px, icons + labels from 1024px, hidden on phones */}
      <aside className="hidden sm:flex w-14 lg:w-56 bg-panel/80 border-r border-border-subtle flex-col py-4 px-2 shrink-0 backdrop-blur">
        <NavLink to="/app" end aria-label="RoadSentinel, alerte" className="flex items-center gap-2.5 px-1.5 pb-5 rounded-lg">
          <Logo variant="mark" size={32} />
          <span className="hidden lg:inline font-display font-bold text-lg">Road<span className="text-gradient">Sentinel</span></span>
        </NavLink>
        <nav aria-label="Navigare principală" className="flex flex-col gap-1">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.exact} title={i.label} aria-label={i.label} className={({ isActive }) => linkCls(isActive)}>
              <i.icon size={18} aria-hidden="true" className="shrink-0" />
              <span className="hidden lg:inline">{i.label}</span>
              <span className="hidden lg:contents">{badge(i)}</span>
            </NavLink>
          ))}
        </nav>
=======
    <div className="flex h-screen w-screen overflow-hidden bg-[#0A0E14] text-[#E6EDF3] font-sans selection:bg-[#3DA5FF]/30 selection:text-white">
      {overlay && (
        <div className="fixed inset-0 z-[100] bg-[#0A0E14] flex flex-col items-center justify-center gap-5">
          <Logo variant="full" className="h-10" />
          <div className="font-sans text-xl font-bold uppercase tracking-wider text-[#E6EDF3]">Pregătire dosare video</div>
          <div className="w-80 h-2 rounded-full bg-[#17202B] overflow-hidden">
            <div className="h-full bg-[#3DA5FF] transition-all duration-300" style={{ width: `${clipTarget ? Math.min(1, clipsDone / clipTarget) * 100 : 0}%` }} />
          </div>
          <div className="text-xs font-mono text-[#7D8A9B]">
            {clipTarget ? `${Math.min(clipsDone, clipTarget)} / ${clipTarget} clipuri pregătite` : 'Se conectează la server…'}
          </div>
          <button type="button" onClick={() => setOverlay(false)} className="text-[11px] text-[#7D8A9B] hover:text-[#E6EDF3] underline cursor-pointer">
            Continuă oricum (restul se încarcă în fundal)
          </button>
        </div>
      )}
      {/* Errors from loading or from an operator action (a failed "Confirmă") are shown, not swallowed */}
      {dataError && (
        <div role="alert" data-testid="error-banner" className="fixed top-3 left-1/2 -translate-x-1/2 z-[90] w-[min(92vw,640px)] flex items-start gap-3 rounded-md border border-[#FF3B3B] bg-[#2A1215] px-4 py-3 shadow-2xl">
          <AlertTriangle size={18} className="text-[#FF3B3B] shrink-0 mt-0.5" aria-hidden />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-[#E6EDF3]">Operațiunea nu a reușit. Reîncercați.</div>
            <div className="text-xs text-[#C9D1D9] mt-0.5 break-words">{dataError}</div>
          </div>
          <button type="button" onClick={() => useDataStore.setState({ error: null })} aria-label="Închide mesajul de eroare" className="text-[#C9D1D9] hover:text-white cursor-pointer shrink-0">
            <X size={16} />
          </button>
        </div>
      )}
      {/* 1. Left Narrow Vertical Sidebar */}
      <aside className="w-16 sm:w-20 bg-[#111821] border-r border-[#1E2A36] flex flex-col justify-between items-center py-4 shrink-0 z-30 select-none">
        {/* Top: Logo */}
        <div className="flex flex-col items-center">
          <NavLink to="/app" end title="Panou dispecerat" className="group">
            <Logo variant="mark" size={32} className="group-hover:scale-105 transition-transform" />
          </NavLink>

          {/* Navigation Items */}
          <nav className="mt-8 flex flex-col gap-2 w-full">
            {MAIN_NAV.filter((item) => (user ? can(user.role, item.permission) : true)).map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.exact}
                  className={({ isActive }) =>
                    `relative flex flex-col items-center justify-center py-2.5 w-full transition-all group ${
                      isActive
                        ? 'text-[#3DA5FF] bg-[#17202B]'
                        : 'text-[#7D8A9B] hover:text-[#E6EDF3] hover:bg-[#17202B]/50'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {/* Active Blue Left Bar */}
                      {isActive && (
                        <span className="absolute left-0 top-0 bottom-0 w-1 bg-[#3DA5FF] shadow-[0_0_10px_rgba(61,165,255,0.7)]" />
                      )}
                      <div className="relative">
                        <Icon size={20} strokeWidth={isActive ? 2.2 : 1.8} />
                        {item.to === '/app' && openAlertsCount > 0 && (
                          <span className="absolute -top-1 -right-2 px-1 py-0.2 min-w-[14px] text-[9px] font-sans font-bold rounded-full bg-[#FF3B3B] text-white flex items-center justify-center">
                            {openAlertsCount}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] font-sans font-semibold mt-1 tracking-wider uppercase">
                        {item.label}
                      </span>
                    </>
                  )}
                </NavLink>
              )
            })}
          </nav>
        </div>

        {/* Bottom: Version tag & subtle actions */}
        <div className="flex flex-col items-center gap-3">
          {/* Quick link to Audit/Patrule if admin */}
          {user?.role === 'admin' && (
            <div className="flex flex-col gap-1 w-full px-2">
              <NavLink
                to="/app/audit"
                title="Jurnal de audit"
                className={({ isActive }) =>
                  `flex items-center justify-center p-1.5 rounded-md text-[#7D8A9B] hover:text-[#E6EDF3] transition-colors ${
                    isActive ? 'bg-[#17202B] text-[#3DA5FF]' : ''
                  }`
                }
              >
                <FileText size={16} />
              </NavLink>
            </div>
          )}
        </div>
>>>>>>> GITHUB_TARGET
      </aside>

      <div className="flex-1 flex flex-col min-w-0 h-dvh overflow-hidden">
        <header className="min-h-16 px-3 sm:px-6 py-2 border-b border-border-subtle bg-void/70 backdrop-blur-md flex items-center gap-3 shrink-0 z-20">
          <NavLink to="/app" end aria-label="RoadSentinel" className="sm:hidden"><Logo variant="mark" size={28} /></NavLink>
          {!(route.own && can(user?.role, route.own)) && (
            <h1 className="font-display text-xl font-semibold truncate">{route.title}</h1>
          )}
          <div className="ml-auto flex items-center gap-2 sm:gap-4 shrink-0">
            <button
              type="button"
              onClick={() => setPalette(true)}
              aria-label="Deschide paleta de comenzi (Ctrl+K)"
              className="press hidden md:flex items-center gap-2 min-h-9 w-48 lg:w-64 px-3 rounded-lg bg-panel/80 border border-border text-sm text-text-muted hover:text-text-primary hover:border-action/50 cursor-pointer"
            >
              <Search size={15} aria-hidden="true" />
              <span className="flex-1 text-left">Caută sau mergi la…</span>
              <kbd className="font-mono text-xs border border-border rounded px-1.5">Ctrl K</kbd>
            </button>
            <button type="button" onClick={() => setPalette(true)} aria-label="Deschide paleta de comenzi" className="press md:hidden inline-flex items-center justify-center w-9 h-9 min-h-[var(--target-min)] min-w-[var(--target-min)] rounded-lg text-text-secondary hover:bg-elevation cursor-pointer">
              <Search size={18} aria-hidden="true" />
            </button>
            <ConnectionIndicator />
            <span className="hidden sm:inline font-mono text-sm tabular-nums text-text-secondary" title="Ora Europa/București">{time}</span>
            <CalmToggle />
            <ThemeToggle />
            <div className="relative">
              <button
                type="button"
                aria-label="Meniu utilizator"
                aria-haspopup="menu"
                aria-expanded={menu}
                onClick={() => setMenu(!menu)}
                className="flex items-center gap-2 px-2 min-h-9 rounded-md hover:bg-panel cursor-pointer"
              >
                <Menu size={16} aria-hidden="true" className="sm:hidden" />
                <span className="hidden sm:flex flex-col text-left leading-tight">
                  <span className="text-sm font-medium">{user?.username ?? '—'}</span>
                  <span className="text-xs text-text-secondary">{roleLabel}</span>
                </span>
              </button>
              {menu && (
                <div role="menu" className="absolute right-0 mt-2 w-56 glass rounded-xl p-2 z-50 rise">
                  <div className="p-2 border-b border-border mb-1">
                    <div className="text-sm font-medium">{user?.username}</div>
                    <div className="text-xs text-text-secondary">{roleLabel}</div>
                  </div>
<<<<<<< INTEGRATION
                  {can(user?.role, 'settings.admin') && (
                    <button role="menuitem" type="button" onClick={() => { setMenu(false); navigate('/app/setari') }}
                      className="w-full text-left px-2.5 min-h-[var(--target-min)] text-sm text-text-secondary hover:text-text-primary hover:bg-elevation rounded-md flex items-center gap-2 cursor-pointer">
                      <Settings size={14} aria-hidden="true" /> Setări
                    </button>
                  )}
                  <button role="menuitem" type="button" onClick={() => { setMenu(false); logout() }}
                    className="w-full text-left px-2.5 min-h-[var(--target-min)] text-sm text-critical hover:bg-critical/10 rounded-md flex items-center gap-2 cursor-pointer">
                    <LogOut size={14} aria-hidden="true" /> Deconectare
                  </button>
                </div>
              )}
=======
                </button>

                {/* Dropdown Menu */}
                {userDropdown && (
                  <div className="absolute right-0 mt-2 w-56 bg-[#111821] border border-[#1E2A36] rounded-md p-2 shadow-2xl z-50">
                    <div className="p-2 border-b border-[#1E2A36] mb-1">
                      <div className="font-semibold text-xs text-[#E6EDF3]">{user?.fullName || 'Operator Dispecerat'}</div>
                      {user?.unit && <div className="text-[10px] text-[#7D8A9B]">{user.unit}</div>}
                      {user && <div className="text-[10px] text-[#3DA5FF] mt-1">{ROLE_LABEL[user.role]}</div>}
                    </div>

                    {can(user?.role, 'settings.admin') && (
                      <button
                        onClick={() => {
                          setUserDropdown(false)
                          navigate('/app/setari')
                        }}
                        className="w-full text-left px-2.5 py-1.5 text-xs text-[#7D8A9B] hover:text-[#E6EDF3] hover:bg-[#17202B] rounded-md transition-colors flex items-center gap-2 cursor-pointer"
                      >
                        <Settings size={14} />
                        <span>Setări platformă</span>
                      </button>
                    )}

                    <button
                      onClick={() => {
                        setUserDropdown(false)
                        logout()
                      }}
                      className="w-full text-left px-2.5 py-1.5 text-xs text-[#FF3B3B] hover:bg-[#FF3B3B]/10 rounded-md transition-colors flex items-center gap-2 cursor-pointer mt-1"
                    >
                      <LogOut size={14} />
                      <span>Deconectare</span>
                    </button>
                  </div>
                )}
              </div>
>>>>>>> GITHUB_TARGET
            </div>
          </div>
        </header>

        {USE_MOCKS && <Banner tone="warn">Mod demonstrativ: datele sunt generate local, nu provin din sistem.</Banner>}
        {storeError && <Banner tone="error">{storeError}</Banner>}

        <main id="main" ref={mainRef} tabIndex={0} aria-label={route.title} className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
          <div key={location.pathname} className="page-in min-h-full"><Outlet /></div>
        </main>

        {/* Phone: bottom tab bar (primary destinations) */}
        <nav aria-label="Navigare principală (mobil)" className="sm:hidden border-t border-border-subtle bg-panel/90 backdrop-blur flex pb-[env(safe-area-inset-bottom)]">
          {items.slice(0, 5).map((i) => (
            <NavLink key={i.to} to={i.to} end={i.exact}
              className={({ isActive }) => `press flex-1 flex flex-col items-center justify-center gap-0.5 min-h-[56px] text-xs ${isActive ? 'text-action font-semibold' : 'text-text-secondary'}`}>
              <span className="relative">
                <i.icon size={20} aria-hidden="true" />
                {i.to === '/app' && openAlertsCount > 0 && (
                  <span className="absolute -top-1.5 -right-3 min-w-[16px] px-1 text-xs leading-4 rounded-full bg-danger text-white text-center" aria-label={`${openAlertsCount} alerte de verificat`}>{openAlertsCount}</span>
                )}
              </span>
              {i.label}
            </NavLink>
          ))}
        </nav>
      </div>

<<<<<<< INTEGRATION
      <CommandPalette open={palette} onClose={() => setPalette(false)} commands={commands} onFreeText={can(user?.role, 'archive.search') ? (q) => navigate('/app/arhiva', { state: { search: q } }) : undefined} />

      {/* New critical/high alert: announced politely, never steals focus, stays until dismissed */}
      <div aria-live="polite" aria-atomic="true" className="fixed bottom-20 sm:bottom-6 right-3 sm:right-6 z-50 w-[calc(100%-1.5rem)] sm:max-w-sm">
        {toast && (
          <div className="glass rounded-xl p-4 rise sev-edge sev-edge-critical !border-critical/60">
            <div className="flex items-start justify-between gap-3">
              <span className="font-display text-sm font-semibold text-critical">Alertă nouă</span>
              <button type="button" aria-label="Închide notificarea" onClick={() => setToast(null)}
                className="p-1 -m-1 text-text-secondary hover:text-text-primary cursor-pointer"><X size={16} aria-hidden="true" /></button>
            </div>
            <p className="mt-1 text-sm font-medium">{ALERT_TYPE[toast.type]?.label ?? toast.ruleSummary ?? toast.type}</p>
            <p className="text-xs text-text-secondary mt-0.5">
              Cameră: {useDataStore.getState().cameras.find((c) => c.id === toast.cameraId)?.name ?? toast.cameraId}
              {toast.metrics?.speedKmh ? ` · ~${Math.round(toast.metrics.speedKmh)} km/h` : ''}
            </p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" className="flex-1" onClick={() => { navigate(`/app/alerte/${toast.id}`); setToast(null) }}>
                Deschide dosarul <ArrowRight size={13} aria-hidden="true" />
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setToast(null)}>Închide</Button>
=======
          <div className="mt-2">
            <div className="font-bold text-sm text-[#E6EDF3]">
              {toast.ruleSummary || ALERT_TYPE[toast.type].label}
            </div>
            <div className="text-xs text-[#7D8A9B] mt-0.5">
              Cameră: {cameraById(toast.cameraId)?.name ?? toast.cameraId} · {toast.metrics?.speedKmh ? `${toast.metrics.speedKmh} km/h` : 'Eveniment rutier'}
>>>>>>> GITHUB_TARGET
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
