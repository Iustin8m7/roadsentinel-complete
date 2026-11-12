import { useAuthStore } from '@/store/auth'
import { USE_MOCKS } from './api'
import type { Role } from '@/types'

// Role-based access (README: "acces pe roluri"). Pages and actions check these.
export type Permission =
  | 'dashboard.view'
  | 'alerts.view'
  | 'alerts.decide'
  | 'alerts.dispatch'
  | 'cameras.view'
  | 'video-analysis.view'
  | 'video-analysis.manage'
  | 'rules.view'
  | 'rules.edit'
  | 'archive.search'
  | 'archive.unblur'
  | 'audit.view'
  | 'stats.view'
  | 'patrols.view'
  | 'settings.admin'

const ALL: Permission[] = [
  'dashboard.view',
  'alerts.view',
  'alerts.decide',
  'alerts.dispatch',
  'cameras.view',
  'video-analysis.view',
  'video-analysis.manage',
  'rules.view',
  'rules.edit',
  'archive.search',
  'archive.unblur',
  'audit.view',
  'stats.view',
  'patrols.view',
  'settings.admin',
]

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: ALL,
  operator: [
    'dashboard.view',
    'alerts.view',
    'alerts.decide',
    'alerts.dispatch',
    'cameras.view',
    'video-analysis.view',
    'video-analysis.manage',
    'archive.search',
    'rules.view',
    'patrols.view',
    'stats.view',
  ],
  anchetator: ['dashboard.view', 'alerts.view', 'archive.search', 'archive.unblur', 'audit.view', 'stats.view'],
  patrula: ['dashboard.view', 'alerts.view', 'cameras.view'],
  auditor: ['audit.view'],
}

export function can(role: Role | undefined, permission: Permission): boolean {
  if (!USE_MOCKS) {
    const granted = useAuthStore.getState().user?.backendPermissions ?? []
    const required: Record<Permission, string[]> = {
      'dashboard.view':['alerts:read'], 'alerts.view':['alerts:read'], 'alerts.decide':['alerts:decide'],
      'alerts.dispatch':['alerts:assign'], 'cameras.view':['cameras:read'],
      'video-analysis.view':['videos:read'], 'video-analysis.manage':['videos:analyze'],
      'rules.view':['cameras:status_read'], 'rules.edit':['cameras:manage'],
      'archive.search':['alerts:read'], 'archive.unblur':['approvals:request'],
      'audit.view':['audit:read'], 'stats.view':['stats:read'],
      'patrols.view':['alerts:assign'], 'settings.admin':['users:manage'],
    }
    return !!role && required[permission].every(p => granted.includes(p))
  }
  return !!role && ROLE_PERMISSIONS[role].includes(permission)
}

export const hasBackendPermission = (permissions: string[] | undefined, permission: string) =>
  permissions?.includes(permission) ?? false
