import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from './auth'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
afterEach(() => { vi.unstubAllGlobals(); useAuthStore.setState({ user: null }) })

describe('login with MFA step', () => {
  it('does not create a session after the password step when MFA is required', async () => {
    vi.stubGlobal('document', { cookie: '' })
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) =>
      Promise.resolve(url.endsWith('/api/login') ? json({ operator: null, auth_required: true, mfa_required: true }) : json({})),
    ))
    const res = await useAuthStore.getState().login('operator', 'x', true)
    expect(res).toEqual({ ok: true, mfa: true })
    expect(useAuthStore.getState().user).toBeNull()
  })
  it('creates the session only after the second factor is accepted', async () => {
    vi.stubGlobal('document', { cookie: '' })
    const calls: string[] = []
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.endsWith('/api/auth/mfa/verify')) return Promise.resolve(new Response(null, { status: 204 }))
      if (url.endsWith('/api/me')) return Promise.resolve(json({ operator: 'operator', auth_required: true }))
      return Promise.resolve(json({ role: 'operator' }))
    }))
    const res = await useAuthStore.getState().verifyMfa({ recovery_code: 'abcd-efgh' })
    expect(res).toEqual({ ok: true })
    expect(useAuthStore.getState().user?.username).toBe('operator')
    expect(calls[0]).toBe('POST /api/auth/mfa/verify')
  })
  it('reports a wrong code without creating a session', async () => {
    vi.stubGlobal('document', { cookie: '' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Cod incorect' }, 401)))
    vi.stubGlobal('location', { pathname: '/login', assign: vi.fn() })
    const res = await useAuthStore.getState().verifyMfa({ code: '000000' })
    expect(res).toEqual({ ok: false, error: 'Cod incorect' })
    expect(useAuthStore.getState().user).toBeNull()
  })
})

it('keeps the recovery-code screen mounted until explicit acknowledgment', async () => {
  vi.stubGlobal('document', { cookie: '' })
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
    if (url.endsWith('/api/auth/mfa/enroll/confirm')) return Promise.resolve(json({ recovery_codes: ['test-recovery-code'] }))
    if (url.endsWith('/api/me')) return Promise.resolve(json({ operator: 'operator', auth_required: true }))
    return Promise.resolve(json({ role: 'operator', permissions: ['alerts:read'] }))
  }))
  const result = await useAuthStore.getState().confirmMfaEnrollment('123456')
  expect(result.ok).toBe(true)
  expect(useAuthStore.getState().user).toBeNull()
  expect((await useAuthStore.getState().finishMfaEnrollment()).ok).toBe(true)
  expect(useAuthStore.getState().user?.backendPermissions).toEqual(['alerts:read'])
})
