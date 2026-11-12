"""Investigation workspace API (Workstream B): case dossier, notes, bookmarks, archive search
with keyset pagination, saved filters, and controlled evidence-package export.

Every route resolves the case through the role-scoped alert query (patrol users only reach
alerts assigned to them) inside the caller's RLS-bound session; ids of another tenant or of
another case are answered with 404, exactly like ids that do not exist."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select

from app.config import get_settings
from app.core.audit import AuditAction
from app.core.crypto import sign_url_params, verify_url_params
from app.core.policy import Permission, can_view_alert, has_permission, scope_alerts
from app.deps import Principal, get_principal, not_found, require, require_fresh_mfa
from app.models import (
    Alert,
    ApprovalRequest,
    Camera,
    CaseBookmark,
    CaseNote,
    ExportJob,
    Role,
    SavedSearch,
    User,
)
from app.schemas import investigation as s
from app.services import archive, casework
from app.services import contract as view
from app.services import exports as export_service
from app.services import investigation as inv
from app.services import search as search_service
from app.services.exports import ExportError
from app.services.investigation import CaseError, audit_case

# Display exclusions sent by the UI: applied to queries, never saved or copied into the audit.
EXCLUSIONS = {"exclude_types", "exclude_numbers"}

router = APIRouter(tags=["investigation"])

PACKAGE_PURPOSE = "export_package"


def error_response(exc: CaseError | ExportError) -> JSONResponse:
    return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status_code)


@contextmanager
def _denials_audited(principal: Principal, alert: Alert) -> Iterator[None]:
    """A refused action leaves a scoped audit record (reason code only, no payload)."""
    try:
        yield
    except (CaseError, ExportError) as exc:
        if exc.status_code in (403, 410):
            audit_case(
                principal.tenant_id,
                principal.user_id,
                AuditAction.access_denied,
                alert,
                reason=exc.code,
            )
        raise


def scoped(principal: Principal) -> Any:
    """Every case the actor may open (tenant by RLS, patrol: assigned only)."""
    return scope_alerts(view.visible_alerts(), principal)


def _case(principal: Principal, number: int) -> tuple[Alert, Camera]:
    row = principal.db.execute(scoped(principal).where(Alert.number == number)).first()
    if row is None:
        raise HTTPException(404, "Eveniment inexistent.")
    return row[0], row[1]


# --------------------------------------------------------------------------- dossier


@router.get("/api/events/{number}/case", response_model=s.CaseDossier)
def case_dossier(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> s.CaseDossier:
    alert, camera = _case(principal, number)
    db, me, role = principal.db, principal.user_id, principal.role
    out = inv.dossier(db, alert, camera, me, role)
    out.related = casework.related_cases(db, scoped(principal), alert, me, role)
    out.context = casework.timeline_context(db, scoped(principal), alert)
    out.followups = casework.followups_out(db, alert, me, role)
    out.legal_hold = casework.hold_state(db, alert, role)
    out.detection_ref = casework.detection_reference(alert)
    return out


# --------------------------------------------------------------------------- notes


def _note_out(principal: Principal, alert: Alert, note_id: uuid.UUID) -> s.NoteOut:
    [out] = [
        n
        for n in inv.notes_out(principal.db, alert, principal.user_id, principal.role)
        if n.id == note_id
    ]
    return out


@router.get("/api/events/{number}/notes", response_model=list[s.NoteOut])
def list_notes(
    number: int,
    kind: s.NoteKindName | None = None,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[s.NoteOut]:
    alert, _ = _case(principal, number)
    return inv.notes_out(principal.db, alert, principal.user_id, principal.role, kind=kind)


@router.post("/api/events/{number}/notes", response_model=s.NoteOut, status_code=201)
def create_note(
    number: int,
    body: s.NoteIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> s.NoteOut:
    alert, _ = _case(principal, number)
    note = inv.add_note(principal.db, principal.keyring, alert, principal.user_id, body)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_note_created,
        alert,
        note_id=str(note.id),
        kind=note.kind,
        revision=1,
        body_length=len(body.body),
        tags=sorted(set(body.tags)),
        evidence_id=str(body.evidence_id) if body.evidence_id else None,
    )
    return _note_out(principal, alert, note.id)


def _get_note(principal: Principal, alert: Alert, note_id: uuid.UUID) -> CaseNote:
    if principal.db.get(CaseNote, note_id) is None:
        not_found(principal, "case_notes", note_id)  # audits a probe of another tenant's id
    return inv.get_note(principal.db, alert, note_id)


@router.get(
    "/api/events/{number}/notes/{note_id}/revisions", response_model=list[s.NoteRevisionOut]
)
def note_revisions(
    number: int,
    note_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[s.NoteRevisionOut]:
    alert, _ = _case(principal, number)
    return inv.note_history(principal.db, _get_note(principal, alert, note_id))


@router.post("/api/events/{number}/notes/{note_id}/revisions", response_model=s.NoteOut)
def revise_note(
    number: int,
    note_id: uuid.UUID,
    body: s.NoteReviseIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> s.NoteOut:
    alert, _ = _case(principal, number)
    note = _get_note(principal, alert, note_id)
    with _denials_audited(principal, alert):
        revision = inv.revise_note(
            principal.db, principal.keyring, alert, note, principal.user_id, body
        )
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_note_revised,
        alert,
        note_id=str(note.id),
        revision=revision,
        previous_revision=revision - 1,
        body_length=len(body.body),
        tags=sorted(set(body.tags)),
    )
    return _note_out(principal, alert, note.id)


@router.post("/api/events/{number}/notes/{note_id}/retract", response_model=s.NoteOut)
def retract_note(
    number: int,
    note_id: uuid.UUID,
    body: s.RetractIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> s.NoteOut:
    alert, _ = _case(principal, number)
    note = _get_note(principal, alert, note_id)
    with _denials_audited(principal, alert):
        inv.retract_note(principal.db, note, principal.user_id, principal.role, body.reason)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_note_retracted,
        alert,
        note_id=str(note.id),
        revision=note.current_revision,
        reason_length=len(body.reason),
        by_author=note.author_id == principal.user_id,
    )
    return _note_out(principal, alert, note.id)


# --------------------------------------------------------------------------- bookmarks


@router.get("/api/events/{number}/bookmarks", response_model=list[s.BookmarkOut])
def list_bookmarks(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> list[s.BookmarkOut]:
    alert, _ = _case(principal, number)
    return inv.bookmarks_out(principal.db, alert, principal.user_id, principal.role)


@router.post("/api/events/{number}/bookmarks", response_model=s.BookmarkOut, status_code=201)
def create_bookmark(
    number: int,
    body: s.BookmarkIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> s.BookmarkOut:
    alert, _ = _case(principal, number)
    bm = inv.add_bookmark(principal.db, principal.keyring, alert, principal.user_id, body)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_bookmark_created,
        alert,
        bookmark_id=str(bm.id),
        evidence_id=str(bm.evidence_id),
        offset_s=bm.offset_s,
    )
    [out] = [
        b
        for b in inv.bookmarks_out(principal.db, alert, principal.user_id, principal.role)
        if b.id == bm.id
    ]
    return out


@router.delete("/api/events/{number}/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(
    number: int,
    bookmark_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> Response:
    alert, _ = _case(principal, number)
    if principal.db.get(CaseBookmark, bookmark_id) is None:
        not_found(principal, "case_bookmarks", bookmark_id)
    with _denials_audited(principal, alert):
        bm = inv.remove_bookmark(
            principal.db, alert, bookmark_id, principal.user_id, principal.role
        )
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_bookmark_removed,
        alert,
        bookmark_id=str(bm.id),
    )
    return Response(status_code=204)


# --------------------------------------------------------------------------- archive


@router.post("/api/archive/search", response_model=s.ArchivePage)
def archive_search(
    body: s.ArchiveSearchIn, principal: Principal = Depends(require(Permission.alerts_read))
) -> s.ArchivePage | JSONResponse:
    """POST, not GET: the text may contain plates or names and URLs end up in access logs."""
    q, filters, cursor, limit = body.q, body.filters, body.cursor, body.limit
    if filters.assigned_to and not has_permission(principal.role, Permission.alerts_assign):
        # Patrol users stay assigned-only; assignments of others are not theirs to filter.
        principal.audit(
            AuditAction.access_denied, details={"reason": "assignment_filter_forbidden"}
        )
        return JSONResponse(
            {
                "detail": "Rolul dumneavoastră nu poate filtra după responsabil.",
                "code": "assignment_filter_forbidden",
            },
            status_code=403,
        )
    base = scoped(principal)
    try:
        rows, next_cursor, total, parsed = archive.run(
            principal.db,
            base,
            user_id=principal.user_id,
            q=q,
            filters=filters,
            cursor=cursor,
            limit=limit,
        )
    except archive.CursorError:
        return JSONResponse(
            {
                "detail": "Cursor invalid: nu aparține acestei căutări sau acestui utilizator.",
                "code": "bad_cursor",
            },
            status_code=400,
        )
    if not cursor:
        # Audit without the query text (it may contain personal data).
        principal.audit(
            AuditAction.alert_search,
            details={
                "query_length": len(q or ""),
                "filters": filters.model_dump(
                    mode="json", exclude_defaults=True, exclude=EXCLUSIONS
                ),
                "results": total,
                "archive": True,
            },
        )
    assignee = (
        {uuid.UUID(filters.assigned_to)}
        if filters.assigned_to and filters.assigned_to != "unassigned"
        else set()
    )
    names = (
        dict(
            principal.db.execute(
                select(User.id, User.display_name).where(User.id.in_(assignee))
            ).all()
        )
        if assignee
        else {}
    )
    return s.ArchivePage(
        results=view.to_events(principal.db, principal.user_id, rows),
        applied_filters=[s.FilterChip(**c) for c in archive.filter_chips(filters, names)],
        next_cursor=next_cursor,
        total=total,
        sort=archive.SORT,
        filter=parsed,
        interpretation=[
            s.TokenInterpretation(**t)  # type: ignore[arg-type]
            for t in (search_service.interpret(q) if q else [])
        ],
    )


@router.get("/api/archive/saved", response_model=list[s.SavedSearchOut])
def saved_searches(
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[s.SavedSearchOut]:
    rows = principal.db.scalars(
        select(SavedSearch)
        .where(SavedSearch.owner_id == principal.user_id)
        .order_by(SavedSearch.created_at.desc())
        .limit(100)
    )
    return [
        s.SavedSearchOut(id=r.id, name=r.name, filters=r.filters, created_at=r.created_at)
        for r in rows
    ]


@router.post("/api/archive/saved", response_model=s.SavedSearchOut, status_code=201)
def save_search(
    body: s.SavedSearchIn, principal: Principal = Depends(require(Permission.alerts_read))
) -> s.SavedSearchOut:
    row = SavedSearch(
        tenant_id=principal.tenant_id,
        owner_id=principal.user_id,
        name=inv.clean_text(body.name, 80),
        filters=body.filters.model_dump(mode="json", exclude_defaults=True, exclude=EXCLUSIONS),
    )
    principal.db.add(row)
    principal.db.commit()
    principal.audit(
        AuditAction.saved_search_created,
        resource_type="saved_searches",
        resource_id=row.id,
        details={"filter_keys": sorted(row.filters)},
    )
    return s.SavedSearchOut(
        id=row.id, name=row.name, filters=row.filters, created_at=row.created_at
    )


@router.delete("/api/archive/saved/{search_id}", status_code=204)
def delete_saved_search(
    search_id: uuid.UUID, principal: Principal = Depends(require(Permission.alerts_read))
) -> Response:
    row = principal.db.get(SavedSearch, search_id)
    if row is None:
        not_found(principal, "saved_searches", search_id)
    if row.owner_id != principal.user_id:
        raise HTTPException(404, "Not found")
    principal.db.delete(row)
    principal.db.commit()
    principal.audit(
        AuditAction.saved_search_deleted, resource_type="saved_searches", resource_id=search_id
    )
    return Response(status_code=204)


# --------------------------------------------------------------------------- exports


def _export_out(principal: Principal, job: ExportJob, number: int) -> s.ExportOut:
    db = principal.db
    approval = db.get(ApprovalRequest, job.approval_id) if job.approval_id else None
    ids = {job.requester_id, approval.decided_by if approval else None}
    names = dict(
        db.execute(
            select(User.id, User.display_name).where(User.id.in_([i for i in ids if i]))
        ).all()
    )
    return s.ExportOut(
        id=job.id,
        event_id=number,
        state=job.state,
        include_original=job.include_original,
        requester=names.get(job.requester_id, "utilizator"),
        requested_by_me=job.requester_id == principal.user_id,
        created_at=job.created_at,
        approval_id=job.approval_id,
        approval_status=approval.status.value if approval else None,
        approved_by=(names.get(approval.decided_by) if approval and approval.decided_by else None),
        attempt=job.attempt,
        error=job.error,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        manifest_sha256=job.manifest_sha256,
        package_sha256=job.package_sha256,
        package_size=job.package_size,
        file_count=job.file_count,
        legal_hold=casework.is_held(db, job.alert_id),
        storage_retries=job.storage_retries,
    )


def _job(principal: Principal, export_id: uuid.UUID) -> tuple[ExportJob, Alert]:
    """Requester, or a tenant admin (approvals:read_all), who can also see the case."""
    job = principal.db.get(ExportJob, export_id)
    if job is None:
        not_found(principal, "export_jobs", export_id)
    alert = principal.db.get(Alert, job.alert_id)
    if (
        alert is None
        or not can_view_alert(principal, alert)
        or not (
            job.requester_id == principal.user_id
            or has_permission(principal.role, Permission.approvals_read_all)
        )
    ):
        raise HTTPException(404, "Not found")
    return job, alert


def _expire(principal: Principal, job: ExportJob, alert: Alert) -> None:
    if export_service.expire_if_due(principal.db, job):
        audit_case(
            principal.tenant_id,
            None,
            AuditAction.export_expired,
            alert,
            export_id=str(job.id),
        )


@router.get("/api/events/{number}/exports", response_model=list[s.ExportOut])
def list_exports(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> list[s.ExportOut]:
    alert, _ = _case(principal, number)
    stmt = select(ExportJob).where(ExportJob.alert_id == alert.id)
    if not has_permission(principal.role, Permission.approvals_read_all):
        stmt = stmt.where(ExportJob.requester_id == principal.user_id)
    jobs = list(principal.db.scalars(stmt.order_by(ExportJob.created_at.desc()).limit(50)))
    for job in jobs:
        _expire(principal, job, alert)
    return [_export_out(principal, j, alert.number) for j in jobs]


@router.post("/api/events/{number}/exports", response_model=s.ExportOut, status_code=201)
def request_export(
    number: int,
    body: s.ExportIn,
    response: Response,
    principal: Principal = Depends(require(Permission.approvals_request)),
) -> s.ExportOut:
    require_fresh_mfa(principal)
    alert, _ = _case(principal, number)
    try:
        job, created = export_service.request_export(
            principal.db, alert=alert, requester_id=principal.user_id, body=body
        )
    except ExportError as exc:
        principal.db.rollback()
        audit_case(
            principal.tenant_id,
            principal.user_id,
            AuditAction.access_denied if exc.status_code == 403 else AuditAction.export_failed,
            alert,
            reason=exc.code,
            include_original=body.include_original,
        )
        raise
    if created:
        audit_case(
            principal.tenant_id,
            principal.user_id,
            AuditAction.export_requested,
            alert,
            export_id=str(job.id),
            approval_id=str(job.approval_id),
            include_original=job.include_original,
            files=len(job.evidence_ids),
            case_reference=body.case_reference,
        )
    else:
        response.status_code = 200  # idempotent replay
    return _export_out(principal, job, alert.number)


@router.get("/api/exports/{export_id}", response_model=s.ExportOut)
def get_export(export_id: uuid.UUID, principal: Principal = Depends(get_principal)) -> s.ExportOut:
    job, alert = _job(principal, export_id)
    _expire(principal, job, alert)
    return _export_out(principal, job, alert.number)


@router.post("/api/exports/{export_id}/run", response_model=s.ExportOut)
def run_export(export_id: uuid.UUID, principal: Principal = Depends(get_principal)) -> s.ExportOut:
    """In-request generation (small packages): claims this job atomically and builds it. If
    another worker holds it, the current state is returned unchanged (poll it)."""
    job, alert = _job(principal, export_id)
    claimed = export_service.claim(principal.db, export_service.worker_id(), job.id)
    if claimed is not None:
        job = export_service.process(principal.db, principal.keyring, claimed)
    else:
        principal.db.refresh(job)
    return _export_out(principal, job, alert.number)


@router.post("/api/exports/{export_id}/cancel", response_model=s.ExportOut)
def cancel_export(
    export_id: uuid.UUID, principal: Principal = Depends(get_principal)
) -> s.ExportOut:
    job, alert = _job(principal, export_id)
    with _denials_audited(principal, alert):
        job = export_service.cancel(
            principal.db, job, principal.user_id, principal.role == Role.tenant_admin
        )
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.export_canceled,
        alert,
        export_id=str(job.id),
    )
    return _export_out(principal, job, alert.number)


def _package_resource(job_id: uuid.UUID) -> str:
    return f"{job_id}:package"


def _signing_key() -> bytes:
    return get_settings().url_signing_key.get_secret_value().encode()


@router.post("/api/exports/{export_id}/link", response_model=s.ExportLinkOut)
def export_link(
    export_id: uuid.UUID, principal: Principal = Depends(get_principal)
) -> s.ExportLinkOut:
    require_fresh_mfa(principal)
    job, alert = _job(principal, export_id)
    _expire(principal, job, alert)
    try:
        export_service.check_downloadable(principal.db, job, principal.user_id)
    except ExportError as exc:
        audit_case(
            principal.tenant_id,
            principal.user_id,
            AuditAction.access_denied,
            alert,
            export_id=str(job.id),
            reason=exc.code,
        )
        raise
    exp = int(time.time()) + get_settings().signed_url_ttl_seconds
    sig = sign_url_params(
        _signing_key(), PACKAGE_PURPOSE, _package_resource(job.id), str(principal.user_id), exp
    )
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.export_link_issued,
        alert,
        export_id=str(job.id),
    )
    return s.ExportLinkOut(
        url=f"/api/exports/{job.id}/download?{urlencode({'exp': exp, 'sig': sig})}",
        expires_at=datetime.fromtimestamp(exp, UTC),
    )


@router.get("/api/exports/{export_id}/download")
def download_export(
    export_id: uuid.UUID,
    exp: int = Query(),
    sig: str = Query(max_length=100),
    principal: Principal = Depends(get_principal),
) -> StreamingResponse:
    if not verify_url_params(
        _signing_key(),
        PACKAGE_PURPOSE,
        _package_resource(export_id),
        str(principal.user_id),
        exp,
        sig,
    ):
        principal.audit(
            AuditAction.access_denied,
            resource_type="export_jobs",
            resource_id=export_id,
            details={"reason": "bad_or_expired_link"},
        )
        raise HTTPException(403, "Link invalid sau expirat.")
    job, alert = _job(principal, export_id)  # tenant + case visibility re-checked now
    _expire(principal, job, alert)
    with _denials_audited(principal, alert):
        export_service.check_downloadable(principal.db, job, principal.user_id)
    stream = export_service.open_package(principal.keyring, job)
    try:
        first = next(stream)
    except FileNotFoundError as exc:
        raise HTTPException(410, "Pachetul nu mai există în stocare.") from exc
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.export_downloaded,
        alert,
        export_id=str(job.id),
        manifest_sha256=job.manifest_sha256,
    )

    def body() -> Any:
        yield first
        yield from stream

    return StreamingResponse(
        body(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="roadsentinel-caz-{alert.number}-{str(job.id)[:8]}.zip"'
            ),
            "Cache-Control": "no-store",
            **({"Content-Length": str(job.package_size)} if job.package_size else {}),
        },
    )
