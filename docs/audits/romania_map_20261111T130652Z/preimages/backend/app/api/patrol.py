"""Patrol workflow: who is available, and the assignee's status updates on an alert."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select

from app.api.alerts import get_visible_alert, to_out
from app.core.audit import AuditAction
from app.core.policy import Permission
from app.deps import Principal, require
from app.models import Alert, Role, User
from app.schemas.ops import AlertOut

router = APIRouter(tags=["patrol"])

ORDER = ("assigned", "en_route", "on_scene", "done")


class PatrolOut(BaseModel):
    id: uuid.UUID
    display_name: str
    open_assignments: int


class PatrolStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["en_route", "on_scene", "done"]


@router.get("/api/patrols", response_model=list[PatrolOut])
def list_patrols(
    principal: Principal = Depends(require(Permission.alerts_assign)),
) -> list[PatrolOut]:
    """Real patrol accounts of this unit with their open assignments. No positions: the system has
    no location source for patrols, so none are shown."""
    open_counts = dict(
        principal.db.execute(
            select(Alert.assigned_to, func.count())
            .where(
                Alert.assigned_to.is_not(None),
                or_(Alert.patrol_status.is_(None), Alert.patrol_status != "done"),
                Alert.superseded_at.is_(None),
            )
            .group_by(Alert.assigned_to)
        ).all()
    )
    users = principal.db.scalars(
        select(User)
        .where(User.role == Role.patrol, User.is_active.is_(True))
        .order_by(User.display_name)
    )
    return [
        PatrolOut(id=u.id, display_name=u.display_name, open_assignments=open_counts.get(u.id, 0))
        for u in users
    ]


@router.post("/api/alerts/{alert_id}/patrol-status", response_model=AlertOut)
def set_patrol_status(
    alert_id: uuid.UUID,
    body: PatrolStatusIn,
    principal: Principal = Depends(require(Permission.patrol_respond)),
) -> AlertOut:
    """Only the patrol the alert is assigned to; forward only (en route -> on scene -> done)."""
    alert = get_visible_alert(principal, alert_id)
    if alert.assigned_to != principal.user_id:
        principal.audit(
            AuditAction.access_denied,
            resource_type="alerts",
            resource_id=alert.id,
            details={"reason": "not_assignee"},
        )
        raise HTTPException(403, "This alert is not assigned to you")
    current = alert.patrol_status or "assigned"
    if ORDER.index(body.status) <= ORDER.index(current):
        raise HTTPException(409, f"Status can only move forward (now: {current})")
    alert.patrol_status, alert.patrol_status_at = body.status, datetime.now(UTC)
    principal.db.commit()
    principal.audit(
        AuditAction.patrol_status,
        resource_type="alerts",
        resource_id=alert.id,
        details={"from": current, "to": body.status},
    )
    return to_out(principal, alert)
