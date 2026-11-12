import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, post } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { MfaEnrollment } from "../components/MfaEnrollment";
import { Banner, Field, ROLE_LABEL, usePageTitle } from "../ui";

interface InviteInfo {
  email: string;
  role: string;
  tenant_name: string;
  expires_at: string;
}

/** Invitation acceptance. The token travels in the URL fragment (#...), which browsers never
 *  send to servers or put in Referer headers; it is removed from the address bar immediately. */
export function InvitePage() {
  const { reload } = useAuth();
  usePageTitle("Invitație");
  const [token] = useState(() => window.location.hash.slice(1));
  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [enroll, setEnroll] = useState(false);

  useEffect(() => {
    history.replaceState(null, "", window.location.pathname);
    if (!token) {
      setErrors(["Lipsește token-ul invitației."]);
      return;
    }
    post<InviteInfo>("/api/auth/invitations/inspect", { token })
      .then(setInfo)
      .catch(() => setErrors(["Invitația este invalidă sau a expirat."]));
  }, [token]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErrors(["Parolele nu coincid."]);
      return;
    }
    try {
      await post("/api/auth/invitations/accept", { token, display_name: name, password });
      setPassword("");
      setConfirm("");
      setEnroll(true);
    } catch (err) {
      setErrors(
        err instanceof ApiError && Array.isArray(err.detail) && typeof err.detail[0] === "string"
          ? (err.detail as string[])
          : ["Invitația nu a putut fi acceptată."],
      );
    }
  }

  return (
    <div className="auth-card">
      <h1>Alăturați-vă la RoadSentinel</h1>
      {errors.map((m) => (
        <Banner key={m} tone="error">
          {m}
        </Banner>
      ))}
      {enroll ? (
        <MfaEnrollment onDone={reload} />
      ) : (
        info && (
          <form onSubmit={submit}>
            <p>
              <strong>{info.tenant_name}</strong> a invitat <strong>{info.email}</strong> cu rolul{" "}
              <em>{ROLE_LABEL[info.role] ?? info.role}</em>.
            </p>
            <Field label="Nume afișat">
              {(id) => (
                <input
                  id={id}
                  required
                  minLength={2}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              )}
            </Field>
            <Field label="Parolă" hint="Cel puțin 12 caractere.">
              {(id, d) => (
                <input
                  id={id}
                  aria-describedby={d}
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
            <button>Creează contul</button>
          </form>
        )
      )}
    </div>
  );
}
