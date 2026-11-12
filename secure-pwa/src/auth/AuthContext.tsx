import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

import { ApiError, del, get, onSessionExpired, post } from "../api/client";
import type { Me } from "../api/types";
import { clearClientState } from "./cleanup";
import { startIdleTimer } from "./idle";

type Status = "loading" | "anonymous" | "authenticated";

interface AuthState {
  status: Status;
  me: Me | null;
  locked: boolean;
  reauthOpen: boolean;
  reload: () => Promise<void>;
  logout: (reason?: string) => Promise<void>;
  unlock: (code: string) => Promise<void>;
  /** Run a sensitive action; if the API asks for fresh MFA, prompt and retry once. */
  withReauth: <T>(action: () => Promise<T>) => Promise<T>;
  submitReauth: (code: string) => Promise<void>;
  cancelReauth: () => void;
  can: (permission: string) => boolean;
  notice: string | null;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [locked, setLocked] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [reauthOpen, setReauthOpen] = useState(false);
  const pending = useRef<{ resolve: () => void; reject: (e: unknown) => void } | null>(null);

  const reload = useCallback(async () => {
    try {
      setMe(await get<Me>("/api/auth/me"));
      setStatus("authenticated");
      setNotice(null);
    } catch {
      setMe(null);
      setStatus("anonymous");
    }
  }, []);

  const logout = useCallback(async (reason?: string) => {
    try {
      // Server side: drop this user's push subscriptions, then revoke the session.
      await del("/api/push/subscriptions").catch(() => undefined);
      await post("/api/auth/logout");
    } catch {
      /* session may already be gone */
    }
    await clearClientState();
    setMe(null);
    setLocked(false);
    setStatus("anonymous");
    setNotice(reason ?? null);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  // Session expired or revoked elsewhere: wipe local state immediately.
  useEffect(
    () =>
      onSessionExpired(() => {
        void clearClientState();
        setMe(null);
        setStatus("anonymous");
        setNotice("Your session ended. Please sign in again.");
      }),
    [],
  );

  // Idle lock after 5 minutes without activity.
  useEffect(() => {
    if (status !== "authenticated" || locked) return;
    return startIdleTimer(() => setLocked(true));
  }, [status, locked]);

  const unlock = useCallback(async (code: string) => {
    await post("/api/auth/reauth", { code });
    setLocked(false);
  }, []);

  const submitReauth = useCallback(async (code: string) => {
    await post("/api/auth/reauth", { code });
    setReauthOpen(false);
    pending.current?.resolve();
    pending.current = null;
  }, []);

  const cancelReauth = useCallback(() => {
    setReauthOpen(false);
    pending.current?.reject(new Error("Re-authentication cancelled"));
    pending.current = null;
  }, []);

  const withReauth = useCallback(async <T,>(action: () => Promise<T>): Promise<T> => {
    try {
      return await action();
    } catch (err) {
      if (!(err instanceof ApiError && err.reauthRequired)) throw err;
      await new Promise<void>((resolve, reject) => {
        pending.current = { resolve, reject };
        setReauthOpen(true);
      });
      return action();
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      status,
      me,
      locked,
      reauthOpen,
      reload,
      logout,
      unlock,
      withReauth,
      submitReauth,
      cancelReauth,
      can: (p: string) => !!me?.permissions.includes(p),
      notice,
    }),
    [
      status,
      me,
      locked,
      reauthOpen,
      reload,
      logout,
      unlock,
      withReauth,
      submitReauth,
      cancelReauth,
      notice,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
