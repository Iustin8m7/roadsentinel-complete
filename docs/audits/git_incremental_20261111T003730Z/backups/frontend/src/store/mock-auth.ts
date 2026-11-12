import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SessionUser } from '@/types'
import { USERS } from '@/mocks/users'
import { useAuditStore } from './mock-audit'

const SESSION_HOURS = 8 // one shift

interface AuthState {
  user: SessionUser | null
  expiresAt: number | null
  login: (username: string, password: string, remember: boolean) => Promise<{ ok: true } | { ok: false; error: string }>
  verifyMfa: (input: { code: string } | { recovery_code: string }) => Promise<{ ok: true; mfa?: boolean } | { ok: false; error: string }>
  startMfaEnrollment: () => Promise<{ ok: true; qr: string; secret: string } | { ok: false; error: string }>
  confirmMfaEnrollment: (code: string) => Promise<{ ok: true; recoveryCodes: string[] } | { ok: false; error: string }>
  finishMfaEnrollment: () => Promise<{ ok: true } | { ok: false; error: string }>
  logout: () => void
  isSessionValid: () => boolean
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// Mock authentication — credentials are checked against src/mocks/users.ts.
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      expiresAt: null,
      async login(username, password, remember) {
        await delay(600) // simulate network latency so loading states can be designed
        const u = USERS.find((x) => x.username === username.trim().toLowerCase() && x.password === password)
        const audit = useAuditStore.getState().log
        if (!u) {
          audit({ username: username || '—', role: 'anonim', action: 'login_failed' })
          return { ok: false, error: 'Utilizator sau parolă incorectă.' }
        }
        const { password: _omit, ...user } = u
        void _omit
        const hours = remember ? SESSION_HOURS * 3 : SESSION_HOURS
        set({ user, expiresAt: Date.now() + hours * 3600_000 })
        audit({ username: user.username, role: user.role, action: 'login' })
        return { ok: true }
      },
      async verifyMfa() {
        return { ok: false as const, error: 'Autentificarea în doi pași nu este disponibilă în modul demo.' }
      },
      async startMfaEnrollment() {
        return { ok: false as const, error: 'Configurarea MFA nu este disponibilă în modul demo.' }
      },
      async confirmMfaEnrollment() {
        return { ok: false as const, error: 'Configurarea MFA nu este disponibilă în modul demo.' }
      },
      async finishMfaEnrollment() { return { ok: false as const, error: 'MFA nu este disponibil în modul demo.' } },
      logout() {
        const u = get().user
        if (u) useAuditStore.getState().log({ username: u.username, role: u.role, action: 'logout' })
        set({ user: null, expiresAt: null })
      },
      isSessionValid() {
        const { user, expiresAt } = get()
        return !!user && !!expiresAt && expiresAt > Date.now()
      },
    }),
    { name: 'rs.session', version: 1 },
  ),
)

/** Current actor for audit entries. */
export function actor() {
  const u = useAuthStore.getState().user
  return u ? { username: u.username, role: u.role } : { username: '—', role: 'anonim' as const }
}
