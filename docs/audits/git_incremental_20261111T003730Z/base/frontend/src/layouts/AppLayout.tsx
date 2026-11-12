import { preloadClips, preloadImages } from '@/lib/demo'
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
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { useDataStore } from '@/store/data'
import { can, type Permission } from '@/lib/permissions'
import { useLiveFeed, useQueue } from '@/hooks'
import type { Alert } from '@/types'
import { Logo } from '@/assets/brand/Logo'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  permission: Permission
  exact?: boolean
}

export const MAIN_NAV: NavItem[] = [
  { to: '/app', label: 'Panou', icon: LayoutDashboard, permission: 'dashboard.view', exact: true },
  { to: '/app/camere', label: 'Camere', icon: Video, permission: 'cameras.view' },
  { to: '/app/arhiva', label: 'Arhivă', icon: Archive, permission: 'archive.search' },
  { to: '/app/statistici', label: 'Statistici', icon: BarChart2, permission: 'stats.view' },
  { to: '/app/setari', label: 'Setări', icon: Settings, permission: 'settings.admin' },
]

export const EXTRA_NAV: NavItem[] = [
  { to: '/app/patrule', label: 'Patrule', icon: Car, permission: 'patrols.view' },
  { to: '/app/reguli', label: 'Reguli & Zone', icon: Sliders, permission: 'rules.view' },
  { to: '/app/audit', label: 'Audit Log', icon: FileText, permission: 'audit.view' },
]

function beep() {
  try {
    const ctx = new AudioContext()
    const o = ctx.createOscillator()
    o.frequency.value = 880
    o.connect(ctx.destination)
    o.start()
    o.stop(ctx.currentTime + 0.15)
  } catch {
    /* blocked by browser audio policy */
  }
}

export default function AppLayout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const soundOnCritical = useDataStore((s) => s.settings.soundOnCritical)
  const queue = useQueue()
  const navigate = useNavigate()
  const location = useLocation()

  const [toast, setToast] = useState<Alert | null>(null)
  const [time, setTime] = useState('')
  const [userDropdown, setUserDropdown] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const update = () => {
      const now = new Date()
      setTime(now.toTimeString().split(' ')[0])
    }
    update()
    const t = setInterval(update, 1000)
    return () => clearInterval(t)
  }, [])

  useLiveFeed((a) => {
    if (a.severity === 'critical' || a.severity === 'high') {
      setToast(a)
      if (a.severity === 'critical' && soundOnCritical) beep()
    }
  })

  // Keyboard controls for Toast
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 8000)

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        navigate(`/app/alerte/${toast.id}`)
        setToast(null)
      } else if (e.key === 'Escape') {
        setToast(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [toast, navigate])

  const openAlertsCount = queue.filter((a) => a.status === 'new' || a.status === 'in_review').length
  // Preload every alert's clip before showing the app, so no video ever buffers during the pitch.
  const allAlerts = useDataStore((s) => s.alerts)
  const [skipPreload, setSkipPreload] = useState(false)
  const [preload, setPreload] = useState<{ done: number; total: number; finished: boolean }>({ done: 0, total: 0, finished: false })
  const clipKey = allAlerts.map((a) => a.id).join(',')
  useEffect(() => {
    if (!allAlerts.length) return
    const ordered = [...queue, ...allAlerts.filter((a) => !queue.includes(a))]
    preloadImages(ordered.map((a) => a.keyframeUrl))
    void preloadClips(ordered.map((a) => a.clip?.src), (done, total) => setPreload((p) => ({ ...p, done, total })))
      .then(() => setPreload((p) => ({ ...p, finished: true })))
  }, [clipKey])
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
      return { title: 'Securitate / Jurnal de audit (Directiva 2016/680)', hasLiveDot: false }
    }
    if (p === '/app/setari') {
      return { title: 'Sistem / Setări operaționale', hasLiveDot: false }
    }
    return { title: 'Dispecerat / Panou principal', hasLiveDot: true }
  }

  const pageHeader = getPageHeader()

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // Router state, not a ?q= URL parameter: search text may contain plates or names and
      // must not end up in history, logs or Referer headers.
      navigate('/app/arhiva', { state: { q: searchQuery.trim() } })
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0A0E14] text-[#E6EDF3] font-sans selection:bg-[#3DA5FF]/30 selection:text-white">
      {!preload.finished && !skipPreload && (
        <div className="fixed inset-0 z-[100] bg-[#0A0E14] flex flex-col items-center justify-center gap-5">
          <Logo variant="full" className="h-10" />
          <div className="font-sans text-xl font-bold uppercase tracking-wider text-[#E6EDF3]">Pregătire dosare video</div>
          <div className="w-80 h-2 rounded-full bg-[#17202B] overflow-hidden">
            <div className="h-full bg-[#3DA5FF] transition-all duration-300" style={{ width: `${preload.total ? (preload.done / preload.total) * 100 : 0}%` }} />
          </div>
          <div className="text-xs font-mono text-[#7D8A9B]">
            {preload.total ? `${preload.done} / ${preload.total} clipuri încărcate` : 'Se conectează la server…'}
          </div>
          <button type="button" onClick={() => setSkipPreload(true)} className="text-[11px] text-[#536070] hover:text-[#7D8A9B] underline cursor-pointer">
            Continuă oricum (restul se încarcă în fundal)
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
          <span className="font-mono text-[10px] text-[#536070] font-medium tracking-widest">
            v2.4
          </span>
        </div>
      </aside>

      {/* 2. Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Topbar (when rendered at shell level) */}
        {pageHeader && (
          <header className="h-14 px-6 border-b border-[#1E2A36] bg-[#0A0E14] flex items-center justify-between shrink-0 z-20">
            {/* Title */}
            <div className="flex items-center gap-3 min-w-0">
              <h1 className="font-sans text-2xl font-bold uppercase tracking-wider text-[#E6EDF3] truncate flex items-center gap-2">
                <span>{pageHeader.title}</span>
                {pageHeader.hasLiveDot && (
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF3B3B] animate-pulse shrink-0" />
                )}
              </h1>
            </div>

            {/* Right Controls: Search, Clock, Avatar */}
            <div className="flex items-center gap-5 shrink-0">
              {/* Quick Search */}
              <form onSubmit={handleSearchSubmit} className="hidden md:flex items-center relative">
                <Search size={15} className="absolute left-3 text-[#7D8A9B] pointer-events-none" />
                <input
                  type="text"
                  placeholder="Căutare"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-48 lg:w-60 bg-[#111821] border border-[#1E2A36] rounded-md pl-9 pr-3 py-1.5 text-xs text-[#E6EDF3] placeholder-[#536070] focus:outline-none focus:border-[#3DA5FF] focus:w-72 transition-all font-sans"
                />
              </form>

              {/* Large Digital Clock */}
              <div className="font-sans text-2xl lg:text-3xl font-bold text-[#E6EDF3] tracking-widest tabular-nums leading-none">
                {time}
              </div>

              {/* User Avatar + Status */}
              <div className="relative">
                <button
                  onClick={() => setUserDropdown(!userDropdown)}
                  className="flex items-center gap-2 p-1 rounded-md hover:bg-[#111821] transition-colors cursor-pointer select-none"
                >
                  <div className="relative">
                    <div className="w-8 h-8 rounded-full bg-[#17202B] border border-[#1E2A36] flex items-center justify-center font-sans font-bold text-xs text-[#3DA5FF]">
                      {initials}
                    </div>
                    <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-[#2ED47A] border-2 border-[#0A0E14]" />
                  </div>
                  <div className="hidden sm:flex flex-col text-left">
                    <span className="text-xs font-semibold text-[#E6EDF3] leading-tight">
                      {user?.username || '—'}
                    </span>
                    <span className="text-[10px] text-[#2ED47A] font-mono leading-tight">
                      ● {user?.role === 'admin' ? 'Administrator' : 'Operator'}
                    </span>
                  </div>
                </button>

                {/* Dropdown Menu */}
                {userDropdown && (
                  <div className="absolute right-0 mt-2 w-56 bg-[#111821] border border-[#1E2A36] rounded-md p-2 shadow-2xl z-50">
                    <div className="p-2 border-b border-[#1E2A36] mb-1">
                      <div className="font-semibold text-xs text-[#E6EDF3]">{user?.fullName || 'Operator Dispecerat'}</div>
                      <div className="text-[10px] text-[#7D8A9B]">{user?.unit || 'Brigada Rutieră'}</div>
                      <div className="text-[9px] font-mono text-[#3DA5FF] mt-1 uppercase">
                        ROL: {user?.role || 'operator'}
                      </div>
                    </div>

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
            </div>
          </header>
        )}

        {/* Scrollable Page Body (internal scrolling only on panels where needed) */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 bg-[#0A0E14]">
          <Outlet />
        </main>
      </div>

      {/* Live Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-[#111821] border border-[#FF3B3B] rounded-md p-4 shadow-[0_0_24px_rgba(255,59,59,0.35)] animate-bounce-short">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF3B3B] animate-ping" />
              <span className="font-sans font-bold text-xs uppercase text-[#FF3B3B] tracking-wider">
                ALERTĂ NOUĂ ÎN TIMP REAL
              </span>
            </div>
            <button
              onClick={() => setToast(null)}
              className="text-[#7D8A9B] hover:text-[#E6EDF3] transition-colors cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>

          <div className="mt-2">
            <div className="font-bold text-sm text-[#E6EDF3]">
              {toast.ruleSummary || toast.type}
            </div>
            <div className="text-xs text-[#7D8A9B] mt-0.5">
              Cameră: {toast.cameraId} · {toast.metrics?.speedKmh ? `${toast.metrics.speedKmh} km/h` : 'Eveniment rutier'}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={() => {
                navigate(`/app/alerte/${toast.id}`)
                setToast(null)
              }}
              className="flex-1 py-1.5 px-3 rounded-md bg-[#3DA5FF] text-white text-xs font-bold hover:bg-[#2C94F0] transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(61,165,255,0.4)]"
            >
              <span>Deschide dosarul</span>
              <ArrowRight size={13} />
            </button>
            <button
              onClick={() => setToast(null)}
              className="py-1.5 px-3 rounded-md bg-[#17202B] text-[#7D8A9B] hover:text-[#E6EDF3] text-xs font-medium transition-colors cursor-pointer"
            >
              Închide (Esc)
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
