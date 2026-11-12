"""The API.md contract (``roadsentinel/schemas.py`` shapes) served by the secure backend.

Same paths and JSON as the prototype. Clients additionally need the CSRF header, the MFA step
and token refresh (see API.md "Secure backend"); ``web/index.html`` needs those changes. Also:
per-user accounts with MFA instead of a shared password, the audit actor is always the
authenticated user, every query runs under the caller's tenant (RLS), patrol users only see
alerts assigned to them, and media is decrypted on the fly for signed, session-checked URLs.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.alerts import get_visible_alert, mark_first_viewed
from app.api.auth import _clear_all, _set_session_cookies
from app.config import get_settings
from app.core.audit import AuditAction
from app.core.catalog import ACTIONS, EVENT_TYPES
from app.core.crypto import CryptoError
from app.core.http import MFA, set_cookie
from app.core.policy import Permission, has_permission, scope_alerts, scope_audit
from app.core.security import create_mfa_pending_token
from app.db import tenant_session
from app.deps import Principal, get_db, get_principal, not_found, require
from app.models import (
    PRIORITY_ORDER,
    Alert,
    AlertStatus,
    AuditLog,
    Camera,
    Evidence,
    SavedSearch,
    User,
    UserSession,
)
from app.schemas import contract as c
from app.services import auth as auth_service
from app.services import contract as view
from app.services import evidence as evidence_service
from app.services import pagination as pagination_service
from app.services import search as search_service

router = APIRouter(tags=["contract"])

POLL_SECONDS = 1.0
MAX_REPLAY = 200
MAX_EVENTS = 500
_viewed: set[tuple[uuid.UUID, uuid.UUID]] = set()  # (session, evidence): audit views once


# --------------------------------------------------------------------------- auth


@router.post("/api/login", response_model=c.Me)
def login(body: c.Login, response: Response, db: Session = Depends(get_db)) -> c.Me:
    """Password step. The second factor is ``POST /api/auth/mfa/verify`` (or enrollment via
    ``/api/auth/mfa/enroll/*`` on first login); then ``GET /api/me`` returns the operator."""
    result = auth_service.login_password(db, body.operator, body.password)
    if auth_service.mfa_exemption_applies(result.user):
        _set_session_cookies(response, auth_service.login_exempt(db, result.user))
        return c.Me(operator=result.user.display_name, auth_required=True, mfa_required=False)
    token = create_mfa_pending_token(
        result.user.id, result.user.tenant_id, enrollment=result.enrollment_required
    )
    set_cookie(response, MFA, token, get_settings().mfa_pending_ttl_seconds)
    return c.Me(
        operator=None,
        auth_required=True,
        mfa_required=True,
        mfa_enrollment=result.enrollment_required,
    )


def _optional_principal(request: Request, db: Session = Depends(get_db)) -> Principal | None:
    try:
        return get_principal(request, db)
    except HTTPException:
        return None


@router.post("/api/logout", response_model=c.Me)
def logout(response: Response, principal: Principal | None = Depends(_optional_principal)) -> c.Me:
    if principal is not None:
        auth_service.revoke_session(
            principal.db, principal.session, actor_id=principal.user_id, reason="logout"
        )
    _clear_all(response)
    return c.Me(operator=None, auth_required=True)


@router.get("/api/me", response_model=c.Me)
def me(principal: Principal | None = Depends(_optional_principal)) -> c.Me:
    return c.Me(operator=principal.user.display_name if principal else None, auth_required=True)


@router.get("/api/meta", response_model=c.Meta)
def meta(_: Principal = Depends(require(Permission.alerts_read))) -> c.Meta:
    return c.Meta(
        event_types={
            t: {"priority": p.value, "label": label} for t, (p, label) in EVENT_TYPES.items()
        },
        actions=ACTIONS,
    )


# --------------------------------------------------------------------------- events


def _visible(principal: Principal, number: int) -> tuple[Alert, Camera]:
    row = principal.db.execute(
        scope_alerts(view.visible_alerts(), principal).where(Alert.number == number)
    ).first()
    if row is None:
        raise HTTPException(404, "Eveniment inexistent.")
    return row


def _detail(principal: Principal, alert: Alert, camera: Camera) -> c.EventDetail:
    [event] = view.to_events(principal.db, principal.user_id, [(alert, camera)])
    return c.EventDetail(**event.model_dump(), audit=view.audit_for_alert(principal.db, alert))


@router.get("/api/events", response_model=list[c.Event])
def events(
    status: AlertStatus | None = None,
    camera_id: str | None = Query(default=None, pattern=c.CAMERA_ID),
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[c.Event]:
    stmt = scope_alerts(view.visible_alerts(), principal)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if camera_id:
        stmt = stmt.where(Camera.slug == camera_id)
    rows = principal.db.execute(view.queue_order(stmt).limit(MAX_EVENTS))
    return view.to_events(principal.db, principal.user_id, rows)


@router.get("/api/events/{number}", response_model=c.EventDetail)
def event(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> c.EventDetail:
    alert, camera = _visible(principal, number)
    return _detail(principal, alert, camera)


@router.post("/api/events/{number}/view", status_code=204)
def viewed(number: int, principal: Principal = Depends(require(Permission.alerts_read))) -> None:
    alert, _ = _visible(principal, number)
    mark_first_viewed(principal, alert)
    principal.audit(
        AuditAction.alert_viewed,
        resource_type="alerts",
        resource_id=alert.id,
        details={"event_no": alert.number},
    )


@router.post("/api/events/{number}/decision", response_model=c.EventDetail)
def decide(
    number: int,
    body: c.Decision,
    principal: Principal = Depends(require(Permission.alerts_decide)),
) -> c.EventDetail:
    alert, camera = _visible(principal, number)
    confirm = body.decision == "confirm"
    if confirm and body.action not in ACTIONS:
        raise HTTPException(
            400, f"La confirmare, action trebuie să fie una din: {', '.join(ACTIONS)}."
        )
    action = body.action if confirm else None
    # Conditional update: of two concurrent decisions, exactly one matches status='new'.
    decided = principal.db.execute(
        update(Alert)
        .where(Alert.id == alert.id, Alert.status == AlertStatus.new)
        .values(
            status=AlertStatus.confirmed if confirm else AlertStatus.rejected,
            action=action,
            decision_note=body.note,
            decided_by=principal.user_id,
            decided_at=datetime.now(UTC),
        )
        .returning(Alert.id)
    ).first()
    principal.db.commit()
    principal.db.refresh(alert)
    if decided is None:
        verb = "confirmat" if alert.status == AlertStatus.confirmed else "respins"
        raise HTTPException(409, f"Evenimentul a fost deja {verb}.")
    note = " - ".join(x for x in (ACTIONS.get(action or ""), body.note) if x) or None
    principal.audit(
        AuditAction.alert_confirmed if confirm else AuditAction.alert_rejected,
        resource_type="alerts",
        resource_id=alert.id,
        details={"event_no": alert.number, "action": action, "note": note},
    )
    return _detail(principal, alert, camera)


# --------------------------------------------------------------------------- cameras, stats


@router.get("/api/cameras", response_model=list[c.CameraOut])
def cameras(principal: Principal = Depends(require(Permission.cameras_read))) -> list[c.CameraOut]:
    out = []
    for cam in principal.db.scalars(select(Camera).order_by(Camera.name)):
        video = view.camera_video(principal.db, cam.id)
        if video and cam.lifecycle_state != "legacy":
            from app.services.camera_control import grant_allows_recordings, grants_for

            if not grant_allows_recordings(
                cam, grants_for(principal.db, cam.id), datetime.now(UTC)
            ):
                video = None
        out.append(
            c.CameraOut(
                id=cam.slug,
                source_kind=cam.source_kind,
                name=cam.name,
                location=cam.location,
                video_url=view.media_url(principal.user_id, video.id) if video else None,
                uuid=cam.id,
                timezone=cam.timezone,
                latitude=cam.latitude,
                longitude=cam.longitude,
                is_active=cam.is_active,
                last_seen_at=cam.last_seen_at,
                status_info=cam.status_info,
            )
        )
    return out


@router.get("/api/stats", response_model=c.Stats)
def stats(principal: Principal = Depends(require(Permission.alerts_read))) -> c.Stats:
    # Aggregate in SQL instead of materializing every alert (which also loads encrypted plate
    # fields and bulky event details that the statistics response never needs).
    scoped = scope_alerts(
        select(Alert.priority, Alert.status, Alert.event_type).where(Alert.superseded_at.is_(None)),
        principal,
    ).subquery()

    def by(column: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for key, count in principal.db.execute(
            select(scoped.c[column], func.count()).group_by(scoped.c[column])
        ):
            key = getattr(key, "value", key)
            out[key] = count
        return out

    by_priority = by("priority")
    by_status = by("status")
    return c.Stats(
        total=sum(by_priority.values()),
        by_priority=by_priority,
        by_status=by_status,
        by_type=by("event_type"),
        vlm_available=False,  # VLM runs on the pipeline machine; the API never sends frames
    )


def _search_response(
    filters: search_service.Filter,
    principal: Principal,
    *,
    cursor: str | None = None,
    limit: int = 50,
    audit_details: dict | None = None,
) -> c.SearchResponse:
    stmt = search_service.apply(scope_alerts(view.visible_alerts(), principal), filters)
    stmt = _priority_queue_order(stmt)
    if cursor:
        is_decided, priority_rank, detected_at, number = pagination_service.decode_cursor(
            cursor, tenant_id=principal.tenant_id, filters=filters.model_dump()
        )
        cursor_rank = case(dict(PRIORITY_ORDER), value=Alert.priority)
        stmt = stmt.where(
            tuple_(Alert.status != AlertStatus.new, cursor_rank, Alert.detected_at, Alert.number)
            > tuple_(is_decided, priority_rank, detected_at, number)
        )
    rows = list(principal.db.execute(stmt.limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if has_more and rows:
        alert, _ = rows[-1]
        next_cursor = pagination_service.encode_cursor(
            tenant_id=principal.tenant_id,
            filters=filters.model_dump(),
            is_decided=alert.status != AlertStatus.new,
            priority_rank=PRIORITY_ORDER[alert.priority],
            detected_at=alert.detected_at,
            number=alert.number,
        )
    # Audit the search without its text (it may contain personal data): length + filter.
    details = {"filter": filters.model_dump(), "results": len(rows)}
    if audit_details:
        details.update(audit_details)
    principal.audit(
        AuditAction.alert_search,
        details=details,
    )
    return c.SearchResponse(
        filter=filters.model_dump(),
        results=view.to_events(principal.db, principal.user_id, rows),
        next_cursor=next_cursor,
    )


def _priority_queue_order(stmt):
    """Queue order with a unique final key, required for stable continuation pages."""
    rank = case(dict(PRIORITY_ORDER), value=Alert.priority)
    return stmt.order_by(Alert.status != AlertStatus.new, rank, Alert.detected_at, Alert.number)


@router.post("/api/search", response_model=c.SearchResponse)
def search_post(
    body: c.SearchQuery,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> c.SearchResponse:
    """Preferred search endpoint: keep sensitive query text out of URL and access logs."""
    filters = search_service.parse_keywords(body.q)
    return _search_response(
        filters,
        principal,
        cursor=body.cursor,
        limit=body.limit,
        audit_details={"query_length": len(body.q)},
    )


@router.get("/api/search", response_model=c.SearchResponse, deprecated=True)
def search_get(
    q: str = Query(min_length=1, max_length=500),
    cursor: str | None = Query(default=None, min_length=16, max_length=1024),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> c.SearchResponse:
    """Compatibility endpoint; new clients should POST the query body."""
    filters = search_service.parse_keywords(q)
    return _search_response(
        filters,
        principal,
        cursor=cursor,
        limit=limit,
        audit_details={"query_length": len(q)},
    )


def _saved_search_out(row: SavedSearch) -> c.SavedSearchOut:
    return c.SavedSearchOut(
        id=row.id, name=row.name, filters=row.filters, created_at=row.created_at
    )


@router.get("/api/saved-searches", response_model=list[c.SavedSearchOut])
def saved_searches(
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[c.SavedSearchOut]:
    rows = principal.db.scalars(
        select(SavedSearch)
        .where(SavedSearch.owner_id == principal.user_id)
        .order_by(SavedSearch.name)
        .limit(100)
    )
    return [_saved_search_out(row) for row in rows]


@router.post("/api/saved-searches", response_model=c.SavedSearchOut, status_code=201)
def create_saved_search(
    body: c.SavedSearchCreate,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> c.SavedSearchOut:
    existing = principal.db.scalar(
        select(func.count())
        .select_from(SavedSearch)
        .where(SavedSearch.owner_id == principal.user_id)
    )
    if (existing or 0) >= 100:
        raise HTTPException(409, "Saved search limit reached")
    parsed = search_service.parse_keywords(body.query)
    row = SavedSearch(
        tenant_id=principal.tenant_id,
        owner_id=principal.user_id,
        name=body.name,
        # Persist only normalized filters; discard the free-text query and its possible PII.
        filters=parsed.model_dump(exclude={"explanation"}),
    )
    principal.db.add(row)
    try:
        principal.db.commit()
    except IntegrityError as exc:
        principal.db.rollback()
        raise HTTPException(409, "A saved search with this name already exists") from exc
    principal.audit(
        AuditAction.saved_search_created,
        resource_type="saved_searches",
        resource_id=row.id,
        details={"name_length": len(row.name)},
    )
    return _saved_search_out(row)


@router.put("/api/saved-searches/{search_id}", response_model=c.SavedSearchOut)
def update_saved_search(
    search_id: uuid.UUID,
    body: c.SavedSearchCreate,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> c.SavedSearchOut:
    row = principal.db.scalar(
        select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.owner_id == principal.user_id
        )
    )
    if row is None:
        raise HTTPException(404, "Saved search not found")
    parsed = search_service.parse_keywords(body.query)
    row.name = body.name
    row.filters = parsed.model_dump(exclude={"explanation"})
    try:
        principal.db.commit()
    except IntegrityError as exc:
        principal.db.rollback()
        raise HTTPException(409, "A saved search with this name already exists") from exc
    principal.audit(
        AuditAction.saved_search_updated,
        resource_type="saved_searches",
        resource_id=row.id,
        details={"name_length": len(row.name)},
    )
    return _saved_search_out(row)


@router.delete("/api/saved-searches/{search_id}", status_code=204)
def delete_saved_search(
    search_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> Response:
    row = principal.db.scalar(
        select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.owner_id == principal.user_id
        )
    )
    if row is None:
        raise HTTPException(404, "Saved search not found")
    search_id = row.id
    principal.db.delete(row)
    principal.db.commit()
    principal.audit(
        AuditAction.saved_search_deleted,
        resource_type="saved_searches",
        resource_id=search_id,
    )
    return Response(status_code=204)


@router.post("/api/saved-searches/{search_id}/run", response_model=c.SearchResponse)
def run_saved_search(
    search_id: uuid.UUID,
    body: c.SearchPage | None = None,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> c.SearchResponse:
    saved = principal.db.scalar(
        select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.owner_id == principal.user_id
        )
    )
    if saved is None:
        raise HTTPException(404, "Saved search not found")
    try:
        filters = search_service.Filter.model_validate(saved.filters)
    except ValueError as exc:
        raise HTTPException(409, "Saved search filters are invalid") from exc
    page = body or c.SearchPage()
    return _search_response(
        filters,
        principal,
        cursor=page.cursor,
        limit=page.limit,
        audit_details={"saved_search_id": str(saved.id)},
    )


@router.get("/api/audit", response_model=list[c.AuditEntry])
def audit(
    limit: int = Query(default=50, ge=1, le=500),
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[c.AuditEntry]:
    """Alert-related history of the caller's unit (detections, views, decisions, VLM).
    Security events stay in the auditor-only raw chain (``/api/audit/chain``)."""
    stmt = scope_audit(view.audit_query(), principal)
    entries = principal.db.scalars(stmt.order_by(AuditLog.seq.desc()).limit(limit))
    return view.to_audit(principal.db, list(entries))


# --------------------------------------------------------------------------- media


@router.get("/api/media/{evidence_id}", include_in_schema=False)
def media(
    evidence_id: uuid.UUID,
    request: Request,
    exp: int = Query(),
    sig: str = Query(max_length=100),
    principal: Principal = Depends(require(Permission.evidence_read)),
) -> StreamingResponse:
    if not view.media_signature_ok(principal.user_id, evidence_id, exp, sig):
        raise HTTPException(403, "Link invalid sau expirat.")
    ev = principal.db.get(Evidence, evidence_id)
    if ev is None:
        not_found(principal, "evidence", evidence_id)
    if ev.alert_id is not None:
        get_visible_alert(principal, ev.alert_id)  # patrol scoping via the parent alert
    elif not has_permission(principal.role, Permission.cameras_read):
        raise HTTPException(403, "Forbidden")
    elif ev.camera_id is not None:
        camera = principal.db.get(Camera, ev.camera_id)
        if camera and camera.lifecycle_state != "legacy":
            from app.services.camera_control import grant_allows_recordings, grants_for

            if not grant_allows_recordings(
                camera, grants_for(principal.db, camera.id), datetime.now(UTC)
            ):
                raise HTTPException(403, "Recording access is not authorized")
    if ev.purged_at is not None:
        raise HTTPException(410, "Dovada a fost ștearsă conform politicii de retenție.")
    stream = evidence_service.open_decrypted(principal.keyring, ev, view.VARIANT)
    try:
        first = next(stream)
    except (CryptoError, FileNotFoundError, StopIteration) as exc:
        raise HTTPException(500, "Evidence unavailable") from exc
    if (principal.session.id, ev.id) not in _viewed:
        _viewed.add((principal.session.id, ev.id))
        principal.audit(
            AuditAction.evidence_viewed,
            resource_type="evidence",
            resource_id=ev.id,
            details={"variant": view.VARIANT, "redaction": ev.redaction},
        )

    def body() -> object:
        yield first
        yield from stream

    range_header = request.headers.get("range")
    if range_header:
        from app.services.http_range import bounds, slice_stream

        # Verify/decrypt each chunk once to measure the actual stored variant, then stream
        # just the requested range. No unbounded buffer, plaintext file or original fallback.
        try:
            size = len(first) + sum(len(chunk) for chunk in stream)
        except (CryptoError, FileNotFoundError) as exc:
            raise HTTPException(500, "Evidence unavailable") from exc
        try:
            start, end = bounds(range_header, size)
        except ValueError:
            raise HTTPException(
                416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"}
            ) from None
        return StreamingResponse(
            slice_stream(
                evidence_service.open_decrypted(principal.keyring, ev, view.VARIANT), start, end
            ),
            status_code=206,
            media_type=ev.content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Content-Length": str(end - start + 1),
                "Accept-Ranges": "bytes",
                "Content-Disposition": "inline",
                "Cache-Control": "private, no-store",
                "Cross-Origin-Resource-Policy": "same-origin",
            },
        )

    return StreamingResponse(
        body(),  # type: ignore[arg-type]
        media_type=ev.content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
            "Cache-Control": "no-store",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


# --------------------------------------------------------------------------- live stream


def _session_alive(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    session = db.get(UserSession, session_id)
    user = db.get(User, user_id)
    now = datetime.now(UTC)
    return bool(
        session
        and session.revoked_at is None
        and session.expires_at > now
        and user
        and user.is_active
    )


def poll(principal: Principal, after_event: int, after_audit: int) -> tuple[str | None, int, int]:
    """One poll in a fresh tenant-bound transaction. Returns (chunk or None if the session is
    no longer valid, new cursors)."""
    with tenant_session(principal.tenant_id) as db:
        if not _session_alive(db, principal.session.id, principal.user_id):
            return None, after_event, after_audit
        chunk = ""
        rows = db.execute(
            scope_alerts(view.visible_alerts(), principal)
            .where(Alert.number > after_event)
            .order_by(Alert.number)
            .limit(MAX_REPLAY)
        )
        for event in view.to_events(db, principal.user_id, list(rows)):
            after_event = max(after_event, event.id)
            chunk += f"id: {event.id}\nevent: alert\ndata: {event.model_dump_json()}\n\n"
        entries = db.scalars(
            scope_audit(view.audit_query(), principal)
            .where(AuditLog.seq > after_audit)
            .order_by(AuditLog.seq)
            .limit(500)
        ).all()
        if entries:
            after_audit = entries[-1].seq
        for entry in view.to_audit(db, entries):
            chunk += f"event: audit\ndata: {entry.model_dump_json()}\n\n"
        return chunk or ": ping\n\n", after_event, after_audit


def release_request_session(principal: Principal) -> None:
    """A stream outlives the request: give the request's DB connection back to the pool now
    (each poll opens its own short transaction). Loaded objects stay usable
    (expire_on_commit=False)."""
    # Detach first: rollback() would expire the loaded user/session and every later poll
    # would fail with DetachedInstanceError. close() then releases the connection.
    principal.db.expunge_all()
    principal.db.close()


def cursors(principal: Principal, last_event_id: str | None) -> tuple[int, int]:
    with tenant_session(principal.tenant_id) as db:
        top_event = db.scalar(select(Alert.number).order_by(Alert.number.desc()).limit(1)) or 0
        top_audit = db.scalar(select(AuditLog.seq).order_by(AuditLog.seq.desc()).limit(1)) or 0
    if last_event_id and last_event_id.isdigit() and len(last_event_id) <= 19:
        return min(int(last_event_id), top_event), top_audit
    return top_event, top_audit


@router.get("/api/stream")
async def stream(
    request: Request, principal: Principal = Depends(require(Permission.alerts_read))
) -> StreamingResponse:
    """Server-Sent Events: ``alert`` (with ``id:`` for ``Last-Event-ID`` replay) and ``audit``.
    The session is re-checked on every poll: a revoked or expired session ends the stream."""
    after_event, after_audit = await run_in_threadpool(
        cursors, principal, request.headers.get("last-event-id")
    )
    await run_in_threadpool(release_request_session, principal)

    async def gen() -> AsyncIterator[str]:
        nonlocal after_event, after_audit
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            chunk, after_event, after_audit = await run_in_threadpool(
                poll, principal, after_event, after_audit
            )
            if chunk is None:
                return
            yield chunk
            await asyncio.sleep(POLL_SECONDS)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
