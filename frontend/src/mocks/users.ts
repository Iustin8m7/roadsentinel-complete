import type { User } from '@/types'

// Mock accounts: mock-only credentials (VITE_USE_MOCKS=1), not valid against a real backend.
export const USERS: User[] = [
  {
    id: 'u-admin',
    username: 'admin',
    password: 'mock-only-demo',
    fullName: 'Administrator Sistem',
    rank: 'Comisar-șef',
    badge: 'RS-0001',
    unit: 'Brigada Rutieră București',
    role: 'admin',
  },
  {
    id: 'u-operator',
    username: 'operator',
    password: 'mock-only-demo',
    fullName: 'Andrei Popescu',
    rank: 'Agent-șef',
    badge: 'RS-1042',
    unit: 'Dispecerat Brigada Rutieră',
    role: 'operator',
  },
]
