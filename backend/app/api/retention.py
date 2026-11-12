"""Retention policy, legal hold and the purge job (tenant admins)."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.alerts import get_visible_alert
from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, require, require_fresh_mfa
from app.models import RETENTION_KINDS
from app.services import retention as svc

router = APIRouter(prefix="/api/retention", tags=["retention"])
manage = require(Permission.retention_manage)


class PolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: dict[Literal["keyframe", "clip", "camera_video", "confirmed_case"], int] = Field(
        min_length=1
    )


class PolicyOut(BaseModel):
    days: dict[str, int]
    defaults: dict[str, int]
    due_now: int
    held_skipped: int


class PurgeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    confirm: str | None = None  # must be "PURGE" for a real run


class PurgeOut(BaseModel):
    dry_run: bool
    candidates: int
    purged: int
    held_skipped: int
    errors: int
    by_kind: dict[str, int]


class HoldIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=10, max_length=500)


@router.get("", response_model=PolicyOut)
def get_policy(principal: Principal = Depends(manage)) -> PolicyOut:
    due, held = svc.find_due(principal.db)
    return PolicyOut(
        days=svc.policy(principal.db),
        defaults=svc.DEFAULT_DAYS,
        due_now=len(due),
        held_skipped=held,
    )


@router.put("", response_model=PolicyOut)
def put_policy(body: PolicyIn, principal: Principal = Depends(manage)) -> PolicyOut:
    require_fresh_mfa(principal)
    for kind, days in body.days.items():
        if kind not in RETENTION_KINDS or not 1 <= days <= 3650:
            raise HTTPException(422, f"{kind}: days must be between 1 and 3650")
    before = svc.policy(principal.db)
    after = svc.set_policy(
        principal.db,
        principal.tenant_id,
        {str(k): v for k, v in body.days.items()},
        principal.user_id,
    )
    principal.db.commit()
    principal.audit(
        AuditAction.retention_policy_changed,
        resource_type="retention_policies",
        details={"before": before, "after": after},
    )
    due, held = svc.find_due(principal.db)
    return PolicyOut(days=after, defaults=svc.DEFAULT_DAYS, due_now=len(due), held_skipped=held)


@router.post("/purge", response_model=PurgeOut)
def purge(body: PurgeIn, principal: Principal = Depends(manage)) -> PurgeOut:
    """Dry-run by default. A real purge needs fresh MFA and the word PURGE; it cannot be undone."""
    if not body.dry_run:
        require_fresh_mfa(principal)
        if body.confirm != "PURGE":
            raise HTTPException(422, 'confirm must be "PURGE" for a real run')
    rep = svc.purge(
        principal.db, principal.tenant_id, dry_run=body.dry_run, actor_id=principal.user_id
    )
    return PurgeOut(
        dry_run=rep.dry_run,
        candidates=rep.candidates,
        purged=rep.purged,
        held_skipped=rep.held_skipped,
        errors=rep.errors,
        by_kind=rep.by_kind,
    )


@router.post("/holds/{alert_id}", status_code=204)
def set_hold(alert_id: uuid.UUID, body: HoldIn, principal: Principal = Depends(manage)) -> None:
    require_fresh_mfa(principal)
    alert = get_visible_alert(principal, alert_id)
    from datetime import UTC, datetime

    alert.legal_hold, alert.legal_hold_reason = True, body.reason
    alert.legal_hold_by, alert.legal_hold_at = principal.user_id, datetime.now(UTC)
    principal.db.commit()
    principal.audit(
        AuditAction.legal_hold_set,
        resource_type="alerts",
        resource_id=alert.id,
        details={"reason": body.reason},
    )


@router.delete("/holds/{alert_id}", status_code=204)
def release_hold(alert_id: uuid.UUID, principal: Principal = Depends(manage)) -> None:
    require_fresh_mfa(principal)
    alert = get_visible_alert(principal, alert_id)
    alert.legal_hold = False
    principal.db.commit()
    principal.audit(AuditAction.legal_hold_released, resource_type="alerts", resource_id=alert.id)
