import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, CSRF_HEADER, onSessionExpired, readCookie } from "./api/client";
import { clearClientState } from "./auth/cleanup";
import { startIdleTimer } from "./auth/idle";
import { sanitizePush } from "./pwa/pushPayload";

type FetchCall = [string, RequestInit | undefined];

function mockFetch(responses: Array<{ status: number; body?: unknown }>) {
  const calls: FetchCall[] = [];
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push([url, init]);
    const r = responses.shift() ?? { status: 200, body: {} };
    return new Response(r.status === 204 ? null : JSON.stringify(r.body ?? {}), {
      status: r.status,
    });
  });
  vi.stubGlobal("fetch", fn);
  return calls;
}

describe("api client", () => {
  beforeEach(() => {
    document.cookie = "__Secure-rs_csrf=tok123; path=/; secure";
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads cookies", () => {
    expect(readCookie("__Secure-rs_csrf", "a=1; __Secure-rs_csrf=abc; b=2")).toBe("abc");
    expect(readCookie("missing", "a=1")).toBeNull();
  });

  it("sends the CSRF header on unsafe methods only, and never an Authorization header", async () => {
    const calls = mockFetch([{ status: 200 }, { status: 200 }]);
    await api("POST", "/api/alerts/1/confirm", {});
    await api("GET", "/api/alerts");
    const postHeaders = calls[0][1]?.headers as Record<string, string>;
    const getHeaders = calls[1][1]?.headers as Record<string, string>;
    expect(postHeaders[CSRF_HEADER]).toBe("tok123");
    expect(getHeaders[CSRF_HEADER]).toBeUndefined();
    for (const [, init] of calls) {
      expect(init?.credentials).toBe("same-origin");
      expect(init?.cache).toBe("no-store");
      expect(Object.keys(init?.headers ?? {})).not.toContain("Authorization");
    }
  });

  it("refreshes once on 401 and retries", async () => {
    const calls = mockFetch([{ status: 401 }, { status: 204 }, { status: 200, body: [1] }]);
    await expect(api("GET", "/api/alerts")).resolves.toEqual([1]);
    expect(calls.map((c) => c[0])).toEqual(["/api/alerts", "/api/auth/refresh", "/api/alerts"]);
  });

  it("signals session expiry when refresh fails", async () => {
    mockFetch([{ status: 401 }, { status: 401 }]);
    const listener = vi.fn();
    const dispose = onSessionExpired(listener);
    await expect(api("GET", "/api/alerts")).rejects.toBeInstanceOf(ApiError);
    expect(listener).toHaveBeenCalledOnce();
    dispose();
  });

  it("exposes reauth_required", async () => {
    mockFetch([{ status: 403, body: { detail: "reauth_required" } }]);
    const err = await api("POST", "/api/approvals/x/approve").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).reauthRequired).toBe(true);
  });
});

describe("logout cleanup", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("clears Cache Storage, IndexedDB and web storage", async () => {
    const deleted: string[] = [];
    vi.stubGlobal("caches", {
      keys: async () => ["workbox-precache-v2", "runtime"],
      delete: async (k: string) => {
        deleted.push(`cache:${k}`);
        return true;
      },
    });
    vi.stubGlobal("indexedDB", {
      databases: async () => [{ name: "rs-db" }],
      deleteDatabase: (name: string) => {
        deleted.push(`idb:${name}`);
        const req: Record<string, unknown> = {};
        setTimeout(() => (req.onsuccess as () => void)(), 0);
        return req;
      },
    });
    globalThis.localStorage.setItem("x", "1");
    await clearClientState();
    expect(deleted).toEqual(
      expect.arrayContaining(["cache:workbox-precache-v2", "cache:runtime", "idb:rs-db"]),
    );
    expect(globalThis.localStorage.length).toBe(0);
  });
});

describe("idle lock", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("fires after 5 minutes without activity, and activity postpones it", () => {
    const onIdle = vi.fn();
    const target = new EventTarget() as unknown as Window;
    const stop = startIdleTimer(onIdle, 5 * 60 * 1000, target);
    vi.advanceTimersByTime(4 * 60 * 1000);
    target.dispatchEvent(new Event("keydown"));
    vi.advanceTimersByTime(4 * 60 * 1000);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(61 * 1000);
    expect(onIdle).toHaveBeenCalledOnce();
    stop();
  });
});

describe("push payload", () => {
  it("keeps only generic text", () => {
    expect(sanitizePush({ body: "New alert, priority: critical" }).body).toBe(
      "New alert, priority: critical",
    );
    for (const bad of [
      { body: "Plate B123ABC on A1 km 23" },
      { body: "New alert, priority: <img src=x>" },
      { body: 42 },
      null,
    ]) {
      expect(sanitizePush(bad).body).toBe("New alert. Open RoadSentinel for details.");
    }
    expect(Object.keys(sanitizePush({ image: "x", body: "y" }))).toEqual(["title", "body", "url"]);
  });
});
