/**
 * Minimal API client. Auth is cookie-only (HttpOnly cookies set by the API); this module never
 * sees or stores a token. It adds the double-submit CSRF header to unsafe requests and
 * transparently refreshes the session once on 401.
 */

export const CSRF_COOKIE = "__Secure-rs_csrf";
export const CSRF_HEADER = "X-CSRF-Token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
  }

  get reauthRequired(): boolean {
    return this.status === 403 && this.detail === "reauth_required";
  }
}

type Listener = () => void;
const sessionExpiredListeners = new Set<Listener>();

/** Called when the session can no longer be refreshed (expired, revoked, reuse detected). */
export function onSessionExpired(listener: Listener): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

export function readCookie(name: string, source: string = document.cookie): string | null {
  for (const part of source.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

let csrfPromise: Promise<string> | null = null;

async function csrfToken(): Promise<string> {
  const existing = readCookie(CSRF_COOKIE);
  if (existing) return existing;
  csrfPromise ??= fetch("/api/auth/csrf", { credentials: "same-origin", cache: "no-store" })
    .then((r) => r.json())
    .then((b: { csrf_token: string }) => b.csrf_token)
    .finally(() => {
      csrfPromise = null;
    });
  return csrfPromise;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const NO_REFRESH = [
  "/api/auth/login",
  "/api/auth/refresh",
  "/api/auth/mfa/",
  "/api/auth/invitations/",
  "/api/auth/reset/",
];

async function raw(method: string, path: string, body?: unknown): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method)) headers[CSRF_HEADER] = await csrfToken();
  return fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
  });
}

let refreshing: Promise<boolean> | null = null;

export async function refreshSession(): Promise<boolean> {
  refreshing ??= raw("POST", "/api/auth/refresh")
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  let res = await raw(method, path, body);
  if (res.status === 401 && !NO_REFRESH.some((p) => path.startsWith(p))) {
    if (await refreshSession()) {
      res = await raw(method, path, body);
    } else {
      sessionExpiredListeners.forEach((l) => l());
    }
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const get = <T>(path: string) => api<T>("GET", path);
export const post = <T>(path: string, body?: unknown) => api<T>("POST", path, body ?? {});
export const patch = <T>(path: string, body?: unknown) => api<T>("PATCH", path, body ?? {});
export const del = <T>(path: string) => api<T>("DELETE", path);
