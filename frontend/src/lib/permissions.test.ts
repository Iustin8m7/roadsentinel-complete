import { afterEach, expect, it } from 'vitest'
import { useAuthStore } from '@/store/auth'
import { can } from './permissions'
const user = { id:'test', username:'test', fullName:'Test', rank:'', badge:'', unit:'' }
afterEach(() => useAuthStore.setState({user:null}))
it('auditor navigation grants audit without alert or video access', () => {
  useAuthStore.setState({user:{...user,role:'auditor',backendPermissions:['audit:read','audit:verify']}})
  expect(can('auditor','audit.view')).toBe(true)
  expect(can('auditor','alerts.view')).toBe(false)
  expect(can('auditor','video-analysis.view')).toBe(false)
})
it('patrol cannot decide or read aggregate statistics', () => {
  useAuthStore.setState({user:{...user,role:'patrula',backendPermissions:['alerts:read','cameras:read']}})
  expect(can('patrula','alerts.view')).toBe(true)
  expect(can('patrula','alerts.decide')).toBe(false)
  expect(can('patrula','stats.view')).toBe(false)
})
it('an unrecognized or missing permission is fail-closed', () => {
  useAuthStore.setState({user:{...user,role:'admin',backendPermissions:[]}})
  expect(can('admin','settings.admin')).toBe(false)
})
