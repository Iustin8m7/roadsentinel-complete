"""Private persisted inbox and replayable tenant-scoped SSE feed."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.policy import Permission, has_permission
from app.db import tenant_session
from app.deps import Principal, require
from app.models import NotificationEvent, NotificationPreference, NotificationReceipt, User, UserSession
from app.services.notifications import visible_query

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class PreferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sound_on_critical: bool


@router.get("/preferences")
def preferences(principal: Principal = Depends(require(Permission.alerts_read))):
    row = principal.db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == principal.user_id))
    return {"sound_on_critical": row.sound_on_critical if row else False}


@router.put("/preferences")
def save_preferences(body: PreferenceIn, principal: Principal = Depends(require(Permission.alerts_read))):
    now = datetime.now(UTC)
    principal.db.execute(insert(NotificationPreference).values(
        id=uuid.uuid4(), tenant_id=principal.tenant_id, user_id=principal.user_id,
        created_at=now, updated_at=now, sound_on_critical=body.sound_on_critical,
    ).on_conflict_do_update(constraint="uq_notification_preference_user",
        set_={"updated_at": now, "sound_on_critical": body.sound_on_critical}))
    principal.db.commit()
    return {"sound_on_critical": body.sound_on_critical}


def _alive(db, principal):
    session = db.get(UserSession, principal.session.id)
    user = db.get(User, principal.user_id)
    if user:
        principal.user.role = user.role
    return bool(session and session.revoked_at is None and session.expires_at > datetime.now(UTC)
                and user and user.is_active and has_permission(user.role, Permission.alerts_read))


def _item(event, alert, receipt):
    return {
        "id": str(event.id), "sequence": event.sequence, "incident_id": str(alert.id),
        "alert_number": alert.number, "kind": event.kind, "priority": event.priority,
        "provenance": event.provenance, "status": alert.status.value,
        "created_at": event.created_at.isoformat(),
        "read_at": receipt.read_at.isoformat() if receipt and receipt.read_at else None,
        "acknowledged_at": receipt.acknowledged_at.isoformat() if receipt and receipt.acknowledged_at else None,
        "dismissed_at": receipt.dismissed_at.isoformat() if receipt and receipt.dismissed_at else None,
    }


def _page(principal, before, limit):
    db = principal.db
    stmt = visible_query(principal).outerjoin(
        NotificationReceipt,
        (NotificationReceipt.event_id == NotificationEvent.id)
        & (NotificationReceipt.user_id == principal.user_id),
    ).add_columns(NotificationReceipt)
    if before:
        stmt = stmt.where(NotificationEvent.sequence < before)
    rows = db.execute(stmt.order_by(NotificationEvent.sequence.desc()).limit(limit + 1)).all()
    items = [_item(e, a, r) for e, a, r in rows[:limit]]
    # A receipt row is unique per event/user. The aggregate is calculated from DB state.
    unread = db.scalar(select(func.count()).select_from(
        visible_query(principal).outerjoin(
            NotificationReceipt,
            (NotificationReceipt.event_id == NotificationEvent.id)
            & (NotificationReceipt.user_id == principal.user_id),
        ).where(NotificationReceipt.read_at.is_(None), NotificationReceipt.dismissed_at.is_(None)).subquery()
    )) or 0
    latest = db.scalar(select(func.max(NotificationEvent.sequence))) or 0
    return {"items": items, "unread": unread, "latest_sequence": latest,
            "next_cursor": items[-1]["sequence"] if len(rows) > limit else None}


@router.get("")
def inbox(before: int | None = Query(default=None, ge=1), limit: int = Query(default=30, ge=1, le=100),
          principal: Principal = Depends(require(Permission.alerts_read))):
    return _page(principal, before, limit)


@router.post("/{event_id}/read")
def mark_read(event_id: uuid.UUID, principal: Principal = Depends(require(Permission.alerts_read))):
    event = principal.db.execute(visible_query(principal).where(NotificationEvent.id == event_id)).first()
    if not event:
        raise HTTPException(404, "Notification not found")
    now = datetime.now(UTC)
    principal.db.execute(insert(NotificationReceipt).values(
        id=uuid.uuid4(), tenant_id=principal.tenant_id, user_id=principal.user_id,
        event_id=event_id, created_at=now, read_at=now,
    ).on_conflict_do_update(
        constraint="uq_notification_receipt_user_event", set_={"read_at": func.coalesce(NotificationReceipt.read_at, now)}
    ))
    principal.db.commit()
    return {"ok": True}


@router.post("/{event_id}/acknowledge")
def acknowledge(event_id: uuid.UUID, principal: Principal = Depends(require(Permission.alerts_read))):
    event = principal.db.execute(visible_query(principal).where(NotificationEvent.id == event_id)).first()
    if not event:
        raise HTTPException(404, "Notification not found")
    now = datetime.now(UTC)
    principal.db.execute(insert(NotificationReceipt).values(
        id=uuid.uuid4(), tenant_id=principal.tenant_id, user_id=principal.user_id,
        event_id=event_id, created_at=now, read_at=now, acknowledged_at=now,
    ).on_conflict_do_update(
        constraint="uq_notification_receipt_user_event", set_={"read_at": func.coalesce(NotificationReceipt.read_at, now),
            "acknowledged_at": func.coalesce(NotificationReceipt.acknowledged_at, now)}
    ))
    principal.db.commit()
    return {"ok": True}


@router.post("/{event_id}/dismiss")
def dismiss(event_id: uuid.UUID, principal: Principal = Depends(require(Permission.alerts_read))):
    event = principal.db.execute(visible_query(principal).where(NotificationEvent.id == event_id)).first()
    if not event:
        raise HTTPException(404, "Notification not found")
    now = datetime.now(UTC)
    principal.db.execute(insert(NotificationReceipt).values(
        id=uuid.uuid4(), tenant_id=principal.tenant_id, user_id=principal.user_id,
        event_id=event_id, created_at=now, dismissed_at=now,
    ).on_conflict_do_update(
        constraint="uq_notification_receipt_user_event", set_={"dismissed_at": func.coalesce(NotificationReceipt.dismissed_at, now)}
    ))
    principal.db.commit()
    return {"ok": True}


def _poll(principal, after):
    with tenant_session(principal.tenant_id) as db:
        if not _alive(db, principal):
            return None, after
        # Reuse the same object-scope predicate as the alert API. Never send coordinates/media.
        rows = db.execute(visible_query(principal).where(NotificationEvent.sequence > after)
                          .order_by(NotificationEvent.sequence).limit(100)).all()
        chunks = []
        for event, alert in rows:
            after = event.sequence
            chunks.append(f"id: {event.sequence}\nevent: notification\ndata: {json.dumps(_item(event, alert, None))}\n\n")
        return "".join(chunks) or ": ping\n\n", after


@router.get("/stream")
async def stream(request: Request, after: int = Query(default=0, ge=0),
                 principal: Principal = Depends(require(Permission.alerts_read))):
    last = request.headers.get("last-event-id", "")
    if last.isdigit() and len(last) <= 19:
        after = max(after, int(last))
    principal.db.expunge_all()
    principal.db.close()

    async def events():
        nonlocal after
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            chunk, after = await run_in_threadpool(_poll, principal, after)
            if chunk is None:
                return
            yield chunk
            await asyncio.sleep(2)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
