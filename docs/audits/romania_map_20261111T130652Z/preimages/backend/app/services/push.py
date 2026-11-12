"""Web Push (VAPID) scaffold. Payloads are deliberately generic: no plate, location, image or
personal data ever leaves through a push service. The client fetches details after login."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from typing import Any

from sqlalchemy import ColumnElement, or_, select

from app.config import get_settings
from app.db import tenant_session
from app.models import Priority, PushSubscription, Role, User

log = logging.getLogger("app.push")

ALLOWED_PAYLOAD_KEYS = frozenset({"title", "body", "tag", "url"})


def build_alert_payload(priority: Priority) -> dict[str, str]:
    return {
        "title": "RoadSentinel",
        "body": f"New alert, priority: {Priority(priority).value}",
        "tag": "rs-alert",
        "url": "/alerts",
    }


def _assert_generic(payload: dict[str, Any]) -> None:
    if set(payload) - ALLOWED_PAYLOAD_KEYS:
        raise ValueError("push payload contains non-generic fields")


def _send(sub: PushSubscription, payload: dict[str, str]) -> bool:
    """Returns False when the subscription is gone (HTTP 404/410)."""
    from pywebpush import WebPushException, webpush  # imported lazily: optional at runtime

    s = get_settings()
    if not s.vapid_private_key:
        return True
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=s.vapid_private_key.get_secret_value(),
            vapid_claims={"sub": s.vapid_subject},
            ttl=300,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        log.info("push delivery failed", extra={"status": status})
        return status not in (404, 410)
    except Exception:
        log.exception("push delivery error")
    return True


def notify_new_alert(
    tenant_id: uuid.UUID, priority: Priority, assignee: uuid.UUID | None
) -> threading.Thread | None:
    """Fan out a generic notification in a background thread (returned for callers that wait)."""
    if not get_settings().vapid_private_key:
        return None
    payload = build_alert_payload(priority)
    _assert_generic(payload)

    def run() -> None:
        audience: list[ColumnElement[bool]] = [User.role.in_([Role.tenant_admin, Role.operator])]
        if assignee:
            audience.append(User.id == assignee)
        with tenant_session(tenant_id) as db:
            stmt = (
                select(PushSubscription)
                .join(User, User.id == PushSubscription.user_id)
                .where(User.is_active.is_(True), or_(*audience))
            )
            gone = [s for s in db.scalars(stmt).all() if not _send(s, payload)]
            for s in gone:
                db.delete(s)
            db.commit()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
