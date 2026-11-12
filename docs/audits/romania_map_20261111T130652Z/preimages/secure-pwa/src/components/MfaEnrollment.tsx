import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { post } from "../api/client";
import { Banner, Field, OtpInput } from "../ui";

interface EnrollStart {
  otpauth_uri: string;
  qr_svg_data_uri: string;
  secret: string;
}

/** Mandatory TOTP enrollment (first login / invitation). Recovery codes are shown exactly once. */
export function MfaEnrollment({ onDone }: { onDone: () => Promise<void> }) {
  const [start, setStart] = useState<EnrollStart | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    post<EnrollStart>("/api/auth/mfa/enroll/start")
      .then(setStart)
      .catch(() => setError("Sesiunea de configurare a expirat. Autentificați-vă din nou."));
  }, []);

  async function confirm(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await post<{ recovery_codes: string[] }>("/api/auth/mfa/enroll/confirm", { code });
      setCodes(r.recovery_codes);
      setStart(null);
    } catch {
      setCode("");
      setError("Codul nu corespunde. Așteptați următorul cod și încercați din nou.");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText((codes ?? []).join("\n"));
      setCopied("Codurile au fost copiate. Lipiți-le într-un loc sigur și goliți clipboardul.");
    } catch {
      setCopied("Copierea nu este disponibilă pe acest dispozitiv. Notați codurile manual.");
    }
  }

  if (codes) {
    return (
      <section className="stack" aria-labelledby="rc-t">
        <h2 id="rc-t">Salvați codurile de recuperare</h2>
        <Banner tone="warn">
          Fiecare cod funcționează o singură dată dacă pierdeți telefonul. Nu vor mai fi afișate
          după ce părăsiți acest ecran.
        </Banner>
        <ul className="codes">
          {codes.map((c) => (
            <li key={c}>
              <code>{c}</code>
            </li>
          ))}
        </ul>
        <div className="actions no-print">
          <button type="button" className="secondary" onClick={() => void copy()}>
            Copiază codurile
          </button>
          <button type="button" className="secondary" onClick={() => window.print()}>
            Tipărește
          </button>
        </div>
        {copied && <Banner>{copied}</Banner>}
        <label className="check no-print">
          <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
          Am păstrat codurile într-un loc sigur
        </label>
        <button className="no-print" disabled={!saved} onClick={() => void onDone()}>
          Continuă
        </button>
      </section>
    );
  }

  return (
    <section className="stack" aria-labelledby="mfa-t">
      <h2 id="mfa-t">Configurați autentificarea în doi pași</h2>
      {error && <Banner tone="error">{error}</Banner>}
      {start && (
        <>
          <p>
            Scanați codul QR cu o aplicație de autentificare, apoi introduceți codul de 6 cifre.
          </p>
          <img
            className="qr"
            src={start.qr_svg_data_uri}
            alt="Cod QR pentru configurarea aplicației de autentificare"
          />
          <details>
            <summary>Nu puteți scana? Introduceți cheia manual</summary>
            <code className="secret">{start.secret}</code>
          </details>
          <form onSubmit={confirm}>
            <Field label="Cod din aplicație" hint="Cod cu 6 cifre.">
              {(id, d) => (
                <OtpInput
                  id={id}
                  aria-describedby={d}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                />
              )}
            </Field>
            <button disabled={busy}>{busy ? "Se verifică…" : "Activează"}</button>
          </form>
        </>
      )}
    </section>
  );
}
