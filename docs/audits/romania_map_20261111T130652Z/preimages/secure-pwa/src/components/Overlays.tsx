import { useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "../auth/AuthContext";
import { Banner, Dialog, Field, OtpInput } from "../ui";

function CodeForm({ onSubmit }: { onSubmit: (code: string) => Promise<void> }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(code);
    } catch {
      setError("Cod incorect sau expirat. Așteptați următorul cod și încercați din nou.");
    } finally {
      setCode("");
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      {error && <Banner tone="error">{error}</Banner>}
      <Field label="Cod din aplicația de autentificare" hint="Cod cu 6 cifre.">
        {(id, d) => (
          <OtpInput
            id={id}
            aria-describedby={d}
            autoFocus
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
        )}
      </Field>
      <button disabled={busy}>{busy ? "Se verifică…" : "Confirmă"}</button>
    </form>
  );
}

/** Full-screen lock after 5 minutes idle: hides all content until a fresh code is entered. */
export function LockScreen() {
  const { unlock, logout, me } = useAuth();
  return (
    <div className="overlay opaque" role="dialog" aria-modal="true" aria-labelledby="lock-t">
      <div className="auth-card">
        <h2 id="lock-t">Sesiune blocată</h2>
        <p className="muted">Blocată după 5 minute de inactivitate. {me?.email}</p>
        <CodeForm onSubmit={unlock} />
        <p className="hint">
          Nu aveți codul la îndemână? Deconectați-vă și autentificați-vă din nou cu un cod de
          recuperare.
        </p>
        <button className="link" onClick={() => void logout()}>
          Deconectare
        </button>
      </div>
    </div>
  );
}

/** Step-up prompt for sensitive actions (approve unblur, export, manage users). */
export function ReauthDialog() {
  const { submitReauth, cancelReauth } = useAuth();
  return (
    <Dialog title="Confirmați identitatea" onClose={cancelReauth}>
      <p className="muted">Această acțiune cere o verificare în doi pași recentă.</p>
      <CodeForm onSubmit={submitReauth} />
      <button className="link" onClick={cancelReauth}>
        Anulează
      </button>
    </Dialog>
  );
}
