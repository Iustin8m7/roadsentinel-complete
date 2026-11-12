"""Investigation completion API: related cases and explicit links, follow-up items, manual
legal hold, the archive's assignee list, uploaded-package verification and the auditor's
per-evidence integrity view.

Case routes resolve the case through the same role-scoped lookup as the rest of the
investigation API (patrol: assigned cases only); ids of another tenant answer 404 and are
recorded as cross-tenant probes in both tenants' audit chains (``not_found``)."""

from __future__ import annotations

import base64
import hashlib
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, tuple_

from app.api.investigation import _case, _denials_audited, scoped
from app.core.audit import AuditAction, request_context
from app.core.crypto import CryptoError
from app.core.policy import Permission, can_view_alert, has_permission
from app.core.rate_limit import Limit, ip_key
from app.deps import Principal, get_principal, not_found, require, require_fresh_mfa
from app.models import (
    Alert,
    Camera,
    CaseFollowup,
    CaseLink,
    Evidence,
    ExportJob,
    Role,
    User,
)
from app.schemas import casework as cw
from app.services import casework
from app.services import evidence as evidence_service
from app.services import exports as export_service
from app.services.auth import check_rate
from app.services.investigation import audit_case
from app.services.package_verify import verify_package

router = APIRouter(tags=["investigation"])

VERIFY_MAX_BYTES = export_service.MAX_PACKAGE_BYTES + 16 * 1024 * 1024
VERIFY_PER_USER = Limit(10, 300)
VERIFY_PER_IP = Limit(30, 300)
ZIP_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream"}
INTEGRITY_VERIFY_MAX = 20


# --------------------------------------------------------------------------- related / links


@router.get("/api/events/{number}/related", response_model=list[cw.RelatedCase])
def related(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> list[cw.RelatedCase]:
    alert, _ = _case(principal, number)
    return casework.related_cases(
        principal.db, scoped(principal), alert, principal.user_id, principal.role
    )


@router.post("/api/events/{number}/links", response_model=list[cw.RelatedCase], status_code=201)
def add_link(
    number: int,
    body: cw.LinkIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> list[cw.RelatedCase]:
    alert, _ = _case(principal, number)
    link, other = casework.add_link(
        principal.db, scoped(principal), alert, body.number, body.reason, principal.user_id
    )
    for this, that in ((alert, other), (other, alert)):
        audit_case(
            principal.tenant_id,
            principal.user_id,
            AuditAction.case_link_created,
            this,
            link_id=str(link.id),
            other_event_no=that.number,
            reason_length=len(link.reason),
        )
    return related(number, principal)


@router.delete("/api/events/{number}/links/{link_id}", status_code=204)
def remove_link(
    number: int,
    link_id: uuid.UUID,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> Response:
    alert, _ = _case(principal, number)
    link = principal.db.get(CaseLink, link_id)
    if link is None:
        not_found(principal, "case_links", link_id)
    with _denials_audited(principal, alert):
        other_id = casework.remove_link(
            principal.db, alert, link, principal.user_id, principal.role
        )
    other = principal.db.get(Alert, other_id)
    for this, that in ((alert, other), (other, alert)):
        if this is None or that is None:
            continue
        audit_case(
            principal.tenant_id,
            principal.user_id,
            AuditAction.case_link_removed,
            this,
            link_id=str(link_id),
            other_event_no=that.number,
        )
    return Response(status_code=204)


# --------------------------------------------------------------------------- follow-ups


@router.get("/api/events/{number}/followups", response_model=list[cw.FollowupOut])
def list_followups(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> list[cw.FollowupOut]:
    alert, _ = _case(principal, number)
    return casework.followups_out(principal.db, alert, principal.user_id, principal.role)


@router.get("/api/events/{number}/followup-assignees", response_model=list[cw.PersonOut])
def followup_assignees(
    number: int, principal: Principal = Depends(require(Permission.cases_annotate))
) -> list[cw.PersonOut]:
    alert, _ = _case(principal, number)
    return casework.eligible_people(principal.db, alert, principal.user_id, principal.role)


def _followup_out(principal: Principal, alert: Alert, fu_id: uuid.UUID) -> cw.FollowupOut:
    [out] = [
        f
        for f in casework.followups_out(principal.db, alert, principal.user_id, principal.role)
        if f.id == fu_id
    ]
    return out


@router.post("/api/events/{number}/followups", response_model=cw.FollowupOut, status_code=201)
def create_followup(
    number: int,
    body: cw.FollowupIn,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> cw.FollowupOut:
    alert, _ = _case(principal, number)
    with _denials_audited(principal, alert):
        fu = casework.add_followup(principal.db, alert, principal.user_id, principal.role, body)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_followup_created,
        alert,
        followup_id=str(fu.id),
        revision=1,
        body_length=len(fu.body),
        assignee_id=str(fu.assignee_id) if fu.assignee_id else None,
        due_date=fu.due_date.isoformat() if fu.due_date else None,
    )
    return _followup_out(principal, alert, fu.id)


@router.patch("/api/events/{number}/followups/{followup_id}", response_model=cw.FollowupOut)
def update_followup(
    number: int,
    followup_id: uuid.UUID,
    body: cw.FollowupPatch,
    principal: Principal = Depends(require(Permission.cases_annotate)),
) -> cw.FollowupOut:
    alert, _ = _case(principal, number)
    fu = principal.db.get(CaseFollowup, followup_id)
    if fu is None:
        not_found(principal, "case_followups", followup_id)
    casework.get_followup(principal.db, alert, fu)
    previous = {"status": fu.status, "assignee_id": fu.assignee_id, "due_date": fu.due_date}
    with _denials_audited(principal, alert):
        fu, changes = casework.update_followup(
            principal.db, alert, fu, principal.user_id, principal.role, body
        )
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.case_followup_updated,
        alert,
        followup_id=str(fu.id),
        revision=fu.revision,
        changes=changes,
        from_status=previous["status"],
        to_status=fu.status,
        assignee_id=str(fu.assignee_id) if fu.assignee_id else None,
        previous_assignee_id=(str(previous["assignee_id"]) if previous["assignee_id"] else None),
        due_date=fu.due_date.isoformat() if fu.due_date else None,
    )
    return _followup_out(principal, alert, fu.id)


# --------------------------------------------------------------------------- legal hold


@router.get("/api/events/{number}/legal-hold", response_model=cw.LegalHoldState)
def legal_hold(
    number: int, principal: Principal = Depends(require(Permission.alerts_read))
) -> cw.LegalHoldState:
    alert, _ = _case(principal, number)
    return casework.hold_state(principal.db, alert, principal.role)


@router.post("/api/events/{number}/legal-hold", response_model=cw.LegalHoldState, status_code=201)
def place_legal_hold(
    number: int,
    body: cw.LegalHoldIn,
    principal: Principal = Depends(require(Permission.cases_legal_hold)),
) -> cw.LegalHoldState:
    require_fresh_mfa(principal)
    alert, _ = _case(principal, number)
    hold = casework.place_hold(principal.db, alert, principal.user_id, body.reason)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.legal_hold_placed,
        alert,
        hold_id=str(hold.id),
        reason_length=len(hold.reason),
    )
    return casework.hold_state(principal.db, alert, principal.role)


@router.post("/api/events/{number}/legal-hold/release", response_model=cw.LegalHoldState)
def release_legal_hold(
    number: int,
    body: cw.LegalHoldIn,
    principal: Principal = Depends(require(Permission.cases_legal_hold)),
) -> cw.LegalHoldState:
    require_fresh_mfa(principal)
    alert, _ = _case(principal, number)
    hold = casework.release_hold(principal.db, alert, principal.user_id, body.reason)
    audit_case(
        principal.tenant_id,
        principal.user_id,
        AuditAction.legal_hold_released,
        alert,
        hold_id=str(hold.id),
        reason_length=len(body.reason),
    )
    # Normal expiry resumes now for this case's packages (nothing else is affected).
    for job in export_service.expire_due(principal.db, alert.id):
        audit_case(
            principal.tenant_id, None, AuditAction.export_expired, alert, export_id=str(job.id)
        )
    return casework.hold_state(principal.db, alert, principal.role)


# --------------------------------------------------------------------------- archive


@router.get("/api/archive/assignees", response_model=list[cw.PersonOut])
def archive_assignees(
    principal: Principal = Depends(require(Permission.alerts_assign)),
) -> list[cw.PersonOut]:
    """Users cases can be assigned to (active patrol users), for the archive filter."""
    rows = principal.db.scalars(
        select(User)
        .where(User.role == Role.patrol, User.is_active.is_(True))
        .order_by(User.display_name)
        .limit(500)
    )
    return [
        cw.PersonOut(
            id=u.id, name=u.display_name, role=u.role.value, is_me=u.id == principal.user_id
        )
        for u in rows
    ]


# --------------------------------------------------------------------------- package verify


def _record_for(principal: Principal, manifest_sha256: str | None) -> cw.ServerRecord | None:
    """The export job that produced this manifest, only if the caller may see that job."""
    if not manifest_sha256:
        return None
    for job in principal.db.scalars(
        select(ExportJob).where(ExportJob.manifest_sha256 == manifest_sha256).limit(5)
    ):
        alert = principal.db.get(Alert, job.alert_id)
        if (
            alert is not None
            and can_view_alert(principal, alert)
            and (
                job.requester_id == principal.user_id
                or has_permission(principal.role, Permission.approvals_read_all)
            )
        ):
            return cw.ServerRecord(export_id=job.id, event_id=alert.number, state=job.state)
    return None


def _finish_verify(
    principal: Principal, path: Path, size: int, expected: str | None
) -> cw.PackageVerifyOut:
    report = verify_package(path, expected, max_uncompressed=VERIFY_MAX_BYTES * 2)
    record = _record_for(principal, report.manifest_sha256)
    if expected:
        note = "Amprenta manifestului a fost comparată cu cea indicată de dumneavoastră."
    elif record is not None:
        note = (
            "Manifestul este cel generat de acest server pentru exportul indicat "
            "(amprenta din jurnalul de audit, export.generated)."
        )
    else:
        note = (
            "Pachetul este doar auto-consistent: nu s-a găsit un export vizibil cu această "
            "amprentă și nu ați indicat amprenta oficială. Un pachet rescris complet nu poate "
            "fi detectat fără amprenta din jurnalul de audit."
        )
    principal.audit(
        AuditAction.package_verified,
        resource_type="export_jobs" if record else None,
        resource_id=record.export_id if record else None,
        details={
            "ok": report.ok,
            "files_checked": report.files_checked,
            "errors": len(report.errors),
            "bytes": size,
            "expected_digest_given": bool(expected),
            "server_record": record is not None,
        },
    )
    return cw.PackageVerifyOut(
        ok=report.ok,
        manifest_sha256=report.manifest_sha256,
        expected_manifest_sha256=expected.lower() if expected else None,
        files_checked=report.files_checked,
        errors=report.errors[:50],
        size_bytes=size,
        server_record=record,
        note=note,
    )


@router.post("/api/exports/verify", response_model=cw.PackageVerifyOut)
async def verify_uploaded_package(
    request: Request,
    manifest_sha256: str | None = Query(default=None, pattern=r"^[0-9a-fA-F]{64}$"),
    principal: Principal = Depends(get_principal),
) -> cw.PackageVerifyOut:
    """Verify an evidence package (raw ZIP body, at most ``VERIFY_MAX_BYTES``). The upload is
    streamed to a private temporary file, checked with the offline verifier and deleted; it
    is never stored. Any signed-in user may verify (no tenant data is needed for the digests);
    the server record is only reported for a job the caller could already see."""
    ctx = request_context.get()
    await run_in_threadpool(
        check_rate,
        (f"pkgverify:user:{principal.user_id}", VERIFY_PER_USER),
        (ip_key("pkgverify", ctx.ip if ctx else None), VERIFY_PER_IP),
        tenant_id=principal.tenant_id,
    )
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype not in ZIP_TYPES:
        raise HTTPException(415, "Încărcați arhiva .zip a pachetului (application/zip).")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > VERIFY_MAX_BYTES:
        raise HTTPException(413, "Fișierul depășește dimensiunea maximă a unui pachet.")
    work = Path(tempfile.mkdtemp(prefix="rs-verify-"))
    path, size = work / "package.zip", 0
    try:
        with open(path, "wb") as fh:
            async for chunk in request.stream():
                size += len(chunk)
                if size > VERIFY_MAX_BYTES:
                    raise HTTPException(413, "Fișierul depășește dimensiunea maximă a unui pachet.")
                fh.write(chunk)
        return await run_in_threadpool(_finish_verify, principal, path, size, manifest_sha256)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- auditor integrity


def _cursor(created_at: datetime, ev_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{ev_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        ts, ev_id = raw.split("|")
        return datetime.fromisoformat(ts), uuid.UUID(ev_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "Cursor invalid.") from exc


def _integrity(principal: Principal, ev: Evidence, state: str, verify: bool) -> str:
    if state != "available":
        return state
    if not (ev.sha256 and len(ev.sha256) == 64):
        return "no_hash"
    if not verify:
        return "not_checked"
    digest = hashlib.sha256()
    try:
        # The ingest hash covers the original plaintext (the only copy when one file was sent).
        for chunk in evidence_service.open_decrypted(principal.keyring, ev, "original"):
            digest.update(chunk)
    except FileNotFoundError:
        return "missing"
    except evidence_service.StorageUnavailableError:
        return "unavailable"
    except (CryptoError, ValueError):
        return "unreadable"  # ciphertext fails authentication: altered or wrong key
    return "match" if digest.hexdigest() == ev.sha256 else "mismatch"


@router.get("/api/audit/evidence", response_model=cw.EvidenceIntegrityPage)
def evidence_integrity(
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=25, ge=1, le=100),
    verify: bool = False,
    principal: Principal = Depends(require(Permission.audit_verify)),
) -> cw.EvidenceIntegrityPage:
    """Per-evidence chain-of-custody status: SHA-256 recorded at ingest, stored file present,
    and (``verify=true``, at most 20 items) whether the decrypted original still matches it.
    Read-only; returns ids and states, never content."""
    if verify and limit > INTEGRITY_VERIFY_MAX:
        raise HTTPException(422, f"Verificarea completă acceptă cel mult {INTEGRITY_VERIFY_MAX}.")
    db = principal.db
    total = db.scalar(select(func.count()).select_from(Evidence)) or 0
    stmt = select(Evidence)
    if cursor:
        ts, ev_id = _decode_cursor(cursor)
        stmt = stmt.where(tuple_(Evidence.created_at, Evidence.id) < tuple_(ts, ev_id))
    rows = list(
        db.scalars(stmt.order_by(Evidence.created_at.desc(), Evidence.id.desc()).limit(limit + 1))
    )
    more = len(rows) > limit
    rows = rows[:limit]
    alert_ids = {e.alert_id for e in rows if e.alert_id}
    alerts = (
        {a.id: a for a in db.scalars(select(Alert).where(Alert.id.in_(alert_ids)))}
        if alert_ids
        else {}
    )
    camera_ids = {e.camera_id for e in rows if e.camera_id} | {a.camera_id for a in alerts.values()}
    slugs = (
        dict(db.execute(select(Camera.id, Camera.slug).where(Camera.id.in_(camera_ids))).all())
        if camera_ids
        else {}
    )
    items = []
    for ev in rows:
        alert = alerts.get(ev.alert_id) if ev.alert_id else None
        state = evidence_service.storage_state(ev, "original")
        cam = ev.camera_id or (alert.camera_id if alert else None)
        items.append(
            cw.EvidenceIntegrityItem(
                id=ev.id,
                kind=ev.kind,
                event_id=alert.number if alert else None,
                camera_id=slugs.get(cam) if cam else None,
                created_at=ev.created_at,
                size_bytes=ev.size_bytes,
                sha256_recorded=bool(ev.sha256 and len(ev.sha256) == 64),
                distinct_original=evidence_service.has_distinct_original(ev),
                storage_state=state,  # type: ignore[arg-type]
                integrity=_integrity(principal, ev, state, verify),  # type: ignore[arg-type]
            )
        )
    if verify:
        counts: dict[str, int] = {}
        for item in items:
            counts[item.integrity] = counts.get(item.integrity, 0) + 1
        principal.audit(
            AuditAction.evidence_integrity_checked,
            details={"checked": len(items), "results": counts},
        )
    return cw.EvidenceIntegrityPage(
        items=items,
        next_cursor=_cursor(rows[-1].created_at, rows[-1].id) if more and rows else None,
        total=total,
        verified=verify,
        note=(
            "Amprenta SHA-256 a fost luată la preluare, pe originalul primit de la pipeline. "
            "Verificarea decriptează originalul pe server și o recalculează; conținutul nu "
            "părăsește serverul. Totul rulează pe același sistem: este o verificare de "
            "integritate, nu o custodie independentă."
        ),
    )
