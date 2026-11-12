export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === '1'
export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
export const apiUrl = (path: string) => `${API_URL}${path}`
export const mediaUrl = (path: string | null) => path ? (/^https?:\/\//.test(path) ? path : apiUrl(path)) : undefined

export class ApiError extends Error {
  /** `detail` keeps a structured error body ({code, message, ...}) when the server sends one. */
  constructor(public status: number, message: string, public detail?: unknown) { super(message) }
  get code(): string | undefined {
    const d = this.detail as { code?: unknown } | undefined
    return typeof d?.code === 'string' ? d.code : undefined
  }
}

function csrfToken() {
  const csrf = document.cookie.split('; ').find((c) => c.startsWith('__Secure-rs_csrf='))?.split('=').slice(1).join('=')
    ?? document.cookie.split('; ').find((c) => c.startsWith('rs_csrf='))?.split('=').slice(1).join('=')
  return csrf ? decodeURIComponent(csrf) : undefined
}

const AUTH_PATHS = ['/api/login', '/api/login/mfa', '/api/auth/mfa/verify', '/api/auth/refresh', '/api/me']
let refreshing: Promise<boolean> | null = null

/** The secure backend's access cookie lives 10 minutes: renew it once, shared by concurrent calls. */
function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(apiUrl('/api/auth/refresh'), {
    method: 'POST', credentials: 'include', headers: csrfToken() ? { 'X-CSRF-Token': csrfToken()! } : {},
  }).then((r) => r.ok).catch(() => false).finally(() => { refreshing = null })
  return refreshing
}

// ------------------------------------------------------------ MFA step-up (403 reauth_required)
export const REAUTH_CANCELLED = 'Acțiune anulată: este necesară confirmarea cu codul de autentificare.'
export interface ReauthPrompt { submit: (code: string) => Promise<void>; cancel: () => void }

let showReauth: ((prompt: ReauthPrompt | null) => void) | null = null
let reauthing: Promise<void> | null = null
let reauthCount = 0

/** The one mounted ReauthDialog registers here; returns the unsubscribe function. */
export function onReauthPrompt(listener: (prompt: ReauthPrompt | null) => void) {
  showReauth = listener
  return () => { showReauth = null }
}

/** Plain fetch: a wrong code is a 401 here and must not trigger the expired-session redirect. */
async function verifyReauth(code: string) {
  let response: Response
  try {
    await refreshSession() // the access cookie may have expired while the prompt was open
    const csrf = csrfToken()
    response = await fetch(apiUrl('/api/auth/reauth'), {
      method: 'POST', credentials: 'include', body: JSON.stringify({ code: code.replace(/\s+/g, '') }),
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
    })
  } catch { throw new Error('Eroare de conexiune. Reîncercați.') }
  if (response.ok) return
  throw new Error(response.status === 401 || response.status === 422 ? 'Cod incorect.'
    : response.status === 429 ? 'Prea multe încercări. Reîncercați mai târziu.' : `Confirmarea a eșuat (${response.status}).`)
}

/** Concurrent 403s share one prompt. It settles when the code is accepted or the user cancels. */
function stepUp(): Promise<void> {
  reauthing ??= new Promise<void>((resolve, reject) => {
    if (!showReauth) return reject(new Error(REAUTH_CANCELLED))
    const close = () => showReauth?.(null)
    showReauth({
      submit: async (code) => { await verifyReauth(code); reauthCount += 1; close(); resolve() },
      cancel: () => { close(); reject(new Error(REAUTH_CANCELLED)) },
    })
  }).finally(() => { reauthing = null })
  return reauthing
}

export async function api<T>(path: string, init: RequestInit = {}, retried = false, steppedUp = false): Promise<T> {
  const headers = new Headers(init.headers)
  // JSON for string bodies; binary uploads (Blob/File) keep the type the caller set.
  if (typeof init.body === 'string') headers.set('Content-Type', 'application/json')
  const csrf = csrfToken()
  if (csrf) headers.set('X-CSRF-Token', csrf)
  const reauthsBefore = reauthCount
  const response = await fetch(apiUrl(path), { ...init, headers, credentials: 'include' })
  if (response.status === 401 && !retried && !AUTH_PATHS.includes(path) && await refreshSession()) {
    return api<T>(path, init, true, steppedUp)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const needsReauth = response.status === 403 && body.detail === 'reauth_required'
    if (needsReauth && !steppedUp) {
      // A step-up finished while this request was in flight: its code already covers the retry.
      if (reauthCount === reauthsBefore) await stepUp()
      return api<T>(path, init, retried, true)
    }
    if (response.status === 401 && location.pathname !== '/login') location.assign('/login')
    const message = needsReauth ? 'Serverul cere din nou confirmarea cu codul de autentificare. Reîncercați.'
      : typeof body.detail === 'string' ? body.detail
      : typeof body.detail?.message === 'string' ? body.detail.message : `Cererea a eșuat (${response.status}).`
    throw new ApiError(response.status, message, body.detail)
  }
  return response.status === 204 ? undefined as T : response.json()
}

export function uploadFile<T>(path: string, file: File, onProgress: (loaded: number, total: number) => void, fields: Record<string, string> = {}): Promise<T> {
  const send = (retried: boolean) => new Promise<T>((resolve, reject) => {
    const form = new FormData()
    form.append('file', file, file.name)
    for (const [key, value] of Object.entries(fields)) form.append(key, value)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', apiUrl(path))
    xhr.withCredentials = true
    const csrf = csrfToken()
    if (csrf) xhr.setRequestHeader('X-CSRF-Token', csrf)
    xhr.upload.onprogress = (event) => onProgress(event.loaded, event.total || file.size)
    xhr.onerror = () => reject(new ApiError(0, 'Încărcarea s-a întrerupt. Verifică rețeaua locală și încearcă din nou.'))
    xhr.onload = async () => {
      if (xhr.status === 401 && !retried && await refreshSession()) {
        send(true).then(resolve, reject)
        return
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const detail = typeof xhr.response?.detail === 'string' ? xhr.response.detail : `Încărcarea a eșuat (${xhr.status}).`
        if (xhr.status === 401 && location.pathname !== '/login') location.assign('/login')
        reject(new ApiError(xhr.status, detail))
        return
      }
      resolve(xhr.response as T)
    }
    xhr.responseType = 'json'
    xhr.send(form)
  })
  return send(false)
}


export async function initCsrf() {
  try { await api('/api/auth/csrf') }
  catch (error) {
    // The local demonstration server predates CSRF protection.
    if (!(error instanceof ApiError && error.status === 404)) throw error
  }
}
export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export interface Me { operator: string | null; auth_required: boolean; mfa_required?: boolean; mfa_enrollment?: boolean }
