"""Case dossier, investigator notes and timeline bookmarks.

A case is an existing alert (``alerts`` row). Callers resolve the alert through the role-scoped
lookup first (patrol users only reach assigned alerts); everything here runs inside the
caller's tenant-bound session, so RLS keeps every read and write in one tenant.

Edit policy (documented in docs/implementation/B-report.md):
* notes are versioned: an edit appends a revision (``case_note_revisions`` is INSERT-only);
  only the author may revise their own note, never after it was retracted;
* a note is never deleted: the author or a tenant admin may *retract* it with a reason;
  retracted notes stay visible (struck through) with who/when/why;
* bookmarks are removed softly by their author or a tenant admin;
* audit entries record ids, kinds, lengths and tags, never the note text.
"""

from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.audit import AuditAction, request_context
from app.core.catalog import ACTIONS, EVENT_TYPES
from app.core.policy import Permission, has_permission
from app.models import (
    Alert,
    AlertStatus,
    AuditLog,
    Camera,
    CaseBookmark,
    CaseNote,
    CaseNoteRevision,
    Evidence,
    NoteKind,
    Role,
    User,
)
from app.schemas import investigation as s
from app.schemas.contract import AuditEntry
from app.services import contract as view
from app.services import evidence as evidence_service

# Fixed, server-side tag catalog (key -> Romanian label). Clients cannot create labels.
NOTE_TAGS: dict[str, str] = {
    "vehicle_visible": "Vehicul clar vizibil",
    "occlusion": "Ocluzie / vizibilitate parțială",
    "low_light": "Iluminare slabă",
    "weather": "Condiții meteo",
    "possible_false_positive": "Posibil fals pozitiv",
    "calibration_doubt": "Calibrare îndoielnică",
    "needs_second_review": "Necesită a doua verificare",
    "context_needed": "Necesită context suplimentar",
}
REDACTION_LABELS = {
    "full": "Fețe și numere de înmatriculare estompate",
    "heads_only": "Doar capetele persoanelor estompate (numerele pot fi vizibile)",
}
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
EXTERNAL_EFFECT = (
    "Înregistrare internă. RoadSentinel nu trimite patrule, nu comandă panouri și nu emite "
    "amenzi; orice acțiune externă se face prin procedurile unității."
)
OBSERVATION_NOTE = (
    "Pipeline-ul raportează un singur moment al detecției (fără interval de urmărire); "
    "ora este a procesării de către pipeline."
)


class CaseError(Exception):
    def __init__(self, status_code: int, message: str, code: str) -> None:
        super().__init__(message)
        self.status_code, self.message, self.code = status_code, message, code


def audit_case(
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: AuditAction,
    alert: Alert,
    **details: Any,
) -> None:
    """Case-scoped audit entry (resource = the alert, so it shows in the case history and in
    patrol-scoped audit views). Adds the request correlation id when there is one."""
    ctx = request_context.get()
    if ctx and ctx.request_id:
        details["request_id"] = ctx.request_id
    audit.record(
        tenant_id,
        action,
        actor_id=actor_id,
        resource_type="alerts",
        resource_id=alert.id,
        details={"event_no": alert.number, **details},
    )


def clean_text(text: str, max_len: int) -> str:
    """Plain text only: strip control characters (keep newlines/tabs), trim, bound length.
    The UI renders it as text (React escapes it); no HTML/markdown is interpreted anywhere."""
    out = _CONTROL.sub("", text.replace("\r\n", "\n")).strip()
    if not out:
        raise CaseError(422, "Textul nu poate fi gol.", "empty_text")
    if len(out) > max_len:
        raise CaseError(422, f"Textul depășește {max_len} de caractere.", "text_too_long")
    return out


def clean_tags(tags: list[str]) -> list[str]:
    unknown = [t for t in tags if t not in NOTE_TAGS]
    if unknown:
        raise CaseError(422, "Etichetă necunoscută (se acceptă doar catalogul).", "unknown_tag")
    return sorted(set(tags))


def case_evidence(db: Session, alert: Alert) -> list[Evidence]:
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.alert_id == alert.id)
            .order_by(Evidence.created_at, Evidence.kind)
        )
    )


def _evidence_of_case(db: Session, alert: Alert, evidence_id: uuid.UUID) -> Evidence:
    ev = db.get(Evidence, evidence_id)  # RLS: another tenant's id is simply not found
    if ev is None or ev.alert_id != alert.id:
        raise CaseError(422, "Proba nu aparține acestui caz.", "evidence_not_in_case")
    return ev


def check_offset(db: Session, keyring: Any, ev: Evidence, offset_s: float) -> None:
    """A timestamp must exist in the evidence: 0 for a still image, within the clip length
    (read from the MP4 header) for a video. Unknown length -> refused, never guessed."""
    if not math.isfinite(offset_s) or offset_s < 0:
        raise CaseError(422, "Momentul trebuie să fie un număr pozitiv.", "bad_offset")
    if ev.purged_at is not None:
        raise CaseError(410, "Proba a fost ștearsă (purjată).", "evidence_purged")
    if not ev.content_type.startswith("video/"):
        if offset_s != 0:
            raise CaseError(422, "O imagine are un singur moment (0 s).", "offset_out_of_range")
        return
    try:
        duration = evidence_service.ensure_duration(db, keyring, ev)
    except FileNotFoundError as exc:
        raise CaseError(410, "Fișierul probei lipsește din stocare.", "evidence_missing") from exc
    if duration is None:
        if offset_s != 0:
            raise CaseError(
                422,
                "Durata clipului nu poate fi citită; se acceptă doar începutul (0 s).",
                "duration_unknown",
            )
        return
    if offset_s > duration:
        raise CaseError(
            422, f"Momentul depășește durata clipului ({duration:.2f} s).", "offset_out_of_range"
        )


def _validate_reference(
    db: Session,
    keyring: Any,
    alert: Alert,
    evidence_id: uuid.UUID | None,
    offset_s: float | None,
    track_id: int | None,
) -> None:
    if offset_s is not None and evidence_id is None:
        raise CaseError(
            422, "Momentul are nevoie de o probă de referință.", "offset_needs_evidence"
        )
    if evidence_id is not None:
        ev = _evidence_of_case(db, alert, evidence_id)
        if offset_s is not None:
            check_offset(db, keyring, ev, offset_s)
    if track_id is not None and track_id != alert.track_id:
        raise CaseError(
            422, "Traseul indicat nu este cel înregistrat pentru acest caz.", "track_not_in_case"
        )


# --------------------------------------------------------------------------- notes


def recorded_bbox(alert: Alert) -> tuple[list[float] | None, str]:
    """The detection box the pipeline recorded in ``details.bbox`` ([x1, y1, x2, y2], pixels
    in the pipeline's frame). The current pipeline does not send one: then not_recorded."""
    raw = (alert.details or {}).get("bbox")
    if raw is None:
        return None, "not_recorded"
    if (
        isinstance(raw, list)
        and len(raw) == 4
        and all(isinstance(v, int | float) and not isinstance(v, bool) for v in raw)
        and all(math.isfinite(float(v)) and 0 <= float(v) <= 100_000 for v in raw)
        and raw[0] < raw[2]
        and raw[1] < raw[3]
    ):
        return [float(v) for v in raw], "recorded"
    return None, "malformed"


def check_bbox(alert: Alert, bbox: list[float] | None) -> list[float] | None:
    if bbox is None:
        return None
    box, _ = recorded_bbox(alert)
    if box is None:
        raise CaseError(
            422,
            "Cazul nu are un chenar de detecție înregistrat; nu poate fi citat.",
            "bbox_not_recorded",
        )
    if len(bbox) != 4 or any(
        not math.isfinite(v) or abs(v - r) > 1e-6 for v, r in zip(bbox, box, strict=True)
    ):
        raise CaseError(
            422, "Chenarul indicat nu este cel înregistrat pentru acest caz.", "bbox_not_in_case"
        )
    return box


def add_note(
    db: Session, keyring: Any, alert: Alert, author_id: uuid.UUID, body: s.NoteIn
) -> CaseNote:
    text = clean_text(body.body, 4000)
    tags = clean_tags(body.tags)
    _validate_reference(db, keyring, alert, body.evidence_id, body.offset_s, body.track_id)
    bbox = check_bbox(alert, body.bbox)
    note = CaseNote(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        author_id=author_id,
        kind=NoteKind(body.kind).value,
        current_revision=1,
    )
    db.add(note)
    db.flush()
    db.add(
        CaseNoteRevision(
            tenant_id=alert.tenant_id,
            note_id=note.id,
            revision=1,
            author_id=author_id,
            body=text,
            tags=tags,
            evidence_id=body.evidence_id,
            offset_s=body.offset_s,
            track_id=body.track_id,
            bbox=bbox,
        )
    )
    db.commit()
    return note


def get_note(db: Session, alert: Alert, note_id: uuid.UUID) -> CaseNote:
    note = db.get(CaseNote, note_id)
    if note is None or note.alert_id != alert.id:
        raise CaseError(404, "Notă inexistentă.", "not_found")
    return note


def revise_note(
    db: Session,
    keyring: Any,
    alert: Alert,
    note: CaseNote,
    actor_id: uuid.UUID,
    body: s.NoteReviseIn,
) -> int:
    if note.author_id != actor_id:
        raise CaseError(403, "Doar autorul își poate modifica nota.", "not_author")
    if note.retracted_at is not None:
        raise CaseError(409, "Nota a fost retrasă și nu mai poate fi modificată.", "retracted")
    text = clean_text(body.body, 4000)
    tags = clean_tags(body.tags)
    _validate_reference(db, keyring, alert, body.evidence_id, body.offset_s, body.track_id)
    bbox = check_bbox(alert, body.bbox)
    # Row lock: two concurrent edits of one note get consecutive revisions, never the same.
    locked = db.scalar(
        select(CaseNote)
        .where(CaseNote.id == note.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert locked is not None
    if locked.retracted_at is not None:
        raise CaseError(409, "Nota a fost retrasă și nu mai poate fi modificată.", "retracted")
    revision = locked.current_revision + 1
    db.add(
        CaseNoteRevision(
            tenant_id=alert.tenant_id,
            note_id=note.id,
            revision=revision,
            author_id=actor_id,
            body=text,
            tags=tags,
            evidence_id=body.evidence_id,
            offset_s=body.offset_s,
            track_id=body.track_id,
            bbox=bbox,
        )
    )
    locked.current_revision = revision
    db.commit()
    return revision


def retract_note(db: Session, note: CaseNote, actor_id: uuid.UUID, role: Role, reason: str) -> None:
    if note.author_id != actor_id and role != Role.tenant_admin:
        raise CaseError(403, "Doar autorul sau un administrator poate retrage nota.", "forbidden")
    if note.retracted_at is not None:
        raise CaseError(409, "Nota este deja retrasă.", "retracted")
    note.retracted_at = datetime.now(UTC)
    note.retracted_by = actor_id
    note.retract_reason = clean_text(reason, 500)
    db.commit()


def _names(db: Session, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids_ = {i for i in ids if i}
    if not ids_:
        return {}
    return dict(db.execute(select(User.id, User.display_name).where(User.id.in_(ids_))).all())


def notes_out(
    db: Session, alert: Alert, me: uuid.UUID, role: Role, *, kind: str | None = None
) -> list[s.NoteOut]:
    stmt = select(CaseNote).where(CaseNote.alert_id == alert.id).order_by(CaseNote.created_at)
    if kind:
        stmt = stmt.where(CaseNote.kind == kind)
    notes = list(db.scalars(stmt))
    if not notes:
        return []
    revs = {
        (r.note_id, r.revision): r
        for r in db.scalars(
            select(CaseNoteRevision).where(CaseNoteRevision.note_id.in_([n.id for n in notes]))
        )
    }
    ids: set[uuid.UUID | None] = {n.author_id for n in notes}
    ids |= {n.retracted_by for n in notes}
    names = _names(db, ids)
    out = []
    for n in notes:
        cur = revs[(n.id, n.current_revision)]
        open_ = n.retracted_at is None
        out.append(
            s.NoteOut(
                id=n.id,
                kind=n.kind,  # type: ignore[arg-type]
                author=names.get(n.author_id, "utilizator"),
                author_is_me=n.author_id == me,
                created_at=n.created_at,
                updated_at=cur.created_at,
                revision=n.current_revision,
                body=cur.body,
                tags=list(cur.tags or []),
                evidence_id=cur.evidence_id,
                offset_s=cur.offset_s,
                track_id=cur.track_id,
                bbox=cur.bbox,
                retracted_at=n.retracted_at,
                retracted_by=names.get(n.retracted_by) if n.retracted_by else None,
                retract_reason=n.retract_reason,
                can_revise=open_ and n.author_id == me,
                can_retract=open_ and (n.author_id == me or role == Role.tenant_admin),
            )
        )
    return out


def note_history(db: Session, note: CaseNote) -> list[s.NoteRevisionOut]:
    revs = list(
        db.scalars(
            select(CaseNoteRevision)
            .where(CaseNoteRevision.note_id == note.id)
            .order_by(CaseNoteRevision.revision)
        )
    )
    names = _names(db, {r.author_id for r in revs})
    return [
        s.NoteRevisionOut(
            revision=r.revision,
            author=names.get(r.author_id, "utilizator"),
            created_at=r.created_at,
            body=r.body,
            tags=list(r.tags or []),
            evidence_id=r.evidence_id,
            offset_s=r.offset_s,
            track_id=r.track_id,
            bbox=r.bbox,
        )
        for r in revs
    ]


# --------------------------------------------------------------------------- bookmarks


def add_bookmark(
    db: Session, keyring: Any, alert: Alert, author_id: uuid.UUID, body: s.BookmarkIn
) -> CaseBookmark:
    label = clean_text(body.label, 120)
    ev = _evidence_of_case(db, alert, body.evidence_id)
    check_offset(db, keyring, ev, body.offset_s)
    bm = CaseBookmark(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        evidence_id=ev.id,
        offset_s=round(body.offset_s, 3),
        label=label,
        author_id=author_id,
    )
    db.add(bm)
    db.commit()
    return bm


def remove_bookmark(
    db: Session, alert: Alert, bookmark_id: uuid.UUID, actor_id: uuid.UUID, role: Role
) -> CaseBookmark:
    bm = db.get(CaseBookmark, bookmark_id)
    if bm is None or bm.alert_id != alert.id or bm.removed_at is not None:
        raise CaseError(404, "Marcaj inexistent.", "not_found")
    if bm.author_id != actor_id and role != Role.tenant_admin:
        raise CaseError(
            403, "Doar autorul sau un administrator poate șterge marcajul.", "forbidden"
        )
    bm.removed_at = datetime.now(UTC)
    bm.removed_by = actor_id
    db.commit()
    return bm


def bookmarks_out(db: Session, alert: Alert, me: uuid.UUID, role: Role) -> list[s.BookmarkOut]:
    rows = list(
        db.scalars(
            select(CaseBookmark)
            .where(CaseBookmark.alert_id == alert.id, CaseBookmark.removed_at.is_(None))
            .order_by(CaseBookmark.evidence_id, CaseBookmark.offset_s, CaseBookmark.created_at)
        )
    )
    names = _names(db, {b.author_id for b in rows})
    return [
        s.BookmarkOut(
            id=b.id,
            evidence_id=b.evidence_id,
            offset_s=b.offset_s,
            label=b.label,
            author=names.get(b.author_id, "utilizator"),
            created_at=b.created_at,
            can_remove=b.author_id == me or role == Role.tenant_admin,
        )
        for b in rows
    ]


# --------------------------------------------------------------------------- history

# Chain action -> case history label. Text bodies are never part of these entries.
HISTORY_ACTIONS: dict[str, str] = {
    AuditAction.alert_created.value: "detected",
    AuditAction.alert_viewed.value: "viewed",
    AuditAction.alert_confirmed.value: "confirmed",
    AuditAction.alert_rejected.value: "rejected",
    AuditAction.alert_assigned.value: "assigned",
    AuditAction.alert_vlm_verdict.value: "vlm_verdict",
    AuditAction.alert_decision_conflict.value: "decision_conflict",
    AuditAction.case_note_created.value: "note_created",
    AuditAction.case_note_revised.value: "note_revised",
    AuditAction.case_note_retracted.value: "note_retracted",
    AuditAction.case_bookmark_created.value: "bookmark_created",
    AuditAction.case_bookmark_removed.value: "bookmark_removed",
    AuditAction.evidence_missing.value: "evidence_missing",
    AuditAction.export_requested.value: "export_requested",
    AuditAction.export_queued.value: "export_approved",
    AuditAction.export_denied.value: "export_denied",
    AuditAction.export_canceled.value: "export_canceled",
    AuditAction.export_generated.value: "export_generated",
    AuditAction.export_failed.value: "export_failed",
    AuditAction.export_downloaded.value: "export_downloaded",
    AuditAction.export_expired.value: "export_expired",
    AuditAction.case_link_created.value: "link_created",
    AuditAction.case_link_removed.value: "link_removed",
    AuditAction.case_followup_created.value: "followup_created",
    AuditAction.case_followup_updated.value: "followup_updated",
    AuditAction.legal_hold_placed.value: "legal_hold_placed",
    AuditAction.legal_hold_released.value: "legal_hold_released",
    AuditAction.evidence_purge_refused.value: "purge_refused",
}


def _history_note(e: AuditLog) -> str | None:
    d = e.details or {}
    if e.action in (AuditAction.alert_confirmed.value, AuditAction.alert_rejected.value):
        return d.get("note")
    if e.action == AuditAction.alert_vlm_verdict.value:
        return f"VLM: {d.get('verdict')}"
    if "export_id" in d:
        return f"export {str(d['export_id'])[:8]}" + (
            f" · manifest {str(d['manifest_sha256'])[:12]}…" if d.get("manifest_sha256") else ""
        )
    if "other_event_no" in d:
        return f"caz #{d['other_event_no']}"
    if "followup_id" in d:
        changes = ", ".join(d.get("changes") or [])
        return f"sarcină {str(d['followup_id'])[:8]}" + (f" · {changes}" if changes else "")
    if "hold_id" in d:
        return f"reținere {str(d['hold_id'])[:8]}"
    if "note_id" in d:
        return f"notă {str(d['note_id'])[:8]} rev. {d.get('revision', 1)}"
    if "attempted" in d:
        return f"încercare {d['attempted']} respinsă (deja {d.get('current_status')})"
    return None


def case_history(db: Session, alert: Alert) -> list[AuditEntry]:
    entries = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "alerts",
                AuditLog.resource_id == str(alert.id),
                AuditLog.action.in_(list(HISTORY_ACTIONS)),
            )
            .order_by(AuditLog.seq)
        )
    )
    names = _names(db, {e.actor_id for e in entries})
    return [
        AuditEntry(
            id=e.seq,
            event_id=alert.number,
            actor=(
                f"vlm:{e.details.get('model', 'unknown')}"
                if e.action == AuditAction.alert_vlm_verdict.value
                else names.get(e.actor_id, "utilizator") if e.actor_id else "system"
            ),
            action=HISTORY_ACTIONS[e.action],
            note=_history_note(e),
            at=e.ts.astimezone(UTC),
            type=alert.event_type,
        )
        for e in entries
    ]


# --------------------------------------------------------------------------- dossier


def _str_or_none(value: object) -> str | None:
    return value[:200] if isinstance(value, str) and value.strip() else None


def provenance(alert: Alert) -> s.Provenance:
    details = dict(alert.details or {})
    raw_source = details.get("source_kind")
    if raw_source in ("live", "recorded_replay"):
        source, basis = raw_source, "Raportat de pipeline în detaliile evenimentului."
    else:
        source = "unknown"
        basis = (
            "Pipeline-ul nu raportează dacă intrarea a fost flux live sau înregistrare redată; "
            "nu se deduce."
        )
    model_id = _str_or_none(details.get("model_id") or details.get("model"))
    model_hash = _str_or_none(details.get("model_hash") or details.get("model_sha256"))
    recorded = {k: v for k, v in details.items() if k not in ("vlm", "redaction")}
    return s.Provenance(
        source_kind=source,
        source_basis=basis,
        model_id=model_id,
        model_hash=model_hash,
        model_status="recorded" if model_id or model_hash else "not_recorded",
        speed_kmh=alert.speed_kmh,
        speed_status="uncalibrated_estimate" if alert.speed_kmh is not None else "not_applicable",
        recorded_details=recorded,
    )


def evidence_items(user_id: uuid.UUID, files: list[Evidence]) -> list[s.EvidenceItem]:
    out = []
    for ev in files:
        state = evidence_service.storage_state(ev)
        out.append(
            s.EvidenceItem(
                id=ev.id,
                kind=ev.kind,
                content_type=ev.content_type,
                redaction=ev.redaction,
                redaction_label=REDACTION_LABELS.get(ev.redaction, ev.redaction),
                original_exists=evidence_service.has_distinct_original(ev),
                size_bytes=ev.size_bytes,
                sha256_recorded=bool(ev.sha256 and len(ev.sha256) == 64),
                storage_state=state,  # type: ignore[arg-type]
                purged_at=ev.purged_at,
                duration_s=ev.duration_s,
                media_url=view.media_url(user_id, ev.id) if state == "available" else None,
            )
        )
    return out


def dossier(
    db: Session, alert: Alert, camera: Camera, user_id: uuid.UUID, role: Role
) -> s.CaseDossier:
    tz = ZoneInfo(camera.timezone)
    observed = alert.detected_at.astimezone(UTC)
    names = _names(db, {alert.decided_by})
    return s.CaseDossier(
        number=alert.number,
        status=alert.status.value,
        priority=alert.priority.value,
        type=alert.event_type,
        type_label=EVENT_TYPES.get(alert.event_type, (None, alert.event_type))[1],
        camera_id=camera.slug,
        camera_name=camera.name,
        location=camera.location,
        timezone=camera.timezone,
        observed_at=observed,
        observed_at_local=observed.astimezone(tz).isoformat(),
        first_observed_at=observed,
        last_observed_at=None,
        observation_note=OBSERVATION_NOTE,
        video_t_s=alert.video_t,
        track_id=alert.track_id,
        object_class=alert.object_class,
        rule=alert.rule or alert.description,
        provenance=provenance(alert),
        evidence=evidence_items(user_id, case_evidence(db, alert)),
        decision=s.DecisionOut(
            status=alert.status.value,
            action=alert.action,
            action_label=ACTIONS.get(alert.action or ""),
            note=alert.decision_note,
            decided_by=names.get(alert.decided_by) if alert.decided_by else None,
            decided_at=alert.decided_at,
            external_effect=EXTERNAL_EFFECT,
        ),
        notes=notes_out(db, alert, user_id, role),
        bookmarks=bookmarks_out(db, alert, user_id, role),
        history=case_history(db, alert),
        permissions=s.CasePermissions(
            can_decide=has_permission(role, Permission.alerts_decide)
            and alert.status == AlertStatus.new,
            can_annotate=has_permission(role, Permission.cases_annotate),
            can_request_export=has_permission(role, Permission.approvals_request),
            can_approve_export=has_permission(role, Permission.approvals_decide),
        ),
        tag_catalog=NOTE_TAGS,
    )
