import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError, post } from "../api/client";
import { Banner, Field, usePageTitle } from "../ui";

interface ResetInfo {
  email: string;
  reset_mfa: boolean;
  expires_at: string;
}

/** Account recovery with a single-use token handed over by a tenant admin. The token is read from
 *  the URL fragment (never sent to servers) and removed from the address bar immediately. */
export function ResetPage() {
  usePageTitle("Recuperare cont");
  const [token] = useState(() => window.location.hash.slice(1));
  const [info, setInfo] = useState<ResetInfo | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [done, setDone] = useState(false);

  useEffect(() => {
    history.replaceState(null, "", window.location.pathname);
    if (!token) {
      setErrors(["Lipsește token-ul de recuperare."]);
      return;
    }
    post<ResetInfo>("/api/auth/reset/inspect", { token })
      .then(setInfo)
      .catch(() => setErrors(["Token-ul este invalid, a fost folosit sau a expirat."]));
  }, [token]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErrors(["Parolele nu coincid."]);
      return;
    }
    try {
      await post("/api/auth/reset/accept", { token, password });
      setPassword("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      setErrors(
        err instanceof ApiError && Array.isArray(err.detail) && typeof err.detail[0] === "string"
          ? (err.detail as string[])
          : ["Parola nu a putut fi schimbată. Cereți un token nou."],
      );
    }
  }

  if (done) {
    return (
      <section className="card">
        <h1>Parola a fost schimbată</h1>
        <Banner tone="ok">
          Toate sesiunile anterioare au fost închise.
          {info?.reset_mfa
            ? " Autentificarea în doi pași a fost resetată: la prima conectare va trebui configurată din nou."
            : " Autentificarea în doi pași rămâne activă."}
        </Banner>
        <p>
          <Link to="/login">Conectare</Link>
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h1>Recuperare cont</h1>
      {info && (
        <p className="muted">
          Cont: <strong>{info.email}</strong>. Alegeți o parolă nouă (minimum 12 caractere).
        </p>
      )}
      {errors.map((m) => (
        <Banner key={m} tone="error">
          {m}
        </Banner>
      ))}
      {info && (
        <form onSubmit={submit}>
          <Field label="Parolă nouă">
            {(id) => (
              <input
                id={id}
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Field>
          <Field label="Repetați parola">
            {(id) => (
              <input
                id={id}
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            )}
          </Field>
          <button>Schimbă parola</button>
        </form>
      )}
    </section>
  );
}
