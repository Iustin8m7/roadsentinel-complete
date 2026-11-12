import { useCallback, useEffect, useState } from "react";

import { ApiError, get, post } from "../api/client";
import type { Approval } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import {
  Banner,
  ConfirmDialog,
  KIND_LABEL,
  STATUS_LABEL,
  fmtDateTime,
  fmtTime,
  usePageTitle,
} from "../ui";

type Act = "approve" | "deny" | "revoke";
const ACT_TEXT: Record<Act, { title: string; button: string; body: string; danger: boolean }> = {
  approve: {
    title: "Aprobați cererea?",
    button: "Aprobă",
    body: "Solicitantul primește acces temporar la dovadă. Fiecare vizualizare este înregistrată în audit. Veți fi rugat să confirmați cu un cod.",
    danger: false,
  },
  deny: {
    title: "Refuzați cererea?",
    button: "Refuză",
    body: "Cererea este închisă și solicitantul nu primește acces.",
    danger: true,
  },
  revoke: {
    title: "Revocați accesul?",
    button: "Revocă",
    body: "Accesul acordat încetează imediat.",
    danger: true,
  },
};

export function ApprovalsPage() {
  const { me, can, withReauth } = useAuth();
  const [items, setItems] = useState<Approval[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [asking, setAsking] = useState<{ id: string; act: Act } | null>(null);
  const [busy, setBusy] = useState(false);
  const [actError, setActError] = useState<string | null>(null);
  const [tab, setTab] = useState<"pending" | "history">("pending");
  usePageTitle("Aprobări");

  const load = useCallback(async () => {
    try {
      setItems(await get<Approval[]>("/api/approvals"));
      setMessage(null);
    } catch {
      setMessage("Cererile nu au putut fi încărcate.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  async function run() {
    if (!asking) return;
    setBusy(true);
    setActError(null);
    try {
      await withReauth(() => post(`/api/approvals/${asking.id}/${asking.act}`));
      setAsking(null);
      await load();
    } catch (err) {
      setActError(
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : "Acțiunea nu a putut fi efectuată.",
      );
    } finally {
      setBusy(false);
    }
  }

  const pending = (items ?? []).filter((r) => r.status === "pending" || r.grant_active);
  const history = (items ?? []).filter((r) => !(r.status === "pending" || r.grant_active));
  const rows = tab === "pending" ? pending : history;

  return (
    <section aria-labelledby="appr-h">
      <h1 id="appr-h">
        {can("approvals:decide") ? "Cereri de aprobare" : "Cererile mele de acces"}
      </h1>
      <p className="muted">
        Regula celor doi ochi: o cerere trebuie aprobată de un alt administrator. Fiecare
        vizualizare este înregistrată în audit.
      </p>
      {message && <Banner tone="error">{message}</Banner>}
      <div className="actions" role="group" aria-label="Filtru cereri">
        <button
          className={tab === "pending" ? "" : "secondary"}
          aria-pressed={tab === "pending"}
          onClick={() => setTab("pending")}
        >
          Active ({pending.length})
        </button>
        <button
          className={tab === "history" ? "" : "secondary"}
          aria-pressed={tab === "history"}
          onClick={() => setTab("history")}
        >
          Istoric ({history.length})
        </button>
      </div>
      {items === null && !message ? (
        <p className="muted" role="status">
          Se încarcă…
        </p>
      ) : (
        <table className="cards">
          <caption className="sr-only">Cereri de acces la dovezi</caption>
          <thead>
            <tr>
              <th scope="col">Tip</th>
              <th scope="col">Caz</th>
              <th scope="col">Justificare</th>
              <th scope="col">Stare</th>
              <th scope="col">Acces acordat</th>
              <th scope="col">
                <span className="sr-only">Acțiuni</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const own = r.requester_id === me?.id;
              return (
                <tr key={r.id}>
                  <td>{KIND_LABEL[r.kind] ?? r.kind}</td>
                  <td data-label="Caz">{r.case_reference}</td>
                  <td className="wrap" data-label="Justificare">
                    {r.justification}
                  </td>
                  <td data-label="Stare">{STATUS_LABEL[r.status] ?? r.status}</td>
                  <td data-label="Acces">
                    {r.grant_active && r.grant_expires_at
                      ? `până la ${fmtTime(r.grant_expires_at)} (${fmtDateTime(r.grant_expires_at).slice(0, 10)})`
                      : "-"}
                  </td>
                  <td className="actions">
                    {can("approvals:decide") && r.status === "pending" && !own && (
                      <>
                        <button onClick={() => setAsking({ id: r.id, act: "approve" })}>
                          Aprobă
                        </button>
                        <button
                          className="reject"
                          onClick={() => setAsking({ id: r.id, act: "deny" })}
                        >
                          Refuză
                        </button>
                      </>
                    )}
                    {can("approvals:decide") && r.status === "pending" && own && (
                      <span className="muted">Necesită un alt administrator</span>
                    )}
                    {r.grant_active && (can("approvals:decide") || own) && (
                      <button
                        className="reject"
                        onClick={() => setAsking({ id: r.id, act: "revoke" })}
                      >
                        Revocă
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  {tab === "pending" ? "Nicio cerere activă." : "Niciun istoric."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {asking && (
        <ConfirmDialog
          title={ACT_TEXT[asking.act].title}
          confirmLabel={ACT_TEXT[asking.act].button}
          danger={ACT_TEXT[asking.act].danger}
          busy={busy}
          error={actError}
          onConfirm={() => void run()}
          onCancel={() => {
            setAsking(null);
            setActError(null);
          }}
        >
          {ACT_TEXT[asking.act].body}
        </ConfirmDialog>
      )}
    </section>
  );
}
