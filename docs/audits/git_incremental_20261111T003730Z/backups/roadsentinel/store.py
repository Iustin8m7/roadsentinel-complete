"""Event store and audit log. All SQL lives here.

Backed by SQLAlchemy, so it runs on SQLite (default, zero setup) or Postgres:
    DATABASE_URL=postgresql+psycopg://localhost/roadsentinel
"""
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    extract,
    func,
    insert,
    or_,
    select,
    update,
)

DEFAULT_URL = "sqlite:///data/roadsentinel.db"
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "info": 3}

meta = MetaData()

events = Table(
    "events", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("camera_id", String(64), nullable=False, index=True),
    Column("camera_name", String(200)),
    Column("location", String(200)),
    Column("type", String(40), nullable=False, index=True),
    Column("priority", String(10), nullable=False),
    Column("occurred_at", DateTime, nullable=False, index=True),   # local wall-clock time of the event
    Column("video_t", Float, nullable=False),                      # seconds into the source video
    Column("track_id", Integer),
    Column("object_class", String(20)),
    Column("speed_kmh", Float),
    Column("rule", Text, nullable=False),                          # the exact threshold that fired
    Column("details", JSON, nullable=False, default=dict),
    Column("keyframe", String(300)),
    Column("clip", String(300)),
    Column("vlm_status", String(12), nullable=False, default="pending"),  # pending|confirmed|rejected|uncertain|skipped
    Column("vlm_text", Text),
    Column("status", String(10), nullable=False, default="new", index=True),  # new|confirmed|rejected
    Column("action", String(40)),
)

audit = Table(
    "audit", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), index=True),
    Column("actor", String(100), nullable=False),
    Column("action", String(40), nullable=False),
    Column("note", Text),
    Column("at", DateTime(timezone=True), nullable=False),
)


def connect(url=None):
    url = url or os.environ.get("DATABASE_URL", DEFAULT_URL)
    # Hosting providers hand out postgres:// URLs; SQLAlchemy needs the driver named.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url.removeprefix(prefix)
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True)
    meta.create_all(engine)
    return engine


def now():
    return datetime.now(UTC)


def _audit_row(r):
    # SQLite drops the UTC offset on read; Postgres keeps it. Always return aware times.
    d = dict(r._mapping)
    if d["at"] is not None and d["at"].tzinfo is None:
        d["at"] = d["at"].replace(tzinfo=UTC)
    return d


def _sorted(rows):
    # Undecided first, then by priority, then oldest first.
    evs = [dict(r._mapping) for r in rows]
    evs.sort(key=lambda e: (e["status"] != "new", PRIORITY_ORDER.get(e["priority"], 9), e["occurred_at"]))
    return evs


def clear_camera(db, camera_id):
    """Reprocessing a camera replaces its events (and their audit trail) with the new run's."""
    with db.begin() as c:
        ids = select(events.c.id).where(events.c.camera_id == camera_id)
        c.execute(delete(audit).where(audit.c.event_id.in_(ids)))
        c.execute(delete(events).where(events.c.camera_id == camera_id))


def insert_event(db, e):
    cols = {k: e.get(k) for k in ("camera_id", "camera_name", "location", "type", "priority", "occurred_at",
                                  "video_t", "track_id", "object_class", "speed_kmh", "rule", "keyframe", "clip",
                                  "vlm_text")}
    cols["vlm_status"] = e.get("vlm_status") or "pending"
    if isinstance(cols["occurred_at"], str):
        cols["occurred_at"] = datetime.fromisoformat(cols["occurred_at"])
    with db.begin() as c:
        event_id = c.execute(insert(events).values(**cols, details=e.get("details", {}))).inserted_primary_key[0]
        c.execute(insert(audit).values(event_id=event_id, actor="system", action="detected", note=e["rule"], at=now()))
    return event_id


def log(db, event_id, actor, action, note=None):
    with db.begin() as c:
        c.execute(insert(audit).values(event_id=event_id, actor=actor, action=action, note=note, at=now()))


def get_event(db, event_id):
    with db.connect() as c:
        row = c.execute(select(events).where(events.c.id == event_id)).first()
        if row is None:
            return None
        trail = c.execute(select(audit).where(audit.c.event_id == event_id).order_by(audit.c.id)).all()
    return {**dict(row._mapping), "audit": [_audit_row(r) for r in trail]}


def query_events(db, *, types=(), classes=(), priorities=(), status=None, vlm_status=None, date_from=None,
                 date_to=None, hours=None, min_speed=None, text=None, camera_id=None):
    q = select(events)
    if types:
        q = q.where(events.c.type.in_(types))
    if classes:
        q = q.where(events.c.object_class.in_(classes))
    if priorities:
        q = q.where(events.c.priority.in_(priorities))
    if status:
        q = q.where(events.c.status == status)
    if vlm_status:
        q = q.where(events.c.vlm_status == vlm_status)
    if camera_id:
        q = q.where(events.c.camera_id == camera_id)
    if date_from:
        q = q.where(events.c.occurred_at >= date_from)
    if date_to:
        q = q.where(events.c.occurred_at < date_to)
    if hours:  # time-of-day window on any date, e.g. (18, 23)
        hour = extract("hour", events.c.occurred_at)
        q = q.where(hour >= hours[0], hour < hours[1])
    if min_speed:
        q = q.where(events.c.speed_kmh >= min_speed)
    if text:
        like = f"%{text}%"
        q = q.where(or_(events.c.vlm_text.ilike(like), events.c.location.ilike(like),
                        events.c.camera_name.ilike(like), events.c.rule.ilike(like)))
    with db.connect() as c:
        return _sorted(c.execute(q).all())


def set_decision(db, event_id, status, action, actor, note):
    with db.begin() as c:
        c.execute(update(events).where(events.c.id == event_id).values(status=status, action=action))
        c.execute(insert(audit).values(event_id=event_id, actor=actor, action=status, note=note, at=now()))


def set_vlm(db, event_id, status, text, verdict=None, actor=None):
    with db.begin() as c:
        values = {"vlm_status": status, "vlm_text": text}
        if verdict is not None:
            details = c.execute(select(events.c.details).where(events.c.id == event_id)).scalar_one()
            values["details"] = {**(details or {}), "vlm": verdict}
        c.execute(update(events).where(events.c.id == event_id).values(**values))
        if actor:
            c.execute(insert(audit).values(event_id=event_id, actor=actor, action=f"vlm_{status}",
                                           note=(verdict or {}).get("reason"), at=now()))


def audit_log(db, limit=50, after_id=0):
    q = (select(audit, events.c.type).select_from(audit.outerjoin(events, audit.c.event_id == events.c.id))
         .where(audit.c.id > after_id))
    q = q.order_by(audit.c.id.desc()).limit(limit) if not after_id else q.order_by(audit.c.id)
    with db.connect() as c:
        return [_audit_row(r) for r in c.execute(q).all()]


def events_after(db, after_id):
    with db.connect() as c:
        return [dict(r._mapping) for r in c.execute(select(events).where(events.c.id > after_id).order_by(events.c.id))]


def last_ids(db):
    with db.connect() as c:
        return (c.execute(select(func.coalesce(func.max(events.c.id), 0))).scalar_one(),
                c.execute(select(func.coalesce(func.max(audit.c.id), 0))).scalar_one())


def stats(db):
    with db.connect() as c:
        def count_by(col):
            return {k: n for k, n in c.execute(select(col, func.count()).group_by(col)).all()}
        return {"total": c.execute(select(func.count()).select_from(events)).scalar_one(),
                "by_priority": count_by(events.c.priority), "by_status": count_by(events.c.status),
                "by_type": count_by(events.c.type)}
