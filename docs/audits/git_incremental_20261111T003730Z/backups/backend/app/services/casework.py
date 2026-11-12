"""Investigation completion: related cases (and explicit links), follow-up items, manual legal
holds, neighbouring-event timeline context and detection references.

Callers resolve the case first through the role-scoped alert query and pass that query
(``scoped``) in, so every other case this module returns is one the actor could open
themselves (patrol users: only assigned cases). Everything runs in the caller's RLS-bound
session. Audit entries hold ids, codes and lengths, never free text.

Relations are stated, not inferred:
* ``link``: an investigator linked the two cases, with a reason;
* ``same_track``: same camera, same pipeline track id AND the same recorded source run
  (``details.run_id``). Track ids restart with every pipeline run, so without a recorded run
  identifier a matching track id proves nothing and no relation is claimed;
* ``same_camera_window``: same camera within ``CONTEXT_WINDOW`` of the detection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.catalog import EVENT_TYPES
from app.core.policy import Permission, has_permission
from app.models import (
    Alert,
    Camera,
    CaseFollowup,
    CaseFollowupEvent,
    CaseLegalHold,
    CaseLink,
    FollowupStatus,
    Role,
    User,
)
from app.schemas import casework as cw
from app.services.investigation import CaseError, clean_text, recorded_bbox

CONTEXT_WINDOW = timedelta(minutes=10)
CONTEXT_LIMIT = 10  # events per side of the timeline
RELATED_LIMIT = 50
MAX_FOLLOWUPS = 100
RUN_ID_KEY = "run_id"
TRANSITIONS: dict[str, set[str]] = {
    FollowupStatus.open.value: {FollowupStatus.done.value, FollowupStatus.cancelled.value},
    FollowupStatus.done.value: {FollowupStatus.open.value},
    FollowupStatus.cancelled.value: {FollowupStatus.open.value},
}
HOLD_EFFECT = (
    "Reținerea legală oprește ștergerea manuală (purjarea) probelor cazului și păstrează "
    "pachetele de export după expirarea ferestrei de descărcare. Nu prelungește accesul: "
    "descărcarea cere în continuare o aprobare activă. Nu există o politică de retenție "
    "automată; reținerea nu schimbă nimic altceva."
)
CONTEXT_NOTE = (
    "Evenimente ale aceleiași camere, în ±10 minute de la detecție, doar cele pe care le puteți "
    "deschide. Poziția este ora detecției raportată de pipeline, nu un moment din clip."
)


def _names(db: Session, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids_ = {i for i in ids if i}
    if not ids_:
        return {}
    return dict(db.execute(select(User.id, User.display_name).where(User.id.in_(ids_))).all())


def _label(event_type: str) -> str:
    return EVENT_TYPES.get(event_type, (None, event_type))[1]


def run_id(alert: Alert) -> str | None:
    value = (alert.details or {}).get(RUN_ID_KEY)
    if isinstance(value, str) and 0 < len(value.strip()) <= 64:
        return value.strip()
    return None


# --------------------------------------------------------------------------- holds


def active_hold(db: Session, alert_id: uuid.UUID) -> CaseLegalHold | None:
    return db.scalar(
        select(CaseLegalHold).where(
            CaseLegalHold.alert_id == alert_id, CaseLegalHold.released_at.is_(None)
        )
    )


def is_held(db: Session, alert_id: uuid.UUID | None) -> bool:
    return alert_id is not None and active_hold(db, alert_id) is not None


def place_hold(db: Session, alert: Alert, actor_id: uuid.UUID, reason: str) -> CaseLegalHold:
    hold = CaseLegalHold(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        placed_by=actor_id,
        reason=clean_text(reason, 500),
    )
    db.add(hold)
    try:
        db.commit()
    except IntegrityError as exc:  # partial unique index: one active hold per case
        db.rollback()
        raise CaseError(409, "Cazul este deja sub reținere legală.", "already_held") from exc
    return hold


def release_hold(db: Session, alert: Alert, actor_id: uuid.UUID, reason: str) -> CaseLegalHold:
    text = clean_text(reason, 500)
    hold = db.scalar(
        select(CaseLegalHold)
        .where(CaseLegalHold.alert_id == alert.id, CaseLegalHold.released_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if hold is None:
        db.rollback()
        raise CaseError(409, "Cazul nu este sub reținere legală.", "not_held")
    hold.released_at = datetime.now(UTC)
    hold.released_by = actor_id
    hold.release_reason = text
    db.commit()
    return hold


def _hold_out(h: CaseLegalHold, names: dict[uuid.UUID, str]) -> cw.LegalHoldOut:
    return cw.LegalHoldOut(
        id=h.id,
        active=h.released_at is None,
        reason=h.reason,
        placed_by=names.get(h.placed_by, "utilizator"),
        placed_at=h.created_at,
        released_at=h.released_at,
        released_by=names.get(h.released_by) if h.released_by else None,
        release_reason=h.release_reason,
    )


def hold_state(db: Session, alert: Alert, role: Role) -> cw.LegalHoldState:
    holds = list(
        db.scalars(
            select(CaseLegalHold)
            .where(CaseLegalHold.alert_id == alert.id)
            .order_by(CaseLegalHold.created_at.desc())
            .limit(20)
        )
    )
    ids: set[uuid.UUID | None] = {h.placed_by for h in holds}
    ids |= {h.released_by for h in holds}
    names = _names(db, ids)
    out = [_hold_out(h, names) for h in holds]
    return cw.LegalHoldState(
        active=next((h for h in out if h.active), None),
        history=out,
        can_manage=has_permission(role, Permission.cases_legal_hold),
        effect=HOLD_EFFECT,
    )


# --------------------------------------------------------------------------- context


def neighbours(
    db: Session, scoped: Select[Any], alert: Alert
) -> tuple[list[tuple[Alert, Camera]], list[tuple[Alert, Camera]], bool, bool]:
    """Same camera, within the window, visible to the actor. (before, after, more_before,
    more_after); ``before`` is nearest-first reversed into chronological order."""
    near = scoped.where(
        Alert.camera_id == alert.camera_id,
        Alert.id != alert.id,
        Alert.detected_at >= alert.detected_at - CONTEXT_WINDOW,
        Alert.detected_at <= alert.detected_at + CONTEXT_WINDOW,
    )
    before = list(
        db.execute(
            near.where(
                or_(
                    Alert.detected_at < alert.detected_at,
                    and_(Alert.detected_at == alert.detected_at, Alert.number < alert.number),
                )
            )
            .order_by(Alert.detected_at.desc(), Alert.number.desc())
            .limit(CONTEXT_LIMIT + 1)
        ).tuples()
    )
    after = list(
        db.execute(
            near.where(
                or_(
                    Alert.detected_at > alert.detected_at,
                    and_(Alert.detected_at == alert.detected_at, Alert.number > alert.number),
                )
            )
            .order_by(Alert.detected_at, Alert.number)
            .limit(CONTEXT_LIMIT + 1)
        ).tuples()
    )
    more_before, more_after = len(before) > CONTEXT_LIMIT, len(after) > CONTEXT_LIMIT
    return (
        list(reversed(before[:CONTEXT_LIMIT])),
        after[:CONTEXT_LIMIT],
        more_before,
        more_after,
    )


def _context_event(a: Alert, anchor: Alert) -> cw.ContextEvent:
    return cw.ContextEvent(
        number=a.number,
        type=a.event_type,
        type_label=_label(a.event_type),
        status=a.status.value,
        observed_at=a.detected_at.astimezone(UTC),
        delta_s=round((a.detected_at - anchor.detected_at).total_seconds(), 3),
    )


def timeline_context(db: Session, scoped: Select[Any], alert: Alert) -> cw.TimelineContext:
    before, after, more_b, more_a = neighbours(db, scoped, alert)
    return cw.TimelineContext(
        window_s=int(CONTEXT_WINDOW.total_seconds()),
        limit_per_side=CONTEXT_LIMIT,
        before=[_context_event(a, alert) for a, _ in before],
        after=[_context_event(a, alert) for a, _ in after],
        truncated_before=more_b,
        truncated_after=more_a,
        note=CONTEXT_NOTE,
    )


# --------------------------------------------------------------------------- related / links


def _minutes(delta: timedelta) -> str:
    seconds = abs(delta.total_seconds())
    when = "înainte" if delta.total_seconds() < 0 else "după"
    if seconds < 60:
        return f"{seconds:.0f} s {when}"
    return f"{seconds / 60:.1f} min {when}".replace(".", ",")


def related_cases(
    db: Session, scoped: Select[Any], alert: Alert, me: uuid.UUID, role: Role
) -> list[cw.RelatedCase]:
    found: dict[uuid.UUID, tuple[Alert, Camera, list[cw.RelationReason]]] = {}

    def add(a: Alert, c: Camera, reason: cw.RelationReason) -> None:
        found.setdefault(a.id, (a, c, []))[2].append(reason)

    links = list(
        db.scalars(
            select(CaseLink)
            .where(
                or_(CaseLink.alert_a_id == alert.id, CaseLink.alert_b_id == alert.id),
                CaseLink.removed_at.is_(None),
            )
            .order_by(CaseLink.created_at)
            .limit(RELATED_LIMIT)
        )
    )
    if links:
        other_ids = {lk.alert_b_id if lk.alert_a_id == alert.id else lk.alert_a_id for lk in links}
        visible = {a.id: (a, c) for a, c in db.execute(scoped.where(Alert.id.in_(other_ids)))}
        names = _names(db, {lk.created_by for lk in links})
        for lk in links:
            other = lk.alert_b_id if lk.alert_a_id == alert.id else lk.alert_a_id
            if other not in visible:  # the other case is outside the actor's scope: not shown
                continue
            a, c = visible[other]
            add(
                a,
                c,
                cw.RelationReason(
                    kind="link",
                    label="Legătură adăugată de investigator",
                    link_id=lk.id,
                    reason=lk.reason,
                    created_by=names.get(lk.created_by, "utilizator"),
                    created_at=lk.created_at,
                    can_remove=lk.created_by == me or role == Role.tenant_admin,
                ),
            )

    run = run_id(alert)
    if alert.track_id is not None and run is not None:
        same_track = scoped.where(
            Alert.camera_id == alert.camera_id,
            Alert.id != alert.id,
            Alert.track_id == alert.track_id,
            Alert.details[RUN_ID_KEY].astext == run,
        )
        for a, c in db.execute(same_track.order_by(Alert.detected_at).limit(RELATED_LIMIT)):
            add(
                a,
                c,
                cw.RelationReason(
                    kind="same_track",
                    label=f"Același traseu #{alert.track_id}, aceeași cameră și rulare {run}",
                ),
            )

    before, after, _, _ = neighbours(db, scoped, alert)
    for a, c in [*before, *after]:
        add(
            a,
            c,
            cw.RelationReason(
                kind="same_camera_window",
                label=f"Aceeași cameră, {_minutes(a.detected_at - alert.detected_at)}",
            ),
        )

    return [
        cw.RelatedCase(
            number=a.number,
            type=a.event_type,
            type_label=_label(a.event_type),
            status=a.status.value,
            priority=a.priority.value,
            observed_at=a.detected_at.astimezone(UTC),
            camera_id=c.slug,
            reasons=reasons,
        )
        for a, c, reasons in sorted(found.values(), key=lambda t: (t[0].detected_at, t[0].number))
    ]


def add_link(
    db: Session,
    scoped: Select[Any],
    alert: Alert,
    other_number: int,
    reason: str,
    actor_id: uuid.UUID,
) -> tuple[CaseLink, Alert]:
    text = clean_text(reason, 300)
    row = db.execute(scoped.where(Alert.number == other_number)).first()
    if row is None:
        raise CaseError(
            404, "Cazul de legat nu există sau nu vă este accesibil.", "linked_case_not_found"
        )
    other: Alert = row[0]
    if other.id == alert.id:
        raise CaseError(422, "Un caz nu poate fi legat de el însuși.", "self_link")
    a, b = sorted((alert.id, other.id), key=lambda u: u.int)  # same order as PostgreSQL uuid
    link = CaseLink(
        tenant_id=alert.tenant_id, alert_a_id=a, alert_b_id=b, reason=text, created_by=actor_id
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CaseError(409, "Cazurile sunt deja legate.", "already_linked") from exc
    return link, other


def remove_link(
    db: Session, alert: Alert, link: CaseLink, actor_id: uuid.UUID, role: Role
) -> uuid.UUID:
    """Returns the id of the other case. The link row stays (soft removal)."""
    if alert.id not in (link.alert_a_id, link.alert_b_id) or link.removed_at is not None:
        raise CaseError(404, "Legătură inexistentă.", "not_found")
    if link.created_by != actor_id and role != Role.tenant_admin:
        raise CaseError(
            403, "Doar autorul sau un administrator poate elimina legătura.", "forbidden"
        )
    link.removed_at = datetime.now(UTC)
    link.removed_by = actor_id
    db.commit()
    return link.alert_b_id if link.alert_a_id == alert.id else link.alert_a_id


# --------------------------------------------------------------------------- follow-ups


def can_access(user: User, alert: Alert) -> bool:
    """Could ``user`` open and act on this case (follow-up assignee eligibility)?"""
    if not user.is_active or user.tenant_id != alert.tenant_id:
        return False
    if not has_permission(user.role, Permission.cases_annotate):
        return False
    if user.role == Role.patrol:
        return alert.assigned_to == user.id
    return has_permission(user.role, Permission.alerts_read)


def eligible_people(db: Session, alert: Alert, me: uuid.UUID, role: Role) -> list[cw.PersonOut]:
    """Assignable users. Roles that may assign cases (alerts:assign) see every eligible user
    of the tenant; others may only assign a follow-up to themselves."""
    stmt = select(User).where(User.is_active.is_(True)).order_by(User.display_name)
    if not has_permission(role, Permission.alerts_assign):
        stmt = stmt.where(User.id == me)
    return [
        cw.PersonOut(id=u.id, name=u.display_name, role=u.role.value, is_me=u.id == me)
        for u in db.scalars(stmt.limit(500))
        if can_access(u, alert)
    ]


def _check_assignee(
    db: Session, alert: Alert, assignee_id: uuid.UUID | None, me: uuid.UUID, role: Role
) -> None:
    if assignee_id is None:
        return
    if assignee_id != me and not has_permission(role, Permission.alerts_assign):
        raise CaseError(
            403, "Rolul dumneavoastră poate atribui sarcini doar sieși.", "assign_forbidden"
        )
    user = db.get(User, assignee_id)  # RLS: another tenant's user is simply not found
    if user is None or not can_access(user, alert):
        raise CaseError(
            422,
            "Responsabilul trebuie să fie un utilizator activ cu acces la acest caz.",
            "assignee_not_eligible",
        )


def _event(fu: CaseFollowup, actor_id: uuid.UUID, change: str) -> CaseFollowupEvent:
    return CaseFollowupEvent(
        tenant_id=fu.tenant_id,
        followup_id=fu.id,
        revision=fu.revision,
        actor_id=actor_id,
        change=change,
        status=fu.status,
        assignee_id=fu.assignee_id,
        due_date=fu.due_date,
    )


def _check_due(due: date | None, *, new: bool) -> None:
    if due is not None and new and due < datetime.now(UTC).date() - timedelta(days=1):
        raise CaseError(422, "Termenul nu poate fi în trecut.", "due_in_past")
    if due is not None and due.year > datetime.now(UTC).year + 5:
        raise CaseError(422, "Termen prea îndepărtat.", "due_too_far")


def add_followup(
    db: Session, alert: Alert, actor_id: uuid.UUID, role: Role, body: cw.FollowupIn
) -> CaseFollowup:
    text = clean_text(body.body, 500)
    _check_assignee(db, alert, body.assignee_id, actor_id, role)
    _check_due(body.due_date, new=True)
    count = db.scalar(
        select(CaseFollowup.id).where(CaseFollowup.alert_id == alert.id).offset(MAX_FOLLOWUPS - 1)
    )
    if count is not None:
        raise CaseError(422, "Prea multe sarcini pe acest caz.", "too_many_followups")
    fu = CaseFollowup(
        id=uuid.uuid4(),
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        author_id=actor_id,
        body=text,
        status=FollowupStatus.open.value,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
        revision=1,
        updated_at=datetime.now(UTC),
    )
    db.add(fu)
    db.flush()
    db.add(_event(fu, actor_id, "created"))
    db.commit()
    return fu


def get_followup(db: Session, alert: Alert, fu: CaseFollowup) -> CaseFollowup:
    if fu.alert_id != alert.id:
        raise CaseError(404, "Sarcină inexistentă.", "not_found")
    return fu


def update_followup(
    db: Session,
    alert: Alert,
    fu: CaseFollowup,
    actor_id: uuid.UUID,
    role: Role,
    body: cw.FollowupPatch,
) -> tuple[CaseFollowup, list[str]]:
    """Apply the provided fields; each change appends one history row. Returns the changes."""
    changes = body.model_fields_set - {"revision"}
    if not changes:
        raise CaseError(422, "Nicio modificare.", "no_change")
    if "status" in changes and body.status is None:
        raise CaseError(422, "Starea nu poate fi goală.", "bad_status")
    locked = db.scalar(
        select(CaseFollowup)
        .where(CaseFollowup.id == fu.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert locked is not None
    if locked.revision != body.revision:
        db.rollback()
        raise CaseError(409, "Sarcina a fost modificată între timp; reîncărcați.", "stale_revision")
    is_admin = role == Role.tenant_admin
    may_status = is_admin or actor_id in (locked.author_id, locked.assignee_id)
    may_reassign = is_admin or actor_id == locked.author_id
    applied: list[str] = []
    if "status" in changes and body.status != locked.status:
        if not may_status:
            db.rollback()
            raise CaseError(403, "Doar autorul, responsabilul sau un administrator.", "forbidden")
        if body.status not in TRANSITIONS[locked.status]:
            db.rollback()
            raise CaseError(
                409, f"Tranziție nepermisă: {locked.status} → {body.status}.", "bad_transition"
            )
        locked.status = str(body.status)
        applied.append("status")
    if "assignee_id" in changes and body.assignee_id != locked.assignee_id:
        if not may_reassign:
            db.rollback()
            raise CaseError(403, "Doar autorul sau un administrator.", "forbidden")
        try:
            _check_assignee(db, alert, body.assignee_id, actor_id, role)
        except CaseError:
            db.rollback()
            raise
        locked.assignee_id = body.assignee_id
        applied.append("assignee")
    if "due_date" in changes and body.due_date != locked.due_date:
        if not may_reassign:
            db.rollback()
            raise CaseError(403, "Doar autorul sau un administrator.", "forbidden")
        try:
            _check_due(body.due_date, new=True)
        except CaseError:
            db.rollback()
            raise
        locked.due_date = body.due_date
        applied.append("due_date")
    if not applied:
        db.rollback()
        raise CaseError(422, "Nicio modificare.", "no_change")
    for change in applied:
        locked.revision += 1
        db.add(_event(locked, actor_id, change))
    locked.updated_at = datetime.now(UTC)
    db.commit()
    return locked, applied


def followups_out(db: Session, alert: Alert, me: uuid.UUID, role: Role) -> list[cw.FollowupOut]:
    rows = list(
        db.scalars(
            select(CaseFollowup)
            .where(CaseFollowup.alert_id == alert.id)
            .order_by(CaseFollowup.created_at)
            .limit(MAX_FOLLOWUPS)
        )
    )
    if not rows:
        return []
    events = list(
        db.scalars(
            select(CaseFollowupEvent)
            .where(CaseFollowupEvent.followup_id.in_([f.id for f in rows]))
            .order_by(CaseFollowupEvent.followup_id, CaseFollowupEvent.revision)
        )
    )
    ids: set[uuid.UUID | None] = {f.author_id for f in rows}
    ids |= {f.assignee_id for f in rows}
    ids |= {e.actor_id for e in events}
    ids |= {e.assignee_id for e in events}
    names = _names(db, ids)
    by_fu: dict[uuid.UUID, list[CaseFollowupEvent]] = {}
    for e in events:
        by_fu.setdefault(e.followup_id, []).append(e)
    today = datetime.now(UTC).date()
    is_admin = role == Role.tenant_admin
    return [
        cw.FollowupOut(
            id=f.id,
            body=f.body,
            status=f.status,  # type: ignore[arg-type]
            author=names.get(f.author_id, "utilizator"),
            author_is_me=f.author_id == me,
            assignee_id=f.assignee_id,
            assignee=names.get(f.assignee_id) if f.assignee_id else None,
            assignee_is_me=f.assignee_id == me,
            due_date=f.due_date,
            overdue=f.status == "open" and f.due_date is not None and f.due_date < today,
            created_at=f.created_at,
            updated_at=f.updated_at,
            revision=f.revision,
            can_change_status=is_admin or me in (f.author_id, f.assignee_id),
            can_reassign=is_admin or me == f.author_id,
            history=[
                cw.FollowupEventOut(
                    revision=e.revision,
                    change=e.change,
                    status=e.status,  # type: ignore[arg-type]
                    assignee=names.get(e.assignee_id) if e.assignee_id else None,
                    due_date=e.due_date,
                    actor=names.get(e.actor_id, "utilizator"),
                    at=e.created_at,
                )
                for e in by_fu.get(f.id, [])
            ],
        )
        for f in rows
    ]


# --------------------------------------------------------------------------- references


def detection_reference(alert: Alert) -> cw.DetectionReference:
    box, status = recorded_bbox(alert)
    note = {
        "recorded": (
            "Chenarul și traseul sunt cele raportate de pipeline pentru detecție "
            "(coordonate în pixeli ai cadrului procesat). O notă le poate cita doar exact."
        ),
        "not_recorded": (
            "Pipeline-ul nu a trimis chenarul detecției pentru acest caz; o notă poate cita "
            "doar traseul înregistrat."
        ),
        "malformed": (
            "Chenarul raportat de pipeline nu are forma [x1, y1, x2, y2]; nu se folosește."
        ),
    }[status]
    return cw.DetectionReference(
        track_id=alert.track_id,
        bbox=box,
        bbox_status=status,  # type: ignore[arg-type]
        video_t_s=alert.video_t,
        run_id=run_id(alert),
        note=note,
    )
