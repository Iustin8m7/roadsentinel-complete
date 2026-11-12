"""The one place where a human decision on an alert is written.

Both decision APIs (``POST /api/alerts/{id}/confirm|reject`` and the contract's
``POST /api/events/{number}/decision``) call :func:`decide`. It is a single conditional
``UPDATE ... WHERE status = 'new' AND superseded_at IS NULL RETURNING``: of two concurrent
operators exactly one matches; the other gets :class:`DecisionConflictError` carrying the decision
that won. There is no read-then-write window.

Ownership: the only server-side ownership rule that exists is patrol assignment
(``alerts.assigned_to``, see ``app.core.policy``). Patrol users cannot decide at all
(no ``alerts:decide``), and visibility is checked before this function is called. There is no
claim/lock/handover module in this codebase; if one is added, its check belongs in the WHERE
clause below so a stale tab cannot bypass it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core import audit
from app.core.audit import AuditAction
from app.models import Alert, AlertStatus, User


@dataclass
class DecisionConflictError(Exception):
    status: str
    action: str | None
    decided_by: str | None
    decided_at: datetime | None
    same_actor: bool

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "action": self.action,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


def decide(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    alert: Alert,
    confirm: bool,
    action: str | None,
    note: str | None,
) -> tuple[Alert, bool]:
    """Atomically move ``alert`` from ``new`` to confirmed/rejected, or raise
    :class:`DecisionConflictError` (and audit the losing attempt). Repeating one's own identical
    decision (a retried request) returns the alert unchanged instead of failing.

    Returns ``(alert, replayed)``; the caller audits the decision only when not replayed."""
    won = db.execute(
        update(Alert)
        .where(
            Alert.id == alert.id,
            Alert.status == AlertStatus.new,
            Alert.superseded_at.is_(None),
        )
        .values(
            status=AlertStatus.confirmed if confirm else AlertStatus.rejected,
            action=action if confirm else None,
            decision_note=note,
            decided_by=actor_id,
            decided_at=datetime.now(UTC),
        )
        .returning(Alert.id)
    ).first()
    db.commit()
    db.refresh(alert)
    if won is None:
        wanted = AlertStatus.confirmed if confirm else AlertStatus.rejected
        if (
            alert.decided_by == actor_id
            and alert.status == wanted
            and alert.action == (action if confirm else None)
        ):
            return alert, True  # idempotent retry of the caller's own decision
        winner = db.get(User, alert.decided_by) if alert.decided_by else None
        name = winner.display_name if winner else None
        conflict = DecisionConflictError(
            status=alert.status.value,
            action=alert.action,
            decided_by=name,
            decided_at=alert.decided_at,
            same_actor=alert.decided_by == actor_id,
        )
        audit.record(
            tenant_id,
            AuditAction.alert_decision_conflict,
            actor_id=actor_id,
            resource_type="alerts",
            resource_id=alert.id,
            details={
                "event_no": alert.number,
                "attempted": "confirm" if confirm else "reject",
                "current_status": alert.status.value,
            },
        )
        raise conflict
    return alert, False


def conflict_message(conflict: DecisionConflictError) -> str:
    if conflict.status == AlertStatus.new.value:
        return "Evenimentul nu mai poate fi decis (a fost retras din coadă)."
    verb = "confirmat" if conflict.status == AlertStatus.confirmed.value else "respins"
    who = f" de {conflict.decided_by}" if conflict.decided_by else ""
    return f"Evenimentul a fost deja {verb}{who}."
