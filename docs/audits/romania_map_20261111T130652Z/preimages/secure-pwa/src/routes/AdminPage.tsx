import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, get, post, api } from "../api/client";
import type { Approval, PurgeResult, RetentionState, UserRow } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Banner, ConfirmDialog, Field, fmtDateTime, usePageTitle } from "../ui";

const KIND_NAMES: Record<string, string> = {
  keyframe: "Cadru cheie (zile)",
  clip: "Clip video (zile)",
  camera_video: "Înregistrare cameră (zile)",
  confirmed_case: "Caz confirmat (zile)",
};

function detail(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === "string") return err.detail;
    if (Array.isArray(err.detail) && typeof err.detail[0] === "string")
      return err.detail[0] as string;
  }
  return fallback;
}

function Retention() {
  const [state, setState] = useState<RetentionState | null>(null);
  const [days, setDays] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PurgeResult | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [typed, setTyped] = useState("");
  const { withReauth } = useAuth();

  const load = useCallback(async () => {
    const s = await get<RetentionState>("/api/retention");
    setState(s);
    setDays(Object.fromEntries(Object.entries(s.days).map(([k, v]) => [k, String(v)])));
  }, []);
  useEffect(() => {
    void load().catch(() => setMsg({ tone: "error", text: "Politica nu a putut fi încărcată." }));
  }, [load]);

  async function save(e: FormEvent) {
    e.preventDefault();
    try {
      const body = Object.fromEntries(Object.entries(days).map(([k, v]) => [k, Number(v)]));
      const s = await withReauth(() =>
        api<RetentionState>("PUT", "/api/retention", { days: body }),
      );
      setState(s);
      setMsg({ tone: "ok", text: "Politica a fost salvată și înregistrată în audit." });
    } catch (err) {
      setMsg({ tone: "error", text: detail(err, "Politica nu a putut fi salvată.") });
    }
  }
  async function purge(dry: boolean) {
    try {
      const r = await withReauth(() =>
        post<PurgeResult>(
          "/api/retention/purge",
          dry ? { dry_run: true } : { dry_run: false, confirm: "PURGE" },
        ),
      );
      setResult(r);
      setConfirm(false);
      setTyped("");
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: detail(err, "Operațiunea a eșuat.") });
    }
  }

  return (
    <section className="card">
      <h2>Retenția dovezilor</h2>
      <p className="muted">
        Fișierele mai vechi decât politica sunt șterse definitiv; alerta, hash-ul și jurnalul de
        audit rămân. Alertele sub blocare legală nu sunt șterse niciodată.
      </p>
      {msg && <Banner tone={msg.tone}>{msg.text}</Banner>}
      {state && (
        <form onSubmit={save}>
          {Object.keys(KIND_NAMES).map((k) => (
            <Field key={k} label={KIND_NAMES[k]} hint={`Implicit: ${state.defaults[k]} zile`}>
              {(id, d) => (
                <input
                  id={id}
                  aria-describedby={d}
                  type="number"
                  min={1}
                  max={3650}
                  required
                  value={days[k] ?? ""}
                  onChange={(e) => setDays({ ...days, [k]: e.target.value })}
                />
              )}
            </Field>
          ))}
          <div className="actions">
            <button>Salvează politica</button>
            <button type="button" className="secondary" onClick={() => void purge(true)}>
              Simulare ștergere (dry-run)
            </button>
            <button type="button" className="danger" onClick={() => setConfirm(true)}>
              Șterge acum
            </button>
          </div>
          <p className="muted">
            Scadente acum: <strong>{state.due_now}</strong>. Omise (blocare legală):{" "}
            {state.held_skipped}.
          </p>
        </form>
      )}
      {result && (
        <Banner tone={result.dry_run ? "info" : "ok"}>
          {result.dry_run ? "Simulare: " : "Executat: "}
          {result.candidates} candidați, {result.purged} șterse, {result.held_skipped} omise,{" "}
          {result.errors} erori.
        </Banner>
      )}
      {confirm && (
        <ConfirmDialog
          title="Ștergeți definitiv dovezile scadente?"
          confirmLabel="Șterge definitiv"
          danger
          onConfirm={() => typed === "PURGE" && void purge(false)}
          onCancel={() => {
            setConfirm(false);
            setTyped("");
          }}
        >
          <p>Operațiunea nu poate fi anulată. Scrieți PURGE pentru confirmare.</p>
          <Field label="Confirmare">
            {(id) => (
              <input
                id={id}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoComplete="off"
              />
            )}
          </Field>
        </ConfirmDialog>
      )}
    </section>
  );
}

function Recovery() {
  const { me, withReauth } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [target, setTarget] = useState("");
  const [resetMfa, setResetMfa] = useState(false);
  const [why, setWhy] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [issued, setIssued] = useState<{ token: string; expires_at: string } | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setUsers(await get<UserRow[]>("/api/users"));
    setApprovals(await get<Approval[]>("/api/approvals"));
  }, []);
  useEffect(() => {
    void load().catch(() => setMsg({ tone: "error", text: "Lista nu a putut fi încărcată." }));
  }, [load]);

  async function request(e: FormEvent) {
    e.preventDefault();
    try {
      await withReauth(() =>
        post(`/api/users/${target}/reset-requests`, {
          reset_mfa: resetMfa,
          justification: why,
          case_reference: caseRef,
        }),
      );
      setMsg({
        tone: "ok",
        text: "Cererea a fost trimisă. Un alt administrator trebuie să o aprobe în „Aprobări”.",
      });
      setWhy("");
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: detail(err, "Cererea nu a putut fi trimisă.") });
    }
  }
  async function issue(id: string) {
    try {
      setIssued(
        await withReauth(() =>
          post<{ token: string; expires_at: string }>(`/api/users/reset-requests/${id}/issue`),
        ),
      );
      await load();
    } catch (err) {
      setMsg({ tone: "error", text: detail(err, "Token-ul nu a putut fi emis.") });
    }
  }

  const mine = approvals.filter(
    (a) =>
      a.kind === "account_reset" &&
      a.requester_id === me?.id &&
      a.status === "approved" &&
      a.grant_active,
  );
  const emailOf = (id: string) => users.find((u) => u.id === id)?.email ?? id;

  return (
    <section className="card">
      <h2>Recuperare cont (regula celor doi ochi)</h2>
      <p className="muted">
        Cererea trebuie aprobată de un alt administrator. După aprobare, solicitantul emite un token
        de unică folosință și îl predă utilizatorului. Autentificarea în doi pași rămâne
        obligatorie.
      </p>
      {msg && <Banner tone={msg.tone}>{msg.text}</Banner>}
      <form onSubmit={request}>
        <Field label="Cont">
          {(id) => (
            <select id={id} required value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="">Alegeți…</option>
              {users
                .filter((u) => u.id !== me?.id && u.is_active)
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name} ({u.email})
                  </option>
                ))}
            </select>
          )}
        </Field>
        <label className="check">
          <input
            type="checkbox"
            checked={resetMfa}
            onChange={(e) => setResetMfa(e.target.checked)}
          />{" "}
          A pierdut dispozitivul de autentificare (se resetează și 2FA)
        </label>
        <Field label="Referință de caz">
          {(id) => (
            <input
              id={id}
              required
              minLength={3}
              value={caseRef}
              onChange={(e) => setCaseRef(e.target.value)}
            />
          )}
        </Field>
        <Field
          label="Justificare scrisă"
          hint="Cel puțin 20 de caractere (cum a fost verificată identitatea)."
        >
          {(id, d) => (
            <textarea
              id={id}
              aria-describedby={d}
              required
              minLength={20}
              value={why}
              onChange={(e) => setWhy(e.target.value)}
            />
          )}
        </Field>
        <button>Trimite cererea</button>
      </form>
      {mine.length > 0 && (
        <>
          <h3>Aprobate, gata de emis</h3>
          <ul>
            {mine.map((a) => (
              <li key={a.id}>
                {emailOf(a.resource_id)} · {a.case_reference} · valabil până la{" "}
                {a.grant_expires_at ? fmtDateTime(a.grant_expires_at) : "?"}{" "}
                <button type="button" onClick={() => void issue(a.id)}>
                  Emite token
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {issued && (
        <Banner tone="warn">
          Token (se afișează o singură dată, valabil până la {fmtDateTime(issued.expires_at)}).
          Predați-l utilizatorului pe o cale sigură; el deschide <code>/reset</code> și îl lipește
          în adresă ca <code>#token</code>:<br />
          <code>{issued.token}</code>
        </Banner>
      )}
    </section>
  );
}

function OwnPassword() {
  const { withReauth } = useAuth();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await withReauth(() =>
        post("/api/auth/password", { current_password: cur, new_password: next }),
      );
      setCur("");
      setNext("");
      setMsg({
        tone: "ok",
        text: "Parola a fost schimbată; celelalte dispozitive au fost deconectate.",
      });
    } catch (err) {
      setMsg({ tone: "error", text: detail(err, "Parola nu a putut fi schimbată.") });
    }
  }
  return (
    <section className="card">
      <h2>Parola mea</h2>
      {msg && <Banner tone={msg.tone}>{msg.text}</Banner>}
      <form onSubmit={submit}>
        <Field label="Parola actuală">
          {(id) => (
            <input
              id={id}
              type="password"
              autoComplete="current-password"
              required
              value={cur}
              onChange={(e) => setCur(e.target.value)}
            />
          )}
        </Field>
        <Field label="Parola nouă" hint="Minimum 12 caractere.">
          {(id, d) => (
            <input
              id={id}
              aria-describedby={d}
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          )}
        </Field>
        <button>Schimbă parola</button>
      </form>
    </section>
  );
}

export function AdminPage() {
  usePageTitle("Administrare");
  const { can } = useAuth();
  return (
    <>
      <h1>Administrare</h1>
      {can("retention:manage") && <Retention />}
      {can("users:manage") && can("approvals:request") && <Recovery />}
      <OwnPassword />
    </>
  );
}
