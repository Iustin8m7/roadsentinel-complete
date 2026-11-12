import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuthStore, defaultLanding } from '@/store/auth'
import { can, type Permission } from '@/lib/permissions'
import { ForbiddenPage } from '@/pages/ErrorPages'

/** Redirects to /login when there is no valid session. */
export function RequireAuth() {
  const valid = useAuthStore((s) => s.isSessionValid())
  const location = useLocation()
  if (!valid) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

/** Shows a 403 page when the role lacks the permission. */
export function RequirePermission({ permission }: { permission: Permission }) {
  const role = useAuthStore((s) => s.user?.role)
  if (!can(role, permission)) return <ForbiddenPage />
  return <Outlet />
}

/** Login page is only reachable while logged out. */
export function GuestOnly() {
  const valid = useAuthStore((s) => s.isSessionValid())
  if (valid) return <Navigate to={defaultLanding(useAuthStore.getState().user)} replace />
  return <Outlet />
}
