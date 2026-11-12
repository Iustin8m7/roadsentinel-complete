"""Generic four-eyes approvals (unblur, export). An approved request is a time-limited grant
for the *requester* on one resource; the approver must be a different tenant admin."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApprovalKind, ApprovalRequest, ApprovalStatus


class ApprovalError(Exception):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC)


def create_request(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    kind: ApprovalKind,
    resource_type: str,
    resource_id: uuid.UUID,
    requester_id: uuid.UUID,
    justification: str,
    case_reference: str,
) -> ApprovalRequest:
    req = ApprovalRequest(
        tenant_id=tenant_id,
        kind=kind,
        resource_type=resource_type,
        resource_id=resource_id,
        requester_id=requester_id,
        justification=justification.strip(),
        case_reference=case_reference.strip(),
        status=ApprovalStatus.pending,
    )
    db.add(req)
    db.flush()
    return req


def approve(db: Session, req: ApprovalRequest, approver_id: uuid.UUID, note: str | None) -> None:
    # Enforced here, server-side, regardless of what the UI shows.
    if req.requester_id == approver_id:
        raise ApprovalError("Requester cannot approve their own request", 403)
    if req.status != ApprovalStatus.pending:
        raise ApprovalError("Request is not pending")
    now = _now()
    req.status = ApprovalStatus.approved
    req.decided_by = approver_id
    req.decided_at = now
    req.decision_note = note
    req.grant_expires_at = now + timedelta(seconds=get_settings().grant_ttl_seconds)
    db.flush()


def deny(db: Session, req: ApprovalRequest, approver_id: uuid.UUID, note: str | None) -> None:
    if req.requester_id == approver_id:
        raise ApprovalError("Requester cannot decide their own request", 403)
    if req.status != ApprovalStatus.pending:
        raise ApprovalError("Request is not pending")
    req.status = ApprovalStatus.denied
    req.decided_by = approver_id
    req.decided_at = _now()
    req.decision_note = note
    db.flush()


def revoke(db: Session, req: ApprovalRequest) -> None:
    if req.status not in (ApprovalStatus.approved, ApprovalStatus.pending):
        raise ApprovalError("Request cannot be revoked")
    req.status = ApprovalStatus.revoked
    req.grant_expires_at = _now() if req.grant_expires_at else None
    db.flush()


def is_grant_active(req: ApprovalRequest) -> bool:
    return (
        req.status == ApprovalStatus.approved
        and req.grant_expires_at is not None
        and req.grant_expires_at > _now()
    )


def active_grant(
    db: Session, *, kind: ApprovalKind, resource_id: uuid.UUID, user_id: uuid.UUID
) -> ApprovalRequest | None:
    return db.scalars(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.kind == kind,
            ApprovalRequest.resource_id == resource_id,
            ApprovalRequest.requester_id == user_id,
            ApprovalRequest.status == ApprovalStatus.approved,
            ApprovalRequest.grant_expires_at > _now(),
        )
        .order_by(ApprovalRequest.grant_expires_at.desc())
        .limit(1)
    ).first()
