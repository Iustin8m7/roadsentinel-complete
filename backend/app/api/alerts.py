from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select

from app.core.audit import AuditAction
from app.core.crypto import blind_index, decrypt_field, encrypt_field, mask_plate, normalize_plate
from app.core.policy import Permission, can_view_alert, has_permission, scope_alerts
from app.deps import Principal, not_found, require
from app.models import Alert, AlertStatus, Camera, Evidence, Priority, Role, User
from app.schemas.ops import AlertAssignIn, AlertDecisionIn, AlertIn, AlertOut
from app.services.push import notify_new_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

PLATE_FIELD = "alerts.plate"
_priority_rank = case(
    {Priority.critical: 0, Priority.high: 1, Priority.medium: 2, Priority.info: 3},
    value=Alert.priority,
)


def mark_first_viewed(principal: Principal, alert: Alert) -> None:
    """Response-time statistics: the first time someone who can decide opens an alert.
    Viewing by a patrol or an auditor is not an operator action and does not count."""
    if alert.first_viewed_at is None and has_permission(principal.role, Permission.alerts_decide):
        alert.first_viewed_at = datetime.now(UTC)
        principal.db.commit()


def to_out(principal: Principal, alert: Alert, camera_name: str | None = None) -> AlertOut:
    masked = None
    if alert.plate_enc is not None:
        masked = mask_plate(decrypt_field(principal.keyring, PLATE_FIELD, alert.plate_enc))
    evidence_ids = list(
        principal.db.scalars(select(Evidence.id).where(Evidence.alert_id == alert.id))
    )
    return AlertOut(
        id=alert.id,
        camera_id=alert.camera_id,
        camera_name=camera_name,
        priority=alert.priority,
        status=alert.status,
        event_type=alert.event_type,
        description=alert.description,
        detected_at=alert.detected_at,
        plate_masked=masked,
        assigned_to=alert.assigned_to,
        assigned_to_name=(
            principal.db.scalar(select(User.display_name).where(User.id == alert.assigned_to))
            if alert.assigned_to
            else None
        ),
        patrol_status=alert.patrol_status,
        patrol_status_at=alert.patrol_status_at,
        decided_by=alert.decided_by,
        decided_at=alert.decided_at,
        evidence_ids=evidence_ids,
    )


def get_visible_alert(principal: Principal, alert_id: uuid.UUID) -> Alert:
    """Load an alert or 404. Patrol users get 404 (not 403) for unassigned alerts too."""
    alert = principal.db.get(Alert, alert_id)
    if alert is None or not can_view_alert(principal, alert):
        not_found(principal, "alerts", alert_id)
    return alert


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status: AlertStatus | None = None,
    plate: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(require(Permission.alerts_read)),
) -> list[AlertOut]:
    stmt = select(Alert, Camera.name).join(Camera, Camera.id == Alert.camera_id)
    stmt = scope_alerts(stmt, principal)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if plate:
        if not has_permission(principal.role, Permission.alerts_plate_search):
            raise HTTPException(403, "Forbidden")
        stmt = stmt.where(
            Alert.plate_bidx == blind_index(principal.keyring, PLATE_FIELD, normalize_plate(plate))
        )
    stmt = stmt.order_by(_priority_rank, Alert.detected_at.desc()).limit(limit)
    rows = principal.db.execute(stmt).all()
    if plate:
        principal.audit(AuditAction.alert_plate_search, details={"results": len(rows)})
    return [to_out(principal, a, cam) for a, cam in rows]


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: uuid.UUID, principal: Principal = Depends(require(Permission.alerts_read))
) -> AlertOut:
    alert = get_visible_alert(principal, alert_id)
    mark_first_viewed(principal, alert)
    camera = principal.db.get(Camera, alert.camera_id)
    return to_out(principal, alert, camera.name if camera else None)


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(
    body: AlertIn, principal: Principal = Depends(require(Permission.alerts_create))
) -> AlertOut:
    """Manual alert creation (the detection pipeline will use the same service later)."""
    camera = principal.db.get(Camera, body.camera_id)
    if camera is None:
        not_found(principal, "cameras", body.camera_id)
    alert = Alert(
        tenant_id=principal.tenant_id,
        camera_id=camera.id,
        priority=body.priority,
        event_type=body.event_type,
        description=body.description,
        detected_at=body.detected_at or datetime.now(UTC),
        details={"origin": "manual_entry", "review_only": True},
    )
    if body.plate:
        norm = normalize_plate(body.plate)
        alert.plate_enc = encrypt_field(principal.keyring, PLATE_FIELD, norm)
        alert.plate_bidx = blind_index(principal.keyring, PLATE_FIELD, norm)
    principal.db.add(alert)
    principal.db.flush()
    from app.services.notifications import record as record_notification
    record_notification(principal.db, alert, "candidate_created")
    principal.db.commit()
    principal.audit(
        AuditAction.alert_created,
        resource_type="alerts",
        resource_id=alert.id,
        details={"priority": alert.priority.value, "event_type": alert.event_type},
    )
    notify_new_alert(principal.tenant_id, alert.priority, None)
    return to_out(principal, alert, camera.name)


def _decide(
    principal: Principal, alert_id: uuid.UUID, status: AlertStatus, note: str | None
) -> AlertOut:
    # Serialize competing decisions; one canonical state transition wins.
    alert = principal.db.scalar(select(Alert).where(Alert.id == alert_id).with_for_update())
    if alert is None or not can_view_alert(principal, alert):
        not_found(principal, "alerts", alert_id)
    if alert.status != AlertStatus.new:
        raise HTTPException(409, "Alert already decided")
    alert.status = status
    alert.decided_by = principal.user_id
    alert.decided_at = datetime.now(UTC)
    from app.services.notifications import record as record_notification
    record_notification(principal.db, alert, "confirmed" if status == AlertStatus.confirmed else "rejected")
    principal.db.commit()
    principal.audit(
        (
            AuditAction.alert_confirmed
            if status == AlertStatus.confirmed
            else AuditAction.alert_rejected
        ),
        resource_type="alerts",
        resource_id=alert.id,
        details={"note": note} if note else None,
    )
    return to_out(principal, alert)


@router.post("/{alert_id}/confirm", response_model=AlertOut)
def confirm(
    alert_id: uuid.UUID,
    body: AlertDecisionIn | None = None,
    principal: Principal = Depends(require(Permission.alerts_decide)),
) -> AlertOut:
    return _decide(principal, alert_id, AlertStatus.confirmed, body.note if body else None)


@router.post("/{alert_id}/reject", response_model=AlertOut)
def reject(
    alert_id: uuid.UUID,
    body: AlertDecisionIn | None = None,
    principal: Principal = Depends(require(Permission.alerts_decide)),
) -> AlertOut:
    return _decide(principal, alert_id, AlertStatus.rejected, body.note if body else None)


@router.post("/{alert_id}/assign", response_model=AlertOut)
def assign(
    alert_id: uuid.UUID,
    body: AlertAssignIn,
    principal: Principal = Depends(require(Permission.alerts_assign)),
) -> AlertOut:
    alert = get_visible_alert(principal, alert_id)
    assignee = principal.db.get(User, body.user_id)
    if assignee is None:
        not_found(principal, "users", body.user_id)
    if assignee.role != Role.patrol or not assignee.is_active:
        raise HTTPException(422, "Alerts can only be assigned to active patrol users")
    alert.assigned_to = assignee.id
    alert.patrol_status, alert.patrol_status_at = "assigned", datetime.now(UTC)
    from app.services.notifications import record as record_notification
    record_notification(principal.db, alert, "assigned", dedup_key=f"assignment:{alert.id}:{assignee.id}")
    principal.db.commit()
    principal.audit(
        AuditAction.alert_assigned,
        resource_type="alerts",
        resource_id=alert.id,
        details={"assignee_id": str(assignee.id)},
    )
    notify_new_alert(principal.tenant_id, alert.priority, assignee.id)
    return to_out(principal, alert)
