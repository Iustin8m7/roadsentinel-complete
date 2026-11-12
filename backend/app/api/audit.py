from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.audit import AuditAction, verify_chain
from app.core.policy import Permission
from app.deps import Principal, require
from app.models import AuditLog
from app.schemas.audit import AuditEntryOut, AuditVerifyOut

# The raw chain lives at /api/audit/chain; GET /api/audit is the API.md view (app.api.contract).
router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/chain", response_model=list[AuditEntryOut])
def list_entries(
    before_seq: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(require(Permission.audit_read)),
) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.tenant_id == principal.tenant_id)
    if before_seq is not None:
        stmt = stmt.where(AuditLog.seq < before_seq)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return list(principal.db.scalars(stmt.order_by(AuditLog.seq.desc()).limit(limit)).all())


@router.get("/verify", response_model=AuditVerifyOut)
def verify(principal: Principal = Depends(require(Permission.audit_verify))) -> AuditVerifyOut:
    result = verify_chain(principal.db, principal.tenant_id)
    principal.audit(
        AuditAction.audit_verified,
        details={
            "ok": result.ok,
            "checked": result.checked,
            "first_broken_seq": result.first_broken_seq,
            "reason": result.reason,
        },
    )
    return AuditVerifyOut(
        ok=result.ok,
        checked=result.checked,
        first_broken_seq=result.first_broken_seq,
        reason=result.reason,
        head_hash=result.head_hash,
    )
