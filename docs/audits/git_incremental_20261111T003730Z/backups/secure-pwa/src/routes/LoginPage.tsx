import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { ApiError, post } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { MfaEnrollment } from "../components/MfaEnrollment";
import { Banner, Field, OtpInput, usePageTitle } from "../ui";

type Step = "password" | "mfa" | "enroll";

export function LoginPage() {
  const { status, reload, notice } = useAuth();
  const [step, setStep] = useState<Step>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const codeRef = useRef<HTMLInputElement>(null);
  usePageTitle("Autentificare");
  useEffect(() => {
    if (step === "mfa") codeRef.current?.focus();
  }, [step, useRecovery]);

  if (status === "authenticated") return <Navigate to="/alerts" replace />;

  const fail = (err: unknown) =>
    setError(
      err instanceof ApiError && err.status === 429
        ? "Prea multe încercări. Așteptați câteva minute și încercați din nou."
        : "Autentificarea a eșuat. Verificați datele și încercați din nou.",
    );

  async function submitPassword(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ enrollment_required: boolean }>("/api/auth/login", {
        email,
        password,
      });
      setPassword("");
      setStep(r.enrollment_required ? "enroll" : "mfa");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function submitMfa(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/api/auth/mfa/verify", useRecovery ? { recovery_code: code } : { code });
      await reload();
    } catch (err) {
      setCode("");
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-card">
      <h1>RoadSentinel</h1>
      <p className="muted">
        Sistem cu acces restricționat, doar pentru personal autorizat. Accesul este înregistrat.
      </p>
      {notice && <Banner>{notice}</Banner>}
      {error && <Banner tone="error">{error}</Banner>}

      {step === "password" && (
        <form onSubmit={submitPassword}>
          <Field label="E-mail">
            {(id) => (
              <input
                id={id}
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            )}
          </Field>
          <Field label="Parolă">
            {(id) => (
              <input
                id={id}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Field>
          <button disabled={busy}>{busy ? "Se verifică…" : "Continuă"}</button>
        </form>
      )}

      {step === "mfa" && (
        <form onSubmit={submitMfa}>
          <Field
            label={useRecovery ? "Cod de recuperare" : "Cod din aplicația de autentificare"}
            hint={
              useRecovery
                ? "Fiecare cod de recuperare poate fi folosit o singură dată."
                : "Cod cu 6 cifre."
            }
          >
            {(id, d) =>
              useRecovery ? (
                <input
                  id={id}
                  aria-describedby={d}
                  ref={codeRef}
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              ) : (
                <OtpInput
                  id={id}
                  aria-describedby={d}
                  ref={codeRef}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                />
              )
            }
          </Field>
          <button disabled={busy}>{busy ? "Se verifică…" : "Verifică"}</button>
          <button
            type="button"
            className="link"
            onClick={() => {
              setUseRecovery(!useRecovery);
              setCode("");
              setError(null);
            }}
          >
            {useRecovery ? "Folosesc codul din aplicație" : "Folosesc un cod de recuperare"}
          </button>
        </form>
      )}

      {step === "enroll" && <MfaEnrollment onDone={reload} />}
    </div>
  );
}
