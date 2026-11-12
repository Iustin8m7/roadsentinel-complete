import { useCallback, useEffect, useState } from "react";

import { ApiError, del, get } from "../api/client";
import type { SessionInfo, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { enablePush, pushSupported } from "../pwa/push";
import { Banner, ConfirmDialog, Field, ROLE_LABEL, fmtDateTime, usePageTitle } from "../ui";

function SessionTable({
  sessions,
  onRevoke,
}: {
  sessions: SessionInfo[];
  onRevoke: (s: SessionInfo) => void;
}) {
  return (
    <table className="cards">
      <caption className="sr-only">Sesiuni</caption>
      <thead>
        <tr>
          <th scope="col">Dispozitiv</th>
          <th scope="col">IP</th>
          <th scope="col">Ultima activitate</th>
          <th scope="col">Stare</th>
          <th scope="col">
            <span className="sr-only">Acțiuni</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((s) => (
          <tr key={s.id}>
            <td className="wrap">
              {s.user_agent ?? "necunoscut"} {s.current && <strong>(acest dispozitiv)</strong>}
            </td>
            <td data-label="IP">{s.ip ?? "-"}</td>
            <td data-label="Ultima activitate">{fmtDateTime(s.last_seen_at)}</td>
            <td data-label="Stare">{s.revoked_at ? `revocată (${s.revoked_reason})` : "activă"}</td>
            <td>
              {!s.revoked_at && (
                <button className="reject" onClick={() => onRevoke(s)}>
                  Revocă
                </button>
              )}
            </td>
          </tr>
        ))}
        {sessions.length === 0 && (
          <tr>
            <td colSpan={5} className="muted">
              Nicio sesiune.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

export function SessionsPage() {
  const { can, logout, withReauth } = useAuth();
  const [mine, setMine] = useState<SessionInfo[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [theirs, setTheirs] = useState<SessionInfo[]>([]);
  const [pushState, setPushState] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState<{ s: SessionInfo; own: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const [actError, setActError] = useState<string | null>(null);
  usePageTitle("Sesiuni");

  const load = useCallback(async () => {
    try {
      setMine(await get<SessionInfo[]>("/api/sessions"));
      if (can("sessions:manage_all")) setUsers(await get<User[]>("/api/users"));
      setError(null);
    } catch {
      setError("Sesiunile nu au putut fi încărcate.");
    }
  }, [can]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selected)
      void get<SessionInfo[]>(`/api/users/${selected}/sessions`)
        .then(setTheirs)
        .catch(() => setError("Sesiunile utilizatorului nu au putut fi încărcate."));
  }, [selected]);

  async function confirmRevoke() {
    if (!asking) return;
    setBusy(true);
    setActError(null);
    try {
      if (asking.own) {
        if (asking.s.current) {
          await logout("Ați revocat acest dispozitiv.");
          return;
        }
        await del(`/api/sessions/${asking.s.id}`);
        await load();
      } else {
        await withReauth(() => del(`/api/users/${asking.s.user_id}/sessions/${asking.s.id}`));
        setTheirs(await get<SessionInfo[]>(`/api/users/${asking.s.user_id}/sessions`));
      }
      setAsking(null);
    } catch (err) {
      setActError(
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : "Sesiunea nu a putut fi revocată.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="sess-h">
      <h1 id="sess-h">Sesiuni active</h1>
      {error && <Banner tone="error">{error}</Banner>}
      <SessionTable sessions={mine} onRevoke={(s) => setAsking({ s, own: true })} />
      {pushSupported() && can("push:subscribe") && (
        <div className="stack">
          <h2>Notificări</h2>
          <p className="muted">
            Notificările push apar pe ecranul dispozitivului și pot conține tipul alertei. Se pot
            dezactiva din setările browserului. La deconectare, abonarea acestui dispozitiv este
            ștearsă.
          </p>
          <div>
            <button className="secondary" onClick={() => void enablePush().then(setPushState)}>
              Activează notificările pe acest dispozitiv
            </button>
          </div>
          {pushState && <Banner>{pushState}</Banner>}
        </div>
      )}
      {can("sessions:manage_all") && (
        <>
          <h2>Dispozitivele utilizatorilor (administrator)</h2>
          <Field label="Utilizator">
            {(id) => (
              <select id={id} value={selected} onChange={(e) => setSelected(e.target.value)}>
                <option value="">Alegeți un utilizator…</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.email} ({ROLE_LABEL[u.role] ?? u.role})
                  </option>
                ))}
              </select>
            )}
          </Field>
          {selected && (
            <SessionTable sessions={theirs} onRevoke={(s) => setAsking({ s, own: false })} />
          )}
        </>
      )}
      {asking && (
        <ConfirmDialog
          title="Revocați sesiunea?"
          confirmLabel="Revocă"
          danger
          busy={busy}
          error={actError}
          onConfirm={() => void confirmRevoke()}
          onCancel={() => {
            setAsking(null);
            setActError(null);
          }}
        >
          {asking.own && asking.s.current
            ? "Veți fi deconectat de pe acest dispozitiv."
            : "Dispozitivul va fi deconectat imediat."}
        </ConfirmDialog>
      )}
    </section>
  );
}
