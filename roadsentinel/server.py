"""DEPRECATED legacy demo server (frozen; see web/DEPRECATED.md). Not the product: use backend/.

RoadSentinel API + operator dashboard (legacy).

Local:  uvicorn roadsentinel.server:app --port 8000
Prod env: DATABASE_URL, SECRET_KEY, DASHBOARD_PASSWORD, INGEST_TOKEN, S3_* (bucket), ANTHROPIC_API_KEY (optional)
"""
import asyncio
import hmac
import os
import secrets
from pathlib import Path

import yaml
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from . import media, search, store, vlm
from .rules import EVENT_TYPES
from .schemas import (
    CAMERA_ID,
    AuditEntry,
    Camera,
    Created,
    Decision,
    Event,
    EventDetail,
    IngestEvent,
    Login,
    Me,
    Meta,
    SearchResponse,
    Stats,
)

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = os.environ.get("DASHBOARD_PASSWORD")      # unset = no login (local development)
INGEST_TOKEN = os.environ.get("INGEST_TOKEN")
SECRET_KEY = os.environ.get("SECRET_KEY")

# On Railway, a missing secret must stop the deploy rather than silently open the dashboard.
if os.environ.get("RAILWAY_ENVIRONMENT"):
    missing = [k for k, v in {"DASHBOARD_PASSWORD": PASSWORD, "INGEST_TOKEN": INGEST_TOKEN,
                              "SECRET_KEY": SECRET_KEY}.items() if not v]
    if missing:
        raise RuntimeError(f"Missing production settings: {', '.join(missing)}")

app = FastAPI(title="RoadSentinel API", version="0.2.0",
              description="Alerte rutiere detectate automat, verificate de operator. Vezi API.md.")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY or secrets.token_hex(32),
                   https_only=os.environ.get("COOKIE_SECURE", "1" if PASSWORD else "0") == "1",
                   same_site="lax", max_age=12 * 3600)
db = store.connect()

ACTIONS = {
    "dispatch_patrol": "Trimite patrulă",
    "warning_sign": "Activează panou de avertizare",
    "enforcement": "Transmite către procedura de constatare",
    "monitor": "Doar monitorizare",
}


# ---------- auth ----------

def same(a: str, b: str) -> bool:
    # compare_digest only accepts ASCII str; passwords may contain diacritics.
    return hmac.compare_digest(a.encode(), b.encode())


def operator(request: Request) -> str:
    """The logged-in operator; every decision in the audit log is attributed to this name."""
    if not PASSWORD:
        return request.session.get("operator") or "operator local"
    name = request.session.get("operator")
    if not name:
        raise HTTPException(401, "Autentificare necesară.")
    return name


def ingest_auth(request: Request):
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not INGEST_TOKEN or not same(token, INGEST_TOKEN):
        raise HTTPException(401, "Token de ingestie invalid.")


@app.post("/api/login", response_model=Me, tags=["auth"])
def login(body: Login, request: Request):
    if PASSWORD and not same(body.password, PASSWORD):
        raise HTTPException(401, "Parolă greșită.")
    name = body.operator.strip()
    if not name:
        raise HTTPException(400, "Numele operatorului e obligatoriu.")
    request.session["operator"] = name
    store.log(db, None, name, "login")
    return Me(operator=name, auth_required=bool(PASSWORD))


@app.post("/api/logout", response_model=Me, tags=["auth"])
def logout(request: Request):
    request.session.clear()
    return Me(operator=None, auth_required=bool(PASSWORD))


@app.get("/api/me", response_model=Me, tags=["auth"])
def me(request: Request):
    return Me(operator=request.session.get("operator"), auth_required=bool(PASSWORD))


# ---------- dashboard data ----------

def to_event(row):
    return {**row, "keyframe_url": row.get("keyframe") and f"/media/{row['keyframe']}",
            "clip_url": row.get("clip") and f"/media/{row['clip']}"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/healthz", include_in_schema=False)
def healthz():
    store.last_ids(db)
    return {"ok": True}


@app.get("/api/meta", response_model=Meta, tags=["dashboard"])
def meta(_: str = Depends(operator)):
    return Meta(event_types={t: {"priority": p, "label": label} for t, (p, label) in EVENT_TYPES.items()},
                actions=ACTIONS)


@app.get("/api/cameras", response_model=list[Camera], tags=["dashboard"])
def cameras(_: str = Depends(operator)):
    out = []
    for p in sorted((ROOT / "cameras").glob("*.yaml")):
        cfg = yaml.safe_load(p.read_text())
        key = f"{cfg['id']}/annotated.mp4"
        out.append(Camera(id=cfg["id"], name=cfg["name"], location=cfg.get("location"),
                          video_url=f"/media/{key}" if media.exists(key) else None))
    return out


@app.get("/api/events", response_model=list[Event], tags=["dashboard"])
def events(status: str | None = None, camera_id: str | None = None, _: str = Depends(operator)):
    return [to_event(e) for e in store.query_events(db, status=status, camera_id=camera_id)]


@app.get("/api/events/{event_id}", response_model=EventDetail, tags=["dashboard"])
def event(event_id: int, _: str = Depends(operator)):
    e = store.get_event(db, event_id)
    if e is None:
        raise HTTPException(404, "Eveniment inexistent.")
    return to_event(e)


@app.post("/api/events/{event_id}/view", status_code=204, tags=["dashboard"])
def view(event_id: int, who: str = Depends(operator)):
    store.log(db, event_id, who, "viewed")


@app.post("/api/events/{event_id}/decision", response_model=EventDetail, tags=["dashboard"])
def decide(event_id: int, body: Decision, who: str = Depends(operator)):
    current = store.get_event(db, event_id)
    if current is None:
        raise HTTPException(404, "Eveniment inexistent.")
    if current["status"] != "new":
        raise HTTPException(409, f"Evenimentul a fost deja {'confirmat' if current['status'] == 'confirmed' else 'respins'}.")
    if body.decision == "confirm" and body.action not in ACTIONS:
        raise HTTPException(400, f"La confirmare, action trebuie să fie una din: {', '.join(ACTIONS)}.")
    status = "confirmed" if body.decision == "confirm" else "rejected"
    action = body.action if status == "confirmed" else None
    note = " – ".join(x for x in (ACTIONS.get(action or ""), body.note) if x) or None
    store.set_decision(db, event_id, status, action, who, note)
    return event(event_id, who)


@app.get("/api/search", response_model=SearchResponse, tags=["dashboard"])
def do_search(q: str, _: str = Depends(operator)):
    f, results = search.run(db, q)
    return {"filter": f.model_dump(), "results": [to_event(e) for e in results]}


@app.get("/api/stats", response_model=Stats, tags=["dashboard"])
def stats(_: str = Depends(operator)):
    return {**store.stats(db), "vlm_available": vlm.available()}


@app.get("/api/audit", response_model=list[AuditEntry], tags=["dashboard"])
def audit(limit: int = 50, _: str = Depends(operator)):
    return store.audit_log(db, limit=min(limit, 500))


def stream_events(after_event, after_audit):
    """Yields one SSE chunk per poll: new alerts (with `id:` so the browser can resume) and audit entries."""
    while True:
        chunk = ""
        for e in store.events_after(db, after_event):
            after_event = e["id"]
            payload = Event.model_validate(to_event(e)).model_dump_json()
            chunk += f"id: {e['id']}\nevent: alert\ndata: {payload}\n\n"
        for a in store.audit_log(db, after_id=after_audit, limit=500):
            after_audit = a["id"]
            chunk += f"event: audit\ndata: {AuditEntry.model_validate(a).model_dump_json()}\n\n"
        yield chunk or ": ping\n\n"


@app.get("/api/stream", tags=["dashboard"])
async def stream(request: Request, _: str = Depends(operator)):
    """Server-Sent Events: `alert` for every new event, `audit` for every new audit entry.
    On reconnect the browser sends Last-Event-ID, and alerts created in the gap are replayed."""
    last_event, last_audit = await run_in_threadpool(store.last_ids, db)
    resume = request.headers.get("last-event-id", "")
    if resume.isdigit():
        last_event = int(resume)
    events = stream_events(last_event, last_audit)

    async def gen():
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            yield await run_in_threadpool(next, events)  # DB polling off the event loop
            await asyncio.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/media/{key:path}", include_in_schema=False)
def get_media(key: str, _: str = Depends(operator)):
    try:
        path = media.local_path(key)  # also validates bucket keys: no absolute paths or ".."
    except ValueError:
        raise HTTPException(404) from None
    if media.bucket():
        return RedirectResponse(media.presigned_url(key), status_code=302)
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


# ---------- ingestion (pipeline -> API) ----------

# Plain `def` routes: FastAPI runs them in a thread pool, so uploads don't block the event loop.
CameraId = PathParam(pattern=CAMERA_ID)


@app.post("/api/ingest/events", response_model=Created, tags=["ingest"], dependencies=[Depends(ingest_auth)])
def ingest_event(event: str = Form(...), keyframe: UploadFile = File(...), clip: UploadFile = File(...)):
    try:
        e = IngestEvent.model_validate_json(event)
    except ValidationError as err:
        raise HTTPException(422, err.errors(include_url=False, include_context=False)) from None
    # Validate everything before storing anything; media names are chosen here, not by the client.
    stem = f"{e.camera_id}/event_{secrets.token_hex(6)}_{e.type}"
    media.save(f"{stem}.jpg", keyframe.file)
    media.save(f"{stem}.mp4", clip.file)
    row = {**e.model_dump(), "priority": EVENT_TYPES[e.type][0], "keyframe": f"{stem}.jpg", "clip": f"{stem}.mp4"}
    return Created(id=store.insert_event(db, row))


@app.put("/api/ingest/cameras/{camera_id}/video", status_code=204, tags=["ingest"],
         dependencies=[Depends(ingest_auth)])
def ingest_video(camera_id: str = CameraId, video: UploadFile = File(...)):
    media.save(f"{camera_id}/annotated.mp4", video.file)


@app.delete("/api/ingest/cameras/{camera_id}", status_code=204, tags=["ingest"], dependencies=[Depends(ingest_auth)])
def ingest_clear(camera_id: str = CameraId):
    store.clear_camera(db, camera_id)
    media.delete_prefix(f"{camera_id}/")
