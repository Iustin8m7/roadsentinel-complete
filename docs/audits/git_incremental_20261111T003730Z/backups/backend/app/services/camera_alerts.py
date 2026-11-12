"""Operational failure notifications for managed cameras (spec 3.8), on the EXISTING Web Push
subsystem (``app.services.push``). No e-mail, SMS or other external messaging.

When a managed camera is in a failure state, the tenant administrators are notified at most once
per ``NOTIFY_THROTTLE`` for each (camera, state). Every notification is recorded in the camera's
health history and in the audit chain, inside the same transaction that sets the throttle mark,
with its honest result:

* ``not_configured`` - no VAPID keys: nothing is sent (no fake dispatch);
* ``no_subscribers`` - push is configured but no administrator has subscribed;
* ``queued`` - handed to the background push sender for N subscriptions (delivery itself is
  best effort, as for alert pushes).

Triggers: heartbeats and acks (event driven), and ``python -m app.cli notify-camera-failures``
for a worker that went silent (no request arrives to trigger anything; schedule it like
``run-export-jobs``). Legacy cameras are never notified about.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.audit import AuditAction
from app.models import Camera, CameraWorkerStatus
from app.services import camera_control, push

NOTIFY_THROTTLE = timedelta(minutes=30)
PUSH_WAIT_S = 30  # upper bound a one-shot sweep waits for one push to be sent
# "stale": the worker crashed or went offline while the camera is desired ON.
NOTIFY_STATES = frozenset(
    {
        "stale",
        "auth_failed",
        "config_rejected",
        "source_mismatch",
        "frozen_image",
        "source_failed",
        "decoder_failed",
        "model_unavailable",
    }
)


@dataclass
class Notice:
    tenant_id: uuid.UUID
    state: str
    result: str
    subscription_ids: list[uuid.UUID] = field(default_factory=list)


def notify_state(
    db: Session,
    camera: Camera,
    row: CameraWorkerStatus,
    state: str,
    now: datetime | None = None,
) -> Notice | None:
    """Record (and, after commit, dispatch with ``dispatch``) a failure notice unless the camera
    is legacy, the state is not a failure, or the same state was notified within the throttle.
    The caller holds the status row lock and commits."""
    if camera.lifecycle_state == "legacy" or state not in NOTIFY_STATES:
        return None
    now = now or datetime.now(UTC)
    marks = dict(row.failure_notified or {})
    last = marks.get(state)
    if last and now - datetime.fromisoformat(last) < NOTIFY_THROTTLE:
        return None
    marks[state] = now.isoformat()
    row.failure_notified = marks
    subs: list[uuid.UUID] = []
    if not push.push_configured():
        result = "not_configured"
    else:
        subs = [s.id for s in push.admin_subscriptions(db)]
        result = "queued" if subs else "no_subscribers"
    camera_control.add_event(
        db, camera, "notify", at=now, health=state, reason_code=f"{state}:{result}"[:64]
    )
    audit.append(
        db,
        camera.tenant_id,
        AuditAction.camera_failure_notified,
        resource_type="cameras",
        resource_id=camera.id,
        details={
            "camera": camera.slug,
            "state": state,
            "result": result,
            "subscriptions": len(subs),
            "channel": "web_push",
        },
    )
    return Notice(camera.tenant_id, state, result, subs)


def check_camera(db: Session, camera: Camera, now: datetime | None = None) -> Notice | None:
    """Notify about the camera's current derived runtime state if it is a failure."""
    row = camera_control.worker_status(db, camera.id)
    if row is None:
        return None  # never seen: not a failure of a running worker
    now = now or datetime.now(UTC)
    state = camera_control.derive_status(db, camera, row, now)["state"]
    return notify_state(db, camera, row, state, now)


def dispatch(notice: Notice | None) -> threading.Thread | None:
    """After commit: hand a queued notice to the push sender (no-op otherwise). Returns the
    sender's background thread, if one was started."""
    if notice is not None and notice.result == "queued":
        return push.notify_camera_failure(notice.tenant_id, notice.subscription_ids, notice.state)
    return None


def sweep(
    db: Session, now: datetime | None = None, *, wait: bool = False
) -> list[tuple[str, Notice]]:
    """One pass over the tenant's managed cameras (``db`` is tenant scoped); commits. ``wait``
    blocks until each push has been sent: a one-shot process would otherwise exit first."""
    now = now or datetime.now(UTC)
    out: list[tuple[str, Notice]] = []
    cameras = db.scalars(
        select(Camera)
        .where(Camera.is_active.is_(True), Camera.lifecycle_state != "legacy")
        .order_by(Camera.slug)
    ).all()
    for camera in cameras:
        if camera_control.worker_status(db, camera.id) is None:
            continue
        camera_control._status_row(db, camera)  # row lock: serializes with heartbeats
        notice = check_camera(db, camera, now)
        db.commit()
        if notice is not None:
            sender = dispatch(notice)
            if wait and sender is not None:
                sender.join(timeout=PUSH_WAIT_S)
            out.append((camera.slug, notice))
    return out
