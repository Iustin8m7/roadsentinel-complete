const PRIORITY = { critical: "Critică", high: "Ridicată", medium: "Medie", info: "Informativă" };
const SIGN_TEXT = { critical: "!", high: "!", medium: "", info: "i" };
const TYPE = {
  wrong_way: "Sens interzis", pedestrian_on_road: "Pieton pe carosabil", very_high_speed: "Viteză foarte mare",
  stopped_emergency_lane: "Vehicul oprit pe banda de urgență", stopped_on_road: "Vehicul oprit pe carosabil",
  hard_braking: "Frânare bruscă", tailgating: "Distanță prea mică", dangerous_lane_change: "Schimbare de bandă periculoasă",
  congestion: "Aglomerare",
};
const CLASS = { car: "autoturism", truck: "camion", bus: "autobuz", motorcycle: "motocicletă", person: "persoană" };
const STATUS = { new: "nouă", confirmed: "confirmată", rejected: "respinsă" };
const AUDIT = { login: "s-a autentificat", detected: "detectat de sistem", viewed: "a deschis dosarul", confirmed: "a confirmat", rejected: "a respins",
  vlm_confirmed: "VLM: confirmat", vlm_rejected: "VLM: infirmat", vlm_uncertain: "VLM: nesigur" };

let events = [], current = null, actions = {}, mode = "queue";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtTime = (iso) => new Date(iso).toLocaleString("ro-RO", { weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });
const sign = (p) => `<span class="sign ${esc(p)}" role="img" aria-label="Prioritate ${esc(PRIORITY[p] ?? p)}">${esc(SIGN_TEXT[p])}</span>`;
const csrf = () => {
  const cookies = new Map(document.cookie.split(";").map((cookie) => {
    const [name, ...value] = cookie.trim().split("=");
    return [name, value.join("=")];
  }));
  return cookies.get("__Secure-rs_csrf") || cookies.get("rs_csrf") || "";
};
let refreshing = null;
const refreshSession = () => {
  refreshing ??= fetch("/api/auth/refresh", {
    method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": csrf() },
  }).then((r) => r.ok).catch(() => false).finally(() => { refreshing = null; });
  return refreshing;
};

const api = async (path, body, retried = false) => {
  const headers = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRF-Token"] = csrf();
  }
  const r = await fetch(path, {
    credentials: "same-origin", method: body === undefined ? "GET" : "POST", headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const loginRequest = path === "/api/login" || path === "/api/login/mfa" || path === "/api/auth/mfa/verify";
  // The secure backend's access cookie lives 10 minutes: renew it once, then retry.
  if (r.status === 401 && !loginRequest && !retried && await refreshSession()) return api(path, body, true);
  if (r.status === 401 && !loginRequest) { showLogin(); throw new Error("401"); }
  if (!r.ok) {
    const error = new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    error.status = r.status;
    throw error;
  }
  return r.status === 204 ? null : r.json();
};

// Every user action reports failures in the banner and can't be double-submitted.
function showError(msg) {
  $("error").textContent = msg;
  $("error").hidden = !msg;
}
async function withBusy(button, busyLabel, fn) {
  const label = button?.textContent;
  if (button) { button.disabled = true; if (busyLabel) button.textContent = busyLabel; }
  try {
    showError("");
    return await fn();
  } catch (err) {
    if (err.message !== "401") showError(err.message || "Serverul nu răspunde. Încearcă din nou.");
  } finally {
    if (button) { button.disabled = false; button.textContent = label; }
  }
}

function renderList(list) {
  $("queue-count").textContent = `${list.length}`;
  if (!list.length) {
    $("alerts").innerHTML = `<li class="empty empty-list">${mode === "queue" ? "Nicio alertă de verificat." : "Nu am găsit evenimente pentru căutarea asta. Încearcă alt interval sau alt tip de eveniment."}</li>`;
    return;
  }
  $("alerts").innerHTML = list.map((e) => `
    <li><button data-id="${esc(e.id)}" aria-current="${esc(current?.id === e.id)}">
      ${sign(e.priority)}
      <span><span class="a-title">${esc(TYPE[e.type] ?? e.type)}</span><br>
        <span class="a-meta">${esc(fmtTime(e.occurred_at))} · ${esc(e.camera_name)}</span></span>
      <span class="a-status ${esc(e.status)}">${esc(STATUS[e.status] ?? e.status)}</span>
    </button></li>`).join("");
}

async function loadQueue() {
  events = await api("/api/events");
  if (mode === "queue") renderList(events);
}

async function openEvent(id) {
  await withBusy(null, null, async () => {
    current = await api(`/api/events/${id}`);
    await api(`/api/events/${id}/view`, {});
    renderList(mode === "queue" ? events : searchResults);
    renderEvidence();
    await loadSide();
  });
}

function renderEvidence() {
  const e = current;
  const facts = [
    ["Prioritate", PRIORITY[e.priority]],
    ["Ora", fmtTime(e.occurred_at)],
    ["Obiect", e.object_class ? `${CLASS[e.object_class] ?? e.object_class} #${e.track_id}` : "scenă"],
    ["Viteză estimată", e.speed_kmh ? `${Math.round(e.speed_kmh)} km/h` : "–"],
    ["Loc", e.location || e.camera_name],
  ];
  const vlmClass = { confirmed: "confirmed", rejected: "rejected" }[e.vlm_status] || "";
  const vlmLabel = { confirmed: "Model vizual: confirmă alerta", rejected: "Model vizual: infirmă alerta",
    uncertain: "Model vizual: nesigur", pending: "Model vizual: în așteptare", skipped: "Model vizual: neverificat" }[e.vlm_status];
  const decided = e.status !== "new"
    ? `<div class="decided"><strong>${e.status === "confirmed" ? "Confirmată" : "Respinsă"}</strong>${e.action ? ` – ${esc(actions[e.action])}` : ""}</div>`
    : `<form class="decide" id="decide">
        <select id="action" aria-label="Acțiune">${Object.entries(actions).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join("")}</select>
        <input id="note" placeholder="Notă (opțional)" aria-label="Notă">
        <button class="primary" type="submit">Confirmă și trimite</button>
        <button class="danger" type="button" id="reject">Respinge</button>
      </form>`;
  $("evidence").innerHTML = `
    <div class="ev-head">${sign(e.priority)}
      <div><h1 class="ev-title">${esc(TYPE[e.type] ?? e.type)}</h1>
      <div class="ev-sub">${esc(e.camera_name)} · secunda ${esc(Number(e.video_t || 0).toFixed(1))} din înregistrare</div></div>
    </div>
    ${e.redaction === "heads_only" ? '<p class="redaction-warning" role="note">Plăcuțe neblurate (plates not blurred)</p>' : ""}
    <div class="media">
      <figure><video src="${esc(e.clip_url)}" controls autoplay muted loop playsinline></video>
        <figcaption>Clip ±3 s în jurul evenimentului</figcaption></figure>
      <figure><img src="${esc(e.keyframe_url)}" alt="Cadru cheie: ${esc(TYPE[e.type] ?? e.type)}">
        <figcaption>Cadru cheie, vehiculul vizat încadrat</figcaption></figure>
    </div>
    <dl class="facts">${facts.map(([k, v]) => `<div class="fact"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
    <div class="rule"><span class="label">Regula care a declanșat alerta</span><p>${esc(e.rule)}</p></div>
    <div class="vlm ${esc(vlmClass)}"><span class="label">${esc(vlmLabel)}</span><p>${esc(e.vlm_text || "Verificarea nu a rulat încă.")}</p></div>
    ${decided}`;
  if (e.status === "new") {
    $("decide").addEventListener("submit", (ev) => { ev.preventDefault(); decide("confirm", ev.submitter); });
    $("reject").addEventListener("click", (ev) => decide("reject", ev.currentTarget));
    $("action").value = e.priority === "critical" || e.priority === "high" ? "dispatch_patrol" : "monitor";
  }
}

async function decide(decision, button) {
  await withBusy(button, "Se trimite…", async () => {
    try {
      current = await api(`/api/events/${current.id}/decision`, {
        decision, action: decision === "confirm" ? $("action").value : null, note: $("note").value || null,
      });
    } catch (err) {
      // 409: another operator decided first; show their decision instead of ours.
      current = await api(`/api/events/${current.id}`);
      renderEvidence();
      throw err;
    }
    renderEvidence();
    $("evidence").querySelector(".decided").classList.add("flash");
    await loadQueue();
    if (mode !== "queue") renderList(searchResults);
    await loadSide();
  });
}

let searchResults = [];
$("search").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const q = $("q").value.trim();
  if (!q) return showQueue();
  const r = await withBusy(ev.submitter, "Se caută…", () => api(`/api/search?q=${encodeURIComponent(q)}`));
  if (!r) return;
  mode = "search";
  searchResults = r.results;
  $("queue-title").textContent = "Rezultate";
  $("understood").innerHTML = `<div class="understood">${esc(r.filter.explanation)}: ${describeFilter(r.filter)}
    <button type="button" id="clear">Înapoi la alerte</button></div>`;
  $("clear").addEventListener("click", showQueue);
  renderList(searchResults);
});

function describeFilter(f) {
  const parts = [];
  if (f.event_types.length) parts.push(f.event_types.map((t) => TYPE[t]).join(", "));
  if (f.object_classes.length) parts.push(f.object_classes.map((c) => CLASS[c]).join(", "));
  if (f.date_from) parts.push(`${fmtTime(f.date_from)} – ${fmtTime(f.date_to)}`);
  if (f.min_speed_kmh) parts.push(`peste ${f.min_speed_kmh} km/h`);
  if (f.priorities.length) parts.push(f.priorities.map((p) => PRIORITY[p]).join(", "));
  return esc(parts.join("; ") || "toate evenimentele");
}

function showQueue() {
  mode = "queue";
  $("q").value = "";
  $("queue-title").textContent = "Alerte";
  $("understood").innerHTML = "";
  renderList(events);
}

async function loadSide() {
  const [stats, audit] = await Promise.all([api("/api/stats"), api("/api/audit?limit=25")]);
  $("stats").innerHTML = ["critical", "high", "medium", "info"]
    .map((p) => `<div title="${esc(PRIORITY[p])}">${sign(p)}${esc(stats.by_priority[p] || 0)}</div>`).join("");
  $("vlm-state").textContent = stats.vlm_available
    ? "Căutarea cu model de limbaj este activă."
    : "Căutarea folosește cuvinte cheie.";
  $("audit").innerHTML = audit.map((a) => `<li><time>${esc(new Date(a.at).toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit", second: "2-digit" }))}</time>
    <span><strong>${esc(a.actor)}</strong> ${esc(AUDIT[a.action] ?? a.action)}${a.event_id ? ` #${esc(a.event_id)}` : ""}${a.note ? `<br><span class="label">${esc(a.note)}</span>` : ""}</span></li>`).join("");
}

async function loadCameras() {
  const cams = (await api("/api/cameras")).filter((c) => c.video_url);
  const pick = (c) => {
    $("live").src = c.video_url;
    $("cams").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.id === c.id));
  };
  $("cams").innerHTML = cams.map((c) => `<button type="button" data-id="${esc(c.id)}" aria-pressed="false">${esc(c.name)}</button>`).join("");
  $("cams").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => pick(cams.find((c) => c.id === b.dataset.id))));
  if (cams[0]) pick(cams[0]);
}

$("alerts").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-id]");
  if (b) openEvent(Number(b.dataset.id));
});

// Live updates: the server pushes `alert` and `audit` events; we refresh at most twice a second.
let refreshTimer = null, stream = null;
function scheduleRefresh() {
  if (refreshTimer) return;
  refreshTimer = setTimeout(async () => {
    refreshTimer = null;
    await withBusy(null, null, () => Promise.all([loadQueue(), loadSide()]));
    if (mode !== "queue") renderList(searchResults);
  }, 500);
}
function connectStream() {
  stream?.close();
  stream = new EventSource("/api/stream");
  stream.addEventListener("alert", scheduleRefresh);
  stream.addEventListener("audit", scheduleRefresh);
  // On (re)connect, reload: anything that happened while disconnected shows up.
  stream.onopen = () => { $("live-dot").classList.add("on"); scheduleRefresh(); };
  stream.onerror = async () => {
    $("live-dot").classList.remove("on");
    const response = await fetch("/api/me", { credentials: "same-origin" }).catch(() => null);
    if (response?.status === 401) return showLogin();
    const who = await response?.json().catch(() => null);
    if (who?.auth_required && !who.operator) showLogin();  // session expired
  };
}

let mfaRequired = false;
function resetLogin() {
  mfaRequired = false;
  $("password-step").hidden = false;
  $("login-name").disabled = false;
  $("login-pass").disabled = false;
  $("mfa-step").hidden = true;
  $("login-code").disabled = true;
  $("login-code").required = false;
  $("login-code").value = "";
  $("login-pass").value = "";
  $("enrollment").hidden = true;
  $("login-reset").hidden = true;
  $("login-submit").hidden = false;
  $("login-submit").textContent = "Intră";
  $("login-error").textContent = "";
}
function showLogin() {
  stream?.close();
  clearTimeout(refreshTimer);
  refreshTimer = null;
  $("live-dot").classList.remove("on");
  if (!$("login").open) { resetLogin(); $("login").showModal(); }
}
$("login-reset").addEventListener("click", resetLogin);
$("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const button = $("login-submit");
  button.disabled = true;
  $("login-error").textContent = "";
  try {
    if (mfaRequired) {
      const body = { code: $("login-code").value.trim() };
      try { await api("/api/login/mfa", body); }
      catch (err) {
        // The secure backend exposes verification at the auth route (204).
        if (err.status !== 404) throw err;
        await api("/api/auth/mfa/verify", body);
      }
      const who = await api("/api/me");
      if (!who.operator) throw new Error("Autentificarea nu este completă. Încearcă din nou.");
    } else {
      const who = await api("/api/login", { operator: $("login-name").value.trim(), password: $("login-pass").value });
      $("login-pass").value = "";
      if (who.mfa_required) {
        mfaRequired = true;
        $("password-step").hidden = true;
        $("login-name").disabled = true;
        $("login-pass").disabled = true;
        $("login-reset").hidden = false;
        if (who.mfa_enrollment) {
          $("enrollment").hidden = false;
          $("login-submit").hidden = true;
        } else {
          $("mfa-step").hidden = false;
          $("login-code").disabled = false;
          $("login-code").required = true;
          $("login-submit").textContent = "Verifică";
          $("login-code").focus();
        }
        return;
      }
    }
    $("login").close();
    resetLogin();
    await start();
  } catch (err) {
    $("login-error").textContent = err.status === 401 || err.message === "401"
      ? (mfaRequired ? "Cod incorect sau expirat. Încearcă din nou." : "Date de autentificare incorecte.") : err.message;
  } finally { button.disabled = false; }
});
$("login").addEventListener("cancel", (ev) => ev.preventDefault());  // Escape must not leave a dead page
$("logout").addEventListener("click", (ev) => withBusy(ev.currentTarget, "Se închide…", async () => { await api("/api/logout", {}); location.reload(); }));

async function start() {
  try { await api("/api/auth/csrf"); }
  catch (err) {
    // The local demonstration server predates CSRF protection.
    if (err.status !== 404) throw err;
  }
  const who = await api("/api/me");
  if (who.auth_required && !who.operator) return showLogin();
  $("who").textContent = who.operator || "operator local";
  $("logout").hidden = !who.auth_required;
  actions = (await api("/api/meta")).actions;
  await Promise.all([loadQueue(), loadSide(), loadCameras()]);
  connectStream();
}
withBusy(null, null, start);
