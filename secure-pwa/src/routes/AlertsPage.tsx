import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, get, post } from "../api/client";
import type { Alert, Approval, Evidence, Patrol, SignedUrl } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import {
  Banner,
  Chip,
  ConfirmDialog,
  Field,
  KIND_LABEL,
  PriorityBadge,
  STATUS_LABEL,
  fmtDateTime,
  redactionChipKind,
  usePageTitle,
} from "../ui";

export { PriorityBadge };

export function AlertsPage() {
  const { can } = useAuth();
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [plate, setPlate] = useState("");
  const [error, setError] = useState<string | null>(null);
  usePageTitle("Alerte");

  const load = useCallback(async (plateQuery?: string) => {
    try {
      const q = plateQuery ? `?plate=${encodeURIComponent(plateQuery)}` : "";
      setAlerts(await get<Alert[]>(`/api/alerts${q}`)); // server sorts by priority
      setError(null);
    } catch {
      setError("Alertele nu au putut fi încărcate.");
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 15000);
    return () => clearInterval(t);
  }, [load]);

  function search(e: FormEvent) {
    e.preventDefault();
    void load(plate.trim() || undefined);
  }

  return (
    <section aria-labelledby="alerts-h">
      <h1 id="alerts-h">Alerte</h1>
      {can("alerts:plate_search") && (
        <form className="inline" onSubmit={search} role="search">
          <Field label="Căutare exactă după număr de înmatriculare">
            {(id) => <input id={id} value={plate} onChange={(e) => setPlate(e.target.value)} />}
          </Field>
          <button>Caută</button>
        </form>
      )}
      {error && (
        <Banner tone="error">
          {error}{" "}
          <button type="button" className="link" onClick={() => void load()}>
            Reîncearcă
          </button>
        </Banner>
      )}
      {alerts === null && !error ? (
        <p className="muted" role="status">
          Se încarcă alertele…
        </p>
      ) : (
        <table className="cards">
          <caption className="sr-only">
            Alerte, ordonate după prioritate. Ora: Europa/București.
          </caption>
          <thead>
            <tr>
              <th scope="col">Prioritate</th>
              <th scope="col">Eveniment</th>
              <th scope="col">Cameră</th>
              <th scope="col">Număr (mascat)</th>
              <th scope="col">Detectat (Europa/București)</th>
              <th scope="col">Stare</th>
            </tr>
          </thead>
          <tbody>
            {(alerts ?? []).map((a) => (
              <tr key={a.id}>
                <td>
                  <PriorityBadge priority={a.priority} />
                </td>
                <td>
                  <Link to={`/alerts/${a.id}`}>{a.description}</Link>
                </td>
                <td data-label="Cameră">{a.camera_name}</td>
                <td data-label="Număr">
                  <code>{a.plate_masked ?? "-"}</code>
                </td>
                <td data-label="Detectat">{fmtDateTime(a.detected_at)}</td>
                <td data-label="Stare">{STATUS_LABEL[a.status] ?? a.status}</td>
              </tr>
            ))}
            {alerts?.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Nicio alertă.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}

function EvidencePanel({ evidence, onChange }: { evidence: Evidence; onChange: () => void }) {
  const { can, withReauth } = useAuth();
  const [src, setSrc] = useState<string | null>(null);
  const [variant, setVariant] = useState<"redacted" | "original">("redacted");
  const [justification, setJustification] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [kind, setKind] = useState<"unblur" | "export">("unblur");
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [confirmExport, setConfirmExport] = useState(false);
  const [busy, setBusy] = useState(false);

  const show = useCallback(
    async (v: "redacted" | "original") => {
      // Short-lived signed URL (60 s), bound to this user; fetched as a blob so it never sits in
      // the DOM or history longer than needed.
      const signed = await post<SignedUrl>(`/api/evidence/${evidence.id}/access`, { variant: v });
      const res = await fetch(signed.url, { credentials: "same-origin", cache: "no-store" });
      if (!res.ok) throw new Error("load failed");
      const blob = await res.blob();
      setSrc((old) => {
        if (old) URL.revokeObjectURL(old);
        return URL.createObjectURL(blob);
      });
      setVariant(v);
    },
    [evidence.id],
  );

  useEffect(() => {
    void show("redacted").catch(() =>
      setMessage({ tone: "error", text: "Dovada nu este disponibilă." }),
    );
  }, [show]);

  useEffect(
    () => () => {
      if (src) URL.revokeObjectURL(src);
    },
    [src],
  );

  async function requestApproval(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await post<Approval>("/api/approvals", {
        kind,
        evidence_id: evidence.id,
        justification,
        case_reference: caseRef,
      });
      setMessage({
        tone: "ok",
        text: `Cererea de ${kind === "unblur" ? "dezvăluire" : "export"} a fost trimisă. Trebuie aprobată de un alt administrator.`,
      });
      setJustification("");
      setCaseRef("");
    } catch (err) {
      setMessage({
        tone: "error",
        text:
          err instanceof ApiError && err.status === 422
            ? "Sunt necesare o justificare de cel puțin 20 de caractere și o referință de caz."
            : "Cererea nu a putut fi trimisă.",
      });
    } finally {
      setBusy(false);
    }
  }

  async function exportEvidence() {
    setBusy(true);
    try {
      const signed = await withReauth(() => post<SignedUrl>(`/api/evidence/${evidence.id}/export`));
      setConfirmExport(false);
      window.location.assign(signed.url);
    } catch {
      setConfirmExport(false);
      setMessage({ tone: "error", text: "Exportul necesită o cerere de export aprobată." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="evidence">
      <div className="actions">
        {variant === "redacted" ? (
          <Chip kind={redactionChipKind(evidence.redaction)} />
        ) : (
          <Chip kind="unredacted" />
        )}
      </div>
      {src && (
        <img src={src} alt={`Dovadă (${variant === "redacted" ? "redactată" : "originală"})`} />
      )}
      <p className="muted">
        {variant === "redacted"
          ? evidence.has_original
            ? "Varianta redactată automat. Redactarea este euristică și nu garantează ascunderea tuturor fețelor sau numerelor."
            : "Singura copie stocată, așa cum a trimis-o camera/pipeline-ul. Nu există o variantă originală distinctă. Redactarea (dacă există) este euristică."
          : "Varianta originală, fără redactare. Accesul este înregistrat în audit."}{" "}
        SHA-256 <code>{evidence.sha256.slice(0, 16)}…</code>
      </p>
      {!evidence.has_original ? (
        <p className="hint" role="note">
          Nu există o variantă originală distinctă: dezvăluirea și exportul originalului nu sunt
          disponibile pentru această dovadă.
        </p>
      ) : evidence.unblur_grant_expires_at ? (
        <p>
          Dezvăluire aprobată până la {fmtDateTime(evidence.unblur_grant_expires_at)}. Număr:{" "}
          <code>{evidence.plate}</code>{" "}
          <button
            className="secondary"
            onClick={() =>
              void show(variant === "redacted" ? "original" : "redacted").catch(() => onChange())
            }
          >
            {variant === "redacted" ? "Arată originalul" : "Arată varianta redactată"}
          </button>
        </p>
      ) : (
        can("approvals:request") && (
          <form onSubmit={requestApproval}>
            <h3>Solicită acces (regula celor doi ochi)</h3>
            <p className="hint">
              Dacă dovada nu are o variantă originală distinctă de cea redactată, aprobarea nu va
              dezvălui nimic suplimentar.
            </p>
            <Field label="Tip cerere">
              {(id) => (
                <select
                  id={id}
                  value={kind}
                  onChange={(e) => setKind(e.target.value as "unblur" | "export")}
                >
                  <option value="unblur">{KIND_LABEL.unblur}</option>
                  <option value="export">{KIND_LABEL.export}</option>
                </select>
              )}
            </Field>
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
            <Field label="Justificare scrisă" hint="Cel puțin 20 de caractere.">
              {(id, d) => (
                <textarea
                  id={id}
                  aria-describedby={d}
                  required
                  minLength={20}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                />
              )}
            </Field>
            <button disabled={busy}>Trimite cererea</button>
          </form>
        )
      )}
      {can("approvals:request") && evidence.has_original && (
        <div>
          <button className="secondary" onClick={() => setConfirmExport(true)}>
            Exportă (necesită o cerere de export aprobată)
          </button>
        </div>
      )}
      {message && <Banner tone={message.tone}>{message.text}</Banner>}
      {confirmExport && (
        <ConfirmDialog
          title="Exportați originalul?"
          confirmLabel="Exportă"
          busy={busy}
          onConfirm={() => void exportEvidence()}
          onCancel={() => setConfirmExport(false)}
        >
          Exportul este înregistrat în audit și funcționează doar cu o cerere de export aprobată.
        </ConfirmDialog>
      )}
    </div>
  );
}

const PATROL_LABEL: Record<string, string> = {
  assigned: "Atribuită",
  en_route: "În drum spre locație",
  on_scene: "La fața locului",
  done: "Încheiată",
};
const PATROL_NEXT: { status: "en_route" | "on_scene" | "done"; label: string }[] = [
  { status: "en_route", label: "Am plecat spre locație" },
  { status: "on_scene", label: "Sunt la fața locului" },
  { status: "done", label: "Intervenție încheiată" },
];

/** Real patrol workflow: operators assign an active patrol account; the assignee reports progress.
 *  No positions or ETAs are shown: the system has no location source for patrols. */
function PatrolPanel({ alert, onChange }: { alert: Alert; onChange: () => void }) {
  const { me, can } = useAuth();
  const [patrols, setPatrols] = useState<Patrol[]>([]);
  const [pick, setPick] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const canAssign = can("alerts:assign");
  useEffect(() => {
    if (canAssign)
      get<Patrol[]>("/api/patrols")
        .then(setPatrols)
        .catch(() => setPatrols([]));
  }, [canAssign]);
  const status = alert.assigned_to ? (alert.patrol_status ?? "assigned") : null;
  const mine = me?.id === alert.assigned_to && can("patrol:respond");
  const order = ["assigned", "en_route", "on_scene", "done"];
  async function assign() {
    try {
      await post(`/api/alerts/${alert.id}/assign`, { user_id: pick });
      setMsg(null);
      onChange();
    } catch {
      setMsg("Atribuirea nu a reușit.");
    }
  }
  async function report(next: string) {
    try {
      await post(`/api/alerts/${alert.id}/patrol-status`, { status: next });
      setMsg(null);
      onChange();
    } catch {
      setMsg("Starea nu a putut fi actualizată.");
    }
  }
  if (!canAssign && !status) return null;
  return (
    <section className="card" aria-label="Patrulă">
      <h2>Patrulă</h2>
      {status ? (
        <p>
          {alert.assigned_to_name ?? "Patrulă"}: <strong>{PATROL_LABEL[status]}</strong>
          {alert.patrol_status_at && (
            <span className="muted"> · {fmtDateTime(alert.patrol_status_at)}</span>
          )}
        </p>
      ) : (
        <p className="muted">Nicio patrulă atribuită.</p>
      )}
      {mine &&
        status &&
        PATROL_NEXT.filter((n) => order.indexOf(n.status) > order.indexOf(status)).map((n) => (
          <button key={n.status} type="button" onClick={() => void report(n.status)}>
            {n.label}
          </button>
        ))}
      {canAssign && (
        <div className="actions">
          <select aria-label="Patrulă" value={pick} onChange={(e) => setPick(e.target.value)}>
            <option value="">Alegeți patrula…</option>
            {patrols.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name} ({p.open_assignments} deschise)
              </option>
            ))}
          </select>
          <button
            type="button"
            className="secondary"
            disabled={!pick}
            onClick={() => void assign()}
          >
            {alert.assigned_to ? "Reatribuie" : "Atribuie"}
          </button>
        </div>
      )}
      {msg && <Banner tone="error">{msg}</Banner>}
    </section>
  );
}

export function AlertDetailPage() {
  const { id } = useParams();
  const { can } = useAuth();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState<"confirm" | "reject" | null>(null);
  const [busy, setBusy] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);
  usePageTitle(alert ? alert.description : "Alertă");

  const load = useCallback(async () => {
    try {
      const a = await get<Alert>(`/api/alerts/${id}`);
      setAlert(a);
      setEvidence(await get<Evidence[]>(`/api/evidence?alert_id=${a.id}`));
    } catch {
      setError("Alerta nu a fost găsită.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(action: "confirm" | "reject") {
    setBusy(true);
    setDecideError(null);
    try {
      await post(`/api/alerts/${id}/${action}`);
      setAsking(null);
      await load();
    } catch (err) {
      setDecideError(
        err instanceof ApiError && err.status === 409
          ? "Alerta a fost deja decisă. Reîncărcați pagina."
          : "Decizia nu a putut fi înregistrată. Încercați din nou.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (error)
    return (
      <div className="stack">
        <h1>Alertă</h1>
        <Banner tone="error">{error}</Banner>
        <Link to="/alerts">← Alerte</Link>
      </div>
    );
  if (!alert)
    return (
      <p className="muted" role="status">
        Se încarcă…
      </p>
    );
  const canDecide = can("alerts:decide") && alert.status === "new";
  return (
    <section aria-labelledby="alert-h">
      <Link to="/alerts">← Alerte</Link>
      <h1 id="alert-h">
        <PriorityBadge priority={alert.priority} /> {alert.description}
      </h1>
      <p>
        {alert.event_type} · {alert.camera_name} · {fmtDateTime(alert.detected_at)}{" "}
        (Europa/București) · număr <code>{alert.plate_masked ?? "-"}</code> · stare{" "}
        <strong>{STATUS_LABEL[alert.status] ?? alert.status}</strong>
      </p>
      <PatrolPanel alert={alert} onChange={() => void load()} />
      {alert.decided_at && <p className="muted">Decisă la {fmtDateTime(alert.decided_at)}.</p>}
      <p className="muted">Decizia aparține operatorului. Sistemul nu emite sancțiuni automat.</p>
      {evidence.map((ev) => (
        <EvidencePanel key={ev.id} evidence={ev} onChange={() => void load()} />
      ))}
      {canDecide && (
        <div className="actions decision-bar">
          <button type="button" onClick={() => setAsking("confirm")}>
            Confirmă
          </button>
          <button type="button" className="reject" onClick={() => setAsking("reject")}>
            Respinge
          </button>
        </div>
      )}
      {asking && (
        <ConfirmDialog
          title={asking === "confirm" ? "Confirmați alerta?" : "Respingeți alerta?"}
          confirmLabel={asking === "confirm" ? "Confirmă alerta" : "Respinge alerta"}
          danger={asking === "reject"}
          busy={busy}
          error={decideError}
          onConfirm={() => void decide(asking)}
          onCancel={() => {
            setAsking(null);
            setDecideError(null);
          }}
        >
          Alerta „{alert.description}” va fi marcată ca{" "}
          {asking === "confirm" ? "confirmată" : "respinsă"}. Decizia se înregistrează în audit și
          nu poate fi anulată din această aplicație.
        </ConfirmDialog>
      )}
    </section>
  );
}
