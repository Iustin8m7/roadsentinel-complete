"""Transactional notification log. The SSE reader polls committed rows across API workers."""

from __future__ import annotations

from sqlalchemy import func, select, text

from app.models import Alert, NotificationEvent


def record(db, alert: Alert, kind: str, *, dedup_key: str | None = None) -> None:
    """Call before the alert transaction commits; retries reuse the canonical alert and key."""
    details = alert.details or {}
    if (details.get("synthetic") is True or details.get("test_only") is True
            or details.get("scenario_type") == "synthetic_test"):
        return
    provenance = str(details.get("origin") or "live_camera")[:32]
    # Serialize only this tenant's append operations. Cursors have no cross-tenant gaps.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
               {"key": f"notification:{alert.tenant_id}"})
    next_sequence = (db.scalar(select(func.max(NotificationEvent.sequence)).where(
        NotificationEvent.tenant_id == alert.tenant_id)) or 0) + 1
    db.add(
        NotificationEvent(
            tenant_id=alert.tenant_id,
            sequence=next_sequence,
            alert_id=alert.id,
            kind=kind,
            priority=alert.priority.value,
            provenance=provenance,
            dedup_key=dedup_key or f"alert:{alert.id}:{kind}",
        )
    )


def visible_query(principal):
    from app.core.policy import scope_alerts

    return scope_alerts(
        select(NotificationEvent, Alert)
        .join(Alert, Alert.id == NotificationEvent.alert_id),
        principal,
    )
