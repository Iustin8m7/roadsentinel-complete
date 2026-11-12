"""Four-eyes approval endpoints (unblur and export requests share one generic model)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.evidence import get_visible_evidence, require_original
from app.core.audit import AuditAction
from app.core.policy import Permission, has_permission
from app.deps import Principal, get_principal, not_found, require, require_fresh_mfa
from app.models import ApprovalRequest, ApprovalStatus
from app.schemas.approvals import ApprovalDecisionIn, ApprovalIn, ApprovalOut
from app.services import approvals as svc
from app.services import exports as export_service
from app.services.approvals import ApprovalError

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _out(req: ApprovalRequest) -> ApprovalOut:
    out = ApprovalOut.model_validate(req)
    out.grant_active = svc.is_grant_active(req)
    return out


def _get(principal: Principal, request_id: uuid.UUID) -> ApprovalRequest:
    req = principal.db.get(ApprovalRequest, request_id)
    visible = req is not None and (
        has_permission(principal.role, Permission.approvals_read_all)
        or req.requester_id == principal.user_id
    )
    if not visible:
        not_found(principal, "approval_requests", request_id)
    assert req is not None
    return req


def _raise(exc: ApprovalError) -> None:
    raise HTTPException(exc.status_code, exc.message) from exc


@router.post("", response_model=ApprovalOut, status_code=201)
def create_request(
    body: ApprovalIn, principal: Principal = Depends(require(Permission.approvals_request))
) -> ApprovalOut:
    ev = get_visible_evidence(principal, body.evidence_id)
    require_original(principal, ev)
    req = svc.create_request(
        principal.db,
        tenant_id=principal.tenant_id,
        kind=body.kind,
        resource_type="evidence",
        resource_id=ev.id,
        requester_id=principal.user_id,
        justification=body.justification,
        case_reference=body.case_reference,
    )
    principal.db.commit()
    principal.audit(
        AuditAction.approval_requested,
        resource_type="approval_requests",
        resource_id=req.id,
        details={
            "kind": req.kind.value,
            "evidence_id": str(ev.id),
            "case_reference": req.case_reference,
            "justification": req.justification,
        },
    )
    return _out(req)


@router.get("", response_model=list[ApprovalOut])
def list_requests(
    status: ApprovalStatus | None = None, principal: Principal = Depends(get_principal)
) -> list[ApprovalOut]:
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(200)
    if not has_permission(principal.role, Permission.approvals_read_all):
        stmt = stmt.where(ApprovalRequest.requester_id == principal.user_id)
    if status is not None:
        stmt = stmt.where(ApprovalRequest.status == status)
    return [_out(r) for r in principal.db.scalars(stmt).all()]


@router.get("/{request_id}", response_model=ApprovalOut)
def get_request(
    request_id: uuid.UUID, principal: Principal = Depends(get_principal)
) -> ApprovalOut:
    return _out(_get(principal, request_id))


@router.post("/{request_id}/approve", response_model=ApprovalOut)
def approve(
    request_id: uuid.UUID,
    body: ApprovalDecisionIn | None = None,
    principal: Principal = Depends(require(Permission.approvals_decide)),
) -> ApprovalOut:
    require_fresh_mfa(principal)
    req = _get(principal, request_id)
    try:
        svc.approve(principal.db, req, principal.user_id, body.note if body else None)
        export_service.on_approval_decided(principal.db, req)
    except ApprovalError as exc:
        if exc.status_code == 403:
            principal.audit(
                AuditAction.approval_self_approval_blocked,
                resource_type="approval_requests",
                resource_id=req.id,
            )
        _raise(exc)
    principal.db.commit()
    principal.audit(
        AuditAction.approval_approved,
        resource_type="approval_requests",
        resource_id=req.id,
        details={
            "kind": req.kind.value,
            "requester_id": str(req.requester_id),
            "grant_expires_at": req.grant_expires_at.isoformat() if req.grant_expires_at else None,
        },
    )
    return _out(req)


@router.post("/{request_id}/deny", response_model=ApprovalOut)
def deny(
    request_id: uuid.UUID,
    body: ApprovalDecisionIn | None = None,
    principal: Principal = Depends(require(Permission.approvals_decide)),
) -> ApprovalOut:
    require_fresh_mfa(principal)
    req = _get(principal, request_id)
    try:
        svc.deny(principal.db, req, principal.user_id, body.note if body else None)
        export_service.on_approval_decided(principal.db, req)
    except ApprovalError as exc:
        _raise(exc)
    principal.db.commit()
    principal.audit(
        AuditAction.approval_denied, resource_type="approval_requests", resource_id=req.id
    )
    return _out(req)


@router.post("/{request_id}/revoke", response_model=ApprovalOut)
def revoke(request_id: uuid.UUID, principal: Principal = Depends(get_principal)) -> ApprovalOut:
    """A tenant admin, or the requester themselves, can end a grant early."""
    req = _get(principal, request_id)
    if not (
        has_permission(principal.role, Permission.approvals_decide)
        or req.requester_id == principal.user_id
    ):
        raise HTTPException(403, "Forbidden")
    try:
        svc.revoke(principal.db, req)
        export_service.on_approval_decided(principal.db, req)
    except ApprovalError as exc:
        _raise(exc)
    principal.db.commit()
    principal.audit(
        AuditAction.approval_revoked, resource_type="approval_requests", resource_id=req.id
    )
    return _out(req)
