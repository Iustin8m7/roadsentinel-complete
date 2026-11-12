import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuditAction, AuditEntry, Role } from '@/types'

interface AuditState {
  entries: AuditEntry[]
  log: (e: { username: string; role: Role | 'anonim'; action: AuditAction; target?: string; details?: string }) => void
  clear: () => void
}

let seq = 0
const uid = () => `AUD-${Date.now().toString(36)}-${(++seq).toString(36)}`

// Append-only audit trail ("cine a văzut, ce a decis, când"), persisted in localStorage.
export const useAuditStore = create<AuditState>()(
  persist(
    (set) => ({
      entries: [],
      log: (e) => set((s) => ({ entries: [{ id: uid(), at: new Date().toISOString(), ...e }, ...s.entries].slice(0, 2000) })),
      clear: () => set({ entries: [] }),
    }),
    { name: 'rs.audit', version: 1 },
  ),
)
