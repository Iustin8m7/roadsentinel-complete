import { create } from 'zustand'
import type { SessionUser } from '@/types'
import { api, initCsrf, post, USE_MOCKS, type Me } from '@/lib/api'
import { useAuthStore as mockStore } from './mock-auth'

interface BackendIdentity { role: string; permissions?: string[]; id?: string; email?: string; display_name?: string }
const sessionUser = (me: Me, identity?: BackendIdentity): SessionUser | null => me.operator || !me.auth_required ? {
  id: identity?.id ?? me.operator ?? 'local', username: identity?.email ?? me.operator ?? 'local', fullName: identity?.display_name ?? me.operator ?? 'Operator local',
  rank: '', badge: '', unit: '',
  role: identity?.role === 'tenant_admin' || identity?.role === 'system_admin' ? 'admin' : identity?.role === 'patrol' ? 'patrula' : identity?.role === 'auditor' ? 'auditor' : 'operator',
  backendRole: identity?.role, backendPermissions: identity?.permissions ?? [],
} : null

async function fetchIdentity(): Promise<BackendIdentity> {
  return api<BackendIdentity>('/api/auth/me')
}
export const defaultLanding = (user: SessionUser | null) => user?.backendRole === 'auditor' || user?.backendRole === 'system_admin' ? '/app/audit' : '/app'
export type LoginResult = { ok: true; mfa?: boolean; enrollment?: boolean } | { ok: false; error: string }
interface AuthState {
  user: SessionUser | null; expiresAt: number | null
  login: (username: string, password: string, remember: boolean) => Promise<LoginResult>
  /** Second step. Second factor: TOTP or recovery code, required for every account. */
  verifyMfa: (input: { code: string } | { recovery_code: string }) => Promise<LoginResult>
  startMfaEnrollment: () => Promise<{ ok: true; qr: string; secret: string } | { ok: false; error: string }>
  confirmMfaEnrollment: (code: string) => Promise<{ ok: true; recoveryCodes: string[] } | { ok: false; error: string }>
  finishMfaEnrollment: () => Promise<LoginResult>
  logout: () => void; isSessionValid: () => boolean
}
const realStore = create<AuthState>((set, get) => ({
  user: null, expiresAt: null,
  async login(username, password) {
    try {
      await initCsrf()
      const me = await post<Me>('/api/login', { operator: username.trim(), password })
      if (me.mfa_enrollment) return { ok: true, enrollment: true }
      if (me.mfa_required) return { ok: true, mfa: true }
      set({ user: sessionUser(me, await fetchIdentity()) })
      return { ok: true }
    } catch (error) { return { ok: false, error: (error as Error).message } }
  },
  async verifyMfa(input) {
    try {
      await post('/api/auth/mfa/verify', input)
      const me = await api<Me>('/api/me')
      set({ user: sessionUser(me, await fetchIdentity()) })
      return { ok: true }
    } catch (error) { return { ok: false, error: (error as Error).message } }
  },
  async startMfaEnrollment() {
    try {
      const started = await post<{ qr_svg_data_uri: string; secret: string }>('/api/auth/mfa/enroll/start')
      return { ok: true, qr: started.qr_svg_data_uri, secret: started.secret }
    } catch (error) { return { ok: false, error: (error as Error).message } }
  },
  async confirmMfaEnrollment(code) {
    try {
      const result = await post<{ recovery_codes: string[] }>('/api/auth/mfa/enroll/confirm', { code })
      // Keep the guest page mounted until the user acknowledges the one-time codes.
      return { ok: true, recoveryCodes: result.recovery_codes }
    } catch (error) { return { ok: false, error: (error as Error).message } }
  },
  async finishMfaEnrollment() {
    try {
      const me = await api<Me>('/api/me')
      set({ user: sessionUser(me, await fetchIdentity()) })
      return { ok: true }
    } catch (error) { return { ok: false, error: (error as Error).message } }
  },
  logout() {
    void post('/api/logout').then(() => { set({ user: null }); location.assign('/login') })
      .catch((error: Error) => window.alert(error.message))
  },
  isSessionValid: () => !!get().user,
}))
export const useAuthStore: typeof realStore = USE_MOCKS ? mockStore : realStore
export async function restoreSession() {
  if (USE_MOCKS) return
  await initCsrf()
  const me = await api<Me>('/api/me')
  realStore.setState({ user: sessionUser(me, me.operator ? await fetchIdentity() : undefined) })
}
export function actor() {
  const user = useAuthStore.getState().user
  return user ? { username: user.username, role: user.role } : { username: '—', role: 'anonim' as const }
}
