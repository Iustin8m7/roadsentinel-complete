import { useCallback, useEffect, useMemo, useState } from "react";

import { get } from "../api/client";
import type { AuditEntry, AuditVerify } from "../api/types";
import { Banner, Field, fmtDateTime, usePageTitle } from "../ui";

export function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [verify, setVerify] = useState<AuditVerify | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  usePageTitle("Jurnal de audit");

  const load = useCallback(async () => {
    try {
      setEntries(await get<AuditEntry[]>("/api/audit/chain?limit=200"));
      setError(null);
    } catch {
      setError("Jurnalul nu a putut fi încărcat.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  async function runVerify() {
    setBusy(true);
    setError(null);
    try {
      setVerify(await get<AuditVerify>("/api/audit/verify"));
      await load();
    } catch {
      setError("Verificarea nu a putut fi efectuată.");
    } finally {
      setBusy(false);
    }
  }

  const actions = useMemo(
    () => [...new Set((entries ?? []).map((e) => e.action))].sort(),
    [entries],
  );
  const shown = (entries ?? []).filter(
    (e) =>
      (!action || e.action === action) && (!actor || (e.actor_id ?? "").startsWith(actor.trim())),
  );

  return (
    <section aria-labelledby="audit-h">
      <h1 id="audit-h">Jurnal de audit</h1>
      <p className="muted">Ultimele {entries?.length ?? 0} înregistrări, ora Europa/București.</p>
      <div className="actions">
        <button onClick={() => void runVerify()} disabled={busy}>
          {busy ? "Se verifică…" : "Verifică integritatea"}
        </button>
      </div>
      {verify &&
        (verify.ok ? (
          <Banner tone="ok">
            Lanț intact: {verify.checked} înregistrări verificate.
            {verify.head_hash && (
              <>
                {" "}
                Hash final: <code>{verify.head_hash.slice(0, 16)}…</code>
              </>
            )}
          </Banner>
        ) : (
          <Banner tone="error">
            Alterare detectată la înregistrarea #{verify.first_broken_seq} ({verify.reason}).
          </Banner>
        ))}
      {error && <Banner tone="error">{error}</Banner>}
      <div className="filters">
        <Field label="Acțiune">
          {(id) => (
            <select id={id} value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="">Toate</option>
              {actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Autor (început de identificator)">
          {(id) => <input id={id} value={actor} onChange={(e) => setActor(e.target.value)} />}
        </Field>
      </div>
      {entries === null && !error ? (
        <p className="muted" role="status">
          Se încarcă…
        </p>
      ) : (
        <table className="audit cards">
          <caption className="sr-only">Lanțul de audit</caption>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Ora</th>
              <th scope="col">Acțiune</th>
              <th scope="col">Autor</th>
              <th scope="col">Resursă</th>
              <th scope="col">IP</th>
              <th scope="col">Detalii</th>
              <th scope="col">Hash</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <tr
                key={e.seq}
                className={
                  verify && !verify.ok && verify.first_broken_seq === e.seq ? "broken" : ""
                }
              >
                <td>
                  <strong>#{e.seq}</strong>
                </td>
                <td data-label="Ora">{fmtDateTime(e.ts)}</td>
                <td data-label="Acțiune">{e.action}</td>
                <td data-label="Autor">
                  <code>{e.actor_id?.slice(0, 8) ?? "-"}</code>
                </td>
                <td data-label="Resursă">
                  {e.resource_type} <code>{e.resource_id?.slice(0, 8)}</code>
                </td>
                <td data-label="IP">{e.ip ?? "-"}</td>
                <td className="wrap" data-label="Detalii">
                  <code>{JSON.stringify(e.details)}</code>
                </td>
                <td data-label="Hash">
                  <code title={e.entry_hash}>{e.entry_hash.slice(0, 10)}…</code>
                </td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">
                  Nicio înregistrare pentru filtrele alese.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
