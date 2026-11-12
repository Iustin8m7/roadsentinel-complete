import { create } from 'zustand'
import { USE_MOCKS } from '@/lib/api'
import type { AuditEntry } from '@/types'
import { useAuditStore as mockStore } from './mock-audit'
const realStore = create<{ entries: AuditEntry[]; log: ReturnType<typeof mockStore.getState>['log']; clear: () => void }>(() => ({
  entries: [], log: () => {}, clear: () => {},
}))
export const useAuditStore = USE_MOCKS ? mockStore : realStore
export function mergeAudit(entries: AuditEntry[]) {
  useAuditStore.setState((state) => ({ entries: [...new Map([...entries, ...state.entries].map((entry) => [entry.id, entry])).values()].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 2000) }))
}
